# 第10章 ES6+ 新特性与模块化

> 难度：intermediate | 预计学习时间：120分钟 | 8个知识点

## 学习目标

- 掌握模板字符串、增强对象字面量等常用 ES6 语法
- **掌握 ES Module (import/export)**
- 了解动态导入和顶层 await
- 了解 BigInt 和 ES2020+ 新特性

---

## 知识点详解

### 10.1-10.3 常用 ES6 语法

> 难度：beginner | topic_code: js_template_literal / js_es6_object / js_let_const_scope

```javascript
// 模板字符串
const name = "张三", age = 20;
const msg = `你好，我是${name}，今年${age}岁`;
// 支持多行（不用 \n）
const html = `
  <div>
    <h1>标题</h1>
  </div>
`;

// 增强的对象字面量
const key = "dynamicKey";
const obj = {
  [key]: "动态键",        // 计算属性名
  name,                   // 属性简写（name: name 的缩写）
  greet() {               // 方法简写
    return `你好，${this.name}`;
  }
};

// 块级作用域 (let/const) — 已经在第2章详细介绍
// 关键区别：var 是函数作用域，let/const 是块级作用域
```

---

### 10.4 ES Module

> 难度：intermediate | topic_code: js_module

ES Module 是现代 JavaScript 的标准模块系统：

```javascript
// ---- math.js ----
// 命名导出
export const PI = 3.14159;
export function add(a, b) { return a + b; }
export class Calculator { /* ... */ }

// 默认导出（一个模块只能有一个）
export default function multiply(a, b) { return a * b; }

// ---- main.js ----
// 命名导入
import { PI, add } from "./math.js";

// 默认导入
import multiply from "./math.js";

// 重命名导入
import { add as sum } from "./math.js";

// 全部导入
import * as MathUtils from "./math.js";
MathUtils.add(1, 2);

// 副作用导入（只执行模块顶层代码，不导入任何绑定）
import "./init.js";
```

> Node.js 中使用 ES Module：package.json 设置 `"type": "module"` 或文件后缀用 `.mjs`

---

### 10.5 动态导入

> 难度：advanced | topic_code: js_dynamic_import

```javascript
// 静态导入：import 必须在模块顶层，不能放在条件/循环/函数里
// 动态导入：import() 返回 Promise，可以在任何地方使用

// 按需加载（代码分割的核心）
if (needChart) {
  const { default: Chart } = await import("./chart.js");
  new Chart(data);
}

// 条件加载
const locale = navigator.language;
const { messages } = await import(`./i18n/${locale}.js`);

// 返回的是模块命名空间对象
const module = await import("./math.js");
console.log(module.add(1, 2));
console.log(module.default(3, 4));  // 默认导出通过 .default 访问
```

---

### 10.6 顶层 await

> 难度：advanced | topic_code: js_top_level_await

ES2022 允许在模块顶层直接使用 `await`，不需要包裹在 async 函数中：

```javascript
// ---- config.js ----
const response = await fetch("/api/config");
export const config = await response.json();

// ---- main.js ----
// import config 的模块会等待顶层 await 完成再执行
import { config } from "./config.js";
console.log(config);  // config 一定已经加载完成
```

> 注意：顶层 await 会阻塞依赖该模块的其他模块的执行。仅在 ES Module 中可用，CommonJS 不支持。

---

### 10.7 BigInt

> 难度：intermediate | topic_code: js_bigint

```javascript
// Number 的安全范围：±9,007,199,254,740,991 (2^53 - 1)
const maxSafe = Number.MAX_SAFE_INTEGER;
console.log(maxSafe + 1 === maxSafe + 2);  // true！（精度丢失）

// BigInt：任意精度的整数
const big = 9007199254740993n;     // 后缀 n
const big2 = BigInt("9007199254740993");

big + big2;    // 18014398509481986n
big * 2n;      // 18014398509481986n
big / 2n;      // 4503599627370496n（除法结果向零截断）

// BigInt 不能与 Number 混用
// big + 1;  // TypeError!
// BigInt(1) + BigInt(1); // 也不行，BigInt() 参数不能是数字
1n + 1n;      // 正确
```

---

### 10.8 ES2020+ 新特性概览

> 难度：intermediate | topic_code: js_es2020_plus

```javascript
// ES2020 (ES11)
// 可选链 ?. （第3章已介绍）
// 空值合并 ??（第3章已介绍）
// 动态导入 import()（本章已介绍）
// BigInt（本章已介绍）
globalThis;  // 统一的全局对象引用（浏览器=window, Node=global）

// ES2021 (ES12)
// 逻辑赋值运算符
x ||= y;  // x = x || y
x &&= y;  // x = x && y
x ??= y;  // x = x ?? y
"hello".replaceAll("l", "L");  // "heLLo"

// ES2022 (ES13)
// 类私有字段 #
// 顶层 await
// Object.hasOwn(obj, prop) — 替代 obj.hasOwnProperty(prop)
// Array.at()：支持负索引
const arr = [1, 2, 3];
arr.at(-1);  // 3（最后一个元素）
arr.at(0);   // 1

// ES2023 (ES14)
// Array.findLast / findLastIndex
[1, 2, 3, 2, 1].findLast(x => x > 1);    // 2
// Array.toSorted / toReversed / toSpliced（返回新数组，不修改原数组）
const sorted = [3, 1, 2].toSorted();  // [1, 2, 3]

// ES2024 (ES15)
// Promise.withResolvers()
// Object.groupBy / Map.groupBy
// 正则 v 标志（Unicode 集合表示法）
```

---

## 本章小结

- 模板字符串用反引号，支持插值 `${}` 和多行
- ES Module 是标准模块化方案，import/export 语法
- 动态 import() 实现按需加载（代码分割）
- Number 安全整数范围有限，超大整数用 BigInt
- ES6 之后每年一个版本，新特性稳定且实用

## 扩展阅读

- MDN ES Module：https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Guide/Modules
- TC39 Proposals（新特性提案跟踪）：https://github.com/tc39/proposals
- ES 各版本特性汇总：https://exploringjs.com/impatient-js/ch_history.html
