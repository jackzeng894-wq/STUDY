"""Auth API endpoints: register, login, and JWT dependency."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.student import Student
from app.schemas.auth import (
    StudentLogin,
    StudentRegister,
    StudentResponse,
    TokenResponse,
)

router = APIRouter(tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(student_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(student_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_current_student(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Student:
    """FastAPI dependency: extract and validate JWT, return current Student."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        student_id: str | None = payload.get("sub")
        if student_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(Student).where(Student.id == str(student_id))
    )
    student = result.scalar_one_or_none()
    if student is None:
        raise credentials_exception
    return student


@router.post("/register", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def register(data: StudentRegister, db: AsyncSession = Depends(get_db)):
    """Register a new student account."""
    # Check username uniqueness
    existing = await db.execute(
        select(Student).where(Student.username == data.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        )

    student = Student(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(student)
    await db.flush()
    await db.refresh(student)
    return student


@router.post("/login", response_model=TokenResponse)
async def login(data: StudentLogin, db: AsyncSession = Depends(get_db)):
    """Login and receive a JWT access token."""
    result = await db.execute(
        select(Student).where(Student.username == data.username)
    )
    student = result.scalar_one_or_none()
    if not student or not verify_password(data.password, student.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(student.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=StudentResponse)
async def get_me(current_student: Student = Depends(get_current_student)):
    """Get the currently authenticated student."""
    return current_student
