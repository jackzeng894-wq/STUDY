# 第2章 变量与数据类型

> 难度：beginner | 预计学习时间：120分钟 | 8个知识点

## 学习目标

- 掌握 let / const 声明方式，理解与 var 的区别
- 掌握 JavaScript 的 7 种基本数据类型
- 理解类型隐式转换的规则和陷阱
- 学会 typeof 类型判断
- 掌握字符串和数字的常用方法
- 理解 null 和 undefined 的区别
- 了解 Symbol 类型的用途

---

## 知识点详解

### 2.1 变量声明：var / let / const

> 难度：beginner | topic_code: js_var_let_const

JavaScript 有三种声明变量的方式：

| 关键字 | 作用域 | 可重复声明 | 可重新赋值 | 声明前可用 | 推荐 |
|--------|--------|-----------|-----------|-----------|------|
| var | 函数作用域 | 可以 | 可以 | 可以(undefined) | 不推荐 |
| let | 块级作用域 | 不可以 | 可以 | 不可以(TDZ) | 推荐 |
| const | 块级作用域 | 不可以 | **不可以** | 不可以(TDZ) | 推荐 |

```javascript
// var: 函数作用域，变量提升
console.log(a);  // undefined（不会报错，这是"变量提升"）
var a = 10;

// let: 块级作用域，存在暂时性死区(TDZ)
// console.log(b);  // ReferenceError!  TDZ 内不能访问
let b = 20;

// const: 声明常量，必须立即初始化
const PI = 3.14159;
// PI = 3;  // TypeError! 不能重新赋值

// 注意：const 的对象属性可以修改
const user = { name: "张三" };
user.name = "李四";  // 允许！const 保护的是引用，不是对象内容
```

> 核心原则：**默认用 const，需要重新赋值时用 let，永远不用 var**。

---

### 2.2 基本数据类型

> 难度：beginner | topic_code: js_primitive_types

JavaScript 共有 7 种基本类型（primitive）和 1 种引用类型（Object）：

| 类型 | 示例 | typeof 结果 | 说明 |
|------|------|------------|------|
| number | `42`, `3.14`, `NaN`, `Infinity` | "number" | 整数和浮点数统一为 number |
| string | `"hello"`, `'world'`, `` `模板` `` | "string" | 三种引号 |
| boolean | `true`, `false` | "boolean" | 逻辑值 |
| undefined | `undefined` | "undefined" | 变量已声明但未赋值 |
| null | `null` | **"object"** | 空值（typeof 的 bug） |
| symbol | `Symbol("id")` | "symbol" | 唯一值 |
| bigint | `9007199254740993n` | "bigint" | 大整数 |

> 注意：`typeof null === "object"` 是 JavaScript 的历史遗留 bug，从第一版开始就存在，因兼容性原因无法修复。

---

### 2.3 类型转换与隐式转换

> 难度：intermediate | topic_code: js_type_coercion

JavaScript 是**弱类型**语言，运算符可能导致自动类型转换，这是很多 bug 的来源：

```javascript
// 隐式转换陷阱（"WTF" 时刻）
console.log(1 + "2");        // "12"  数字 + 字符串 → 字符串拼接
console.log("5" - 3);        // 2     字符串 - 数字 → 数学运算
console.log("5" * "2");      // 10    两个字符串 → 数学运算
console.log(0 == false);     // true  宽松相等会类型转换
console.log(0 === false);    // false 严格相等不转换
console.log([] + []);        // ""    空数组转空字符串
console.log([] + {});        // "[object Object]"
console.log(typeof NaN);     // "number"  NaN 也是 number 类型
```

> 核心原则：**永远使用 `===` 和 `!==`**（严格比较），不要用 `==` 和 `!=`（宽松比较）。

---

### 2.4 typeof 与类型判断

> 难度：beginner | topic_code: js_typeof

```javascript
typeof "hello";      // "string"
typeof 42;           // "number"
typeof true;         // "boolean"
typeof undefined;    // "undefined"
typeof Symbol();     // "symbol"
typeof 123n;         // "bigint"
typeof {};           // "object"
typeof [];           // "object"  ← 注意：数组也是 object
typeof null;         // "object"  ← 历史 bug
typeof function(){}; // "function" ← 函数是特殊的对象

// 判断数组：用 Array.isArray
Array.isArray([1, 2, 3]);  // true
Array.isArray({a: 1});     // false

// 判断 null：直接用 ===
value === null;
```

---

### 2.5 字符串常用方法

> 难度：beginner | topic_code: js_string_methods

```javascript
const str = "Hello, JavaScript";

// 基本信息
str.length;               // 18
str[0];                   // "H"（但不要这样遍历，用 charAt）

// 查找
str.indexOf("Java");      // 7
str.includes("world");    // false
str.startsWith("Hello");  // true
str.endsWith("Script");   // true

// 截取
str.slice(0, 5);          // "Hello"
str.slice(-6);            // "Script"
str.substring(0, 5);      // "Hello"（不支持负数）

// 变换
str.toUpperCase();        // "HELLO, JAVASCRIPT"
str.toLowerCase();        // "hello, javascript"
str.replace("Java", "Type"); // "Hello, TypeScript"
str.replaceAll("l", "L"); // "HeLLo, JavaScript"

// 分割与拼接
str.split(", ");          // ["Hello", "JavaScript"]
["a", "b", "c"].join("-"); // "a-b-c"

// 去除空格
"  hello  ".trim();       // "hello"
```

---

### 2.6 数字与 Math 对象

> 难度：beginner | topic_code: js_number_methods

```javascript
// 数字转换
Number("42");       // 42
parseInt("42px", 10); // 42（推荐传第二个参数指定进制）
parseFloat("3.14"); // 3.14

// 精度问题：经典陷阱
console.log(0.1 + 0.2);          // 0.30000000000000004
console.log(0.1 + 0.2 === 0.3);  // false!

// Math 对象
Math.round(3.6);     // 4    四舍五入
Math.floor(3.6);     // 3    向下取整
Math.ceil(3.2);      // 4    向上取整
Math.random();       // 0-1之间的随机数
Math.max(1, 5, 3);   // 5    最大值
Math.min(1, 5, 3);   // 1    最小值
Math.abs(-5);        // 5    绝对值
Math.PI;             // 3.141592653589793
```

---

### 2.7 null 与 undefined

> 难度：beginner | topic_code: js_null_undefined

`undefined` 和 `null` 都表示"没有值"，但含义完全不同：

| | undefined | null |
|------|-----------|------|
| 含义 | 变量已声明但**未赋值** | **故意设置为空** |
| 类型 | undefined | object（bug） |
| 谁设置的 | JavaScript 引擎自动 | 开发者手动 |
| 何时出现 | 未初始化的变量、函数无返回值、访问不存在的属性 | 开发者明确表示"这里应该是空" |

```javascript
let x;                  // x 是 undefined（声明但未赋值）
function foo() {}       // foo() 返回 undefined（无return语句）
const obj = {};
obj.notExist;           // undefined（属性不存在）

let y = null;           // 开发者主动设为 null，表示"目前没有值"

// 判断
x == null;   // true（null和undefined宽松相等）
x === null;  // false（严格不等）
x == undefined; // true（等价写法：x === undefined）
```

---

### 2.8 Symbol 类型

> 难度：intermediate | topic_code: js_symbol

Symbol 是 ES6 引入的基本类型，每次创建的值都是**唯一**的：

```javascript
const s1 = Symbol("id");
const s2 = Symbol("id");
console.log(s1 === s2);  // false  即使描述相同，Symbol 值也不等

// 用途1：对象唯一属性名（防止属性名冲突）
const user = {
  name: "张三",
  [Symbol("id")]: 12345
};

// 用途2：内置 Well-Known Symbol
// Symbol.iterator 让对象可被 for...of 遍历
// Symbol.toStringTag 自定义 Object.prototype.toString 的输出
```

> Symbol 主要用于库/框架开发中防止属性名冲突，日常业务代码中较少直接使用。

---

## 本章小结

- 默认用 const，需要改值时用 let，永远不用 var
- JavaScript 有 7 种基本类型 + Object，注意 typeof null 的 bug
- **永远用 ===**，避免隐式转换的坑
- 0.1 + 0.2 ≠ 0.3 是浮点数精度的通病，不是 JS 独有的

## 扩展阅读

- MDN 数据类型：https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Data_structures
- 为什么 0.1 + 0.2 ≠ 0.3：https://0.30000000000000004.com/
