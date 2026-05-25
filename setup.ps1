# RJB Project Setup Script
# 一键配置开发环境并启动项目
# 使用方法: 右键 -> 使用PowerShell运行, 或 .\setup.ps1

$ErrorActionPreference = "Stop"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RJB 个性化学习平台 - 环境配置" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Check/Install PostgreSQL
Write-Host "`n[1/5] 检查 PostgreSQL..." -ForegroundColor Yellow
$pgInstalled = Get-Command psql -ErrorAction SilentlyContinue
if (-not $pgInstalled) {
    Write-Host "  PostgreSQL 未安装，正在通过 winget 安装..." -ForegroundColor Gray
    winget install PostgreSQL.PostgreSQL.16 --accept-source-agreements --accept-package-agreements
    Write-Host "  请重新打开终端以使 PostgreSQL 生效" -ForegroundColor Yellow
    Write-Host "  或手动添加 PostgreSQL bin 目录到 PATH" -ForegroundColor Yellow
}

# 2. Install Python dependencies
Write-Host "`n[2/5] 安装 Python 依赖..." -ForegroundColor Yellow
Set-Location $PSScriptRoot/backend
pip install -r requirements.txt -q
Write-Host "  Python 依赖安装完成" -ForegroundColor Green

# 3. Install Frontend dependencies
Write-Host "`n[3/5] 安装前端依赖..." -ForegroundColor Yellow
Set-Location $PSScriptRoot/frontend
npm install --silent
Write-Host "  前端依赖安装完成" -ForegroundColor Green

# 4. Setup Database
Write-Host "`n[4/5] 配置数据库..." -ForegroundColor Yellow
$env:PGPASSWORD = "postgres"

# Try to create database (ignore error if already exists)
psql -U postgres -h localhost -c "CREATE DATABASE learning_agent;" 2>$null
psql -U postgres -h localhost -d learning_agent -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>$null
Write-Host "  数据库就绪" -ForegroundColor Green

# Run migrations
Set-Location $PSScriptRoot/backend
alembic upgrade head
Write-Host "  数据库迁移完成" -ForegroundColor Green

# 5. Index Knowledge Base
Write-Host "`n[5/5] 索引知识库..." -ForegroundColor Yellow
python -m app.rag.indexer
Write-Host "  知识库索引完成" -ForegroundColor Green

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  配置完成! 启动项目:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  终端1 (后端):" -ForegroundColor White
Write-Host "    cd backend" -ForegroundColor Gray
Write-Host "    uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "  终端2 (前端):" -ForegroundColor White
Write-Host "    cd frontend" -ForegroundColor Gray
Write-Host "    npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "  后端API: http://localhost:8000/api/v1" -ForegroundColor Blue
Write-Host "  API文档: http://localhost:8000/docs" -ForegroundColor Blue
Write-Host "  前端页面: http://localhost:5173" -ForegroundColor Blue
Write-Host ""
