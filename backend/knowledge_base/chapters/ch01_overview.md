# 第1章 JavaScript 基础概述

> 难度：beginner | 预计学习时间：60分钟 | 4个知识点

## 学习目标

- 了解 JavaScript 是什么及其核心用途
- 了解 ECMAScript 标准的发展历程
- 理解 JavaScript 的运行环境（浏览器 / Node.js）
- 掌握开发者工具的基本使用

---

## 知识点详解

### 1.1 JavaScript 简介

> 难度：beginner | topic_code: js_intro

JavaScript（简称JS）是一种**轻量级、解释型**的编程语言，最初由 Brendan Eich 在1995年创建。它是 Web 开发的三大核心技术之一：

| 技术 | 作用 | 类比 |
|------|------|------|
| HTML | 定义网页**结构** | 房子的骨架 |
| CSS | 定义网页**样式** | 房子的装修 |
| JavaScript | 定义网页**行为** | 房子的电器/开关 |

**JavaScript 能做什么？**
- 网页交互：表单验证、动画效果、数据动态加载
- 服务器开发：Node.js 让 JS 可以写后端
- 移动端开发：React Native / Flutter（Dart）
- 桌面应用：Electron（VS Code 就是用 JS 开发的）

**JavaScript 不是 Java**：两者只是名字相似，语法和设计理念完全不同。取名"JavaScript"是当时 Java 正火，跟风营销的结果。

---

### 1.2 JavaScript 发展史与 ECMAScript

> 难度：beginner | topic_code: js_history

JavaScript 由 ECMA 国际标准组织以 **ECMAScript** 名称标准化。关键版本节点：

| 版本 | 年份 | 别名 | 关键特性 |
|------|------|------|----------|
| ES3 | 1999 | - | 正则、try/catch、更完善的字符串方法 |
| ES5 | 2009 | - | 严格模式、JSON、数组方法(map/filter/forEach) |
| **ES6** | **2015** | ES2015 | **最大更新：class、箭头函数、let/const、Promise、模块** |
| ES7 | 2016 | ES2016 | Array.includes、指数运算符 |
| ES8 | 2017 | ES2017 | async/await、Object.values |
| ES9-ES15 | 2018-2024 | - | 可选链(?.)、空值合并(??)、顶层await |

> 关键认知：**ES6 之后改为每年发布一个版本**，命名方式从 ES6 改为 ES2015。日常说的"ES6+"通常泛指 ES6 及之后的所有新特性。

---

### 1.3 JavaScript 运行环境

> 难度：beginner | topic_code: js_runtime

JavaScript 代码需要一个**运行时环境**来执行。主要有两种：

**浏览器环境**：
- 每个浏览器都内置了 JavaScript 引擎：
  - Chrome → V8引擎
  - Firefox → SpiderMonkey
  - Safari → JavaScriptCore
- 浏览器提供了 **Web API**（DOM、BOM、Fetch、Canvas 等），这些不是 JS 语言本身的功能，而是浏览器赋予的额外能力
- 将 `<script>` 标签放在 HTML 文件中即可运行

**Node.js 环境**：
- 2009年 Ryan Dahl 将 V8引擎从浏览器中抽出来，加上了文件系统、网络等能力，创造了 Node.js
- 可以在服务器/命令行运行 JS
- 没有 DOM / BOM 等浏览器 API，但提供了 `fs`、`http`、`path` 等模块

> 核心区别：浏览器 JS 主要操作网页；Node.js JS 主要操作文件和网络。语言核心（语法、数据类型、函数等）两者完全一样。

---

### 1.4 开发工具与调试

> 难度：beginner | topic_code: js_devtools

**开发工具**：
- **VS Code**：最流行的 JS 开发编辑器，插件生态强大
- **浏览器 DevTools**：F12 打开，Console 面板可以输入和运行 JS 代码，是最好的 JS 学习工具

**调试方法**：
- `console.log(变量)` — 最基础的输出调试
- `console.table(数组)` — 以表格形式打印数组
- DevTools → Sources → 打断点 → 逐步执行 — 专业调试
- `debugger;` 语句 — 在代码中插入断点

**快速开始**：
打开浏览器按 F12，在 Console 中输入：
```javascript
console.log("Hello, JavaScript!");
```

---

## 本章小结

- JavaScript 是 Web 三大核心技术之一，负责网页交互行为
- ECMAScript 是 JS 的标准名称，ES6(2015)是最大的一次更新
- JS 代码只能在运行环境（浏览器/Node.js）中执行
- 浏览器 F12 打开 DevTools 是最方便的学习和调试工具

## 扩展阅读

- MDN JavaScript 教程：https://developer.mozilla.org/zh-CN/docs/Web/JavaScript
- JavaScript 历史（英文）：https://www.w3schools.com/js/js_history.asp
- Node.js 官网：https://nodejs.org/
