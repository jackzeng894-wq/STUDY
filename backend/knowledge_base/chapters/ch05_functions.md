# 第5章 函数

> 难度：intermediate | 预计学习时间：150分钟 | 10个知识点

## 学习目标

- 掌握函数声明的多种方式
- 理解箭头函数与普通函数的区别
- 掌握参数解构、默认值、剩余参数
- **深入理解作用域链和闭包**
- 掌握高阶函数和回调模式
- 了解递归

---

## 知识点详解

### 5.1 函数声明与表达式

> 难度：beginner | topic_code: js_func_decl

```javascript
// 1. 函数声明（会"提升"）
function add(a, b) {
  return a + b;
}

// 2. 函数表达式（不会提升）
const subtract = function(a, b) {
  return a - b;
};

// 3. 箭头函数
const multiply = (a, b) => a * b;

// 区别：声明会提升，表达式不会
console.log(declared());  // "ok"
function declared() { return "ok"; }

// console.log(expressed());  // ReferenceError!
const expressed = function() { return "error"; };
```

---

### 5.2 箭头函数

> 难度：beginner | topic_code: js_arrow_func

```javascript
// 简洁语法
const add = (a, b) => a + b;          // 单表达式省略 return
const greet = name => `Hello, ${name}`; // 单参数省略括号
const noArg = () => "no args";         // 无参数必须写括号
const multiLine = (a, b) => {          // 多行需要 {} 和 return
  const result = a + b;
  return result * 2;
};

// 箭头函数与普通函数的核心区别：
// 1. 没有自己的 this（继承外层词法作用域的 this）
// 2. 没有 arguments 对象
// 3. 不能用作构造函数（不能 new）
// 4. 没有 prototype 属性
```

---

### 5.3-5.4 参数处理

> 难度：beginner-intermediate | topic_code: js_params / js_default_rest

```javascript
// 参数解构
function printUser({ name, age, email = "未填写" }) {
  console.log(`${name}, ${age}岁, ${email}`);
}
printUser({ name: "张三", age: 20 });

// 默认参数
function greet(name = "匿名用户") {
  return `你好，${name}`;
}
greet();       // "你好，匿名用户"
greet("李四");  // "你好，李四"

// 剩余参数 ...rest（总是放在最后）
function sum(...numbers) {
  return numbers.reduce((total, n) => total + n, 0);
}
sum(1, 2, 3, 4);  // 10

// arguments 对象（旧式，箭头函数中不可用）
function oldStyle() {
  console.log(arguments);  // 类数组对象
}
```

---

### 5.5 作用域与作用域链

> 难度：intermediate | topic_code: js_scope

JavaScript 采用**词法作用域**（静态作用域）：函数的作用域由书写位置决定，而不是调用位置。

```javascript
// 三种作用域
var globalVar = "全局";  // 全局作用域

function outer() {
  const outerVar = "外层";  // 函数作用域

  function inner() {
    const innerVar = "内层";  // 函数作用域
    console.log(innerVar);    // "内层" - 自己的
    console.log(outerVar);    // "外层" - 上层作用域
    console.log(globalVar);   // "全局" - 全局作用域
  }

  inner();
  // console.log(innerVar);  // ReferenceError! 不能访问内部
}
```

**作用域链**：查找变量时，从当前作用域开始，一层层向上找，直到全局。找到即停，找不到报错。这个"链"在函数**定义**时就确定了。

---

### 5.6 闭包

> 难度：advanced | topic_code: js_closure

闭包是 JavaScript 中最重要的概念之一：**函数 + 其引用的外部变量 = 闭包**。

```javascript
// 经典闭包示例
function createCounter() {
  let count = 0;               // 这个变量被"封闭"在内部
  return function() {
    count++;                   // 内部函数引用外部变量
    return count;
  };
}

const counter = createCounter();
console.log(counter());  // 1
console.log(counter());  // 2
// count 变量不会被垃圾回收，因为返回的函数还在引用它
```

**闭包的实用场景**：

```javascript
// 1. 数据私有化（模块模式）
function createUser(name) {
  let _age = 0;  // 私有变量
  return {
    getName: () => name,
    getAge: () => _age,
    setAge: (age) => { if (age > 0) _age = age; }
  };
}

// 2. 循环中的经典问题
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 100);  // 3 3 3
}
// 解决方案1：用 let（块级作用域）
for (let i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 100);  // 0 1 2
}
// 解决方案2：闭包 + IIFE
for (var i = 0; i < 3; i++) {
  (function(j) { setTimeout(() => console.log(j), 100); })(i);  // 0 1 2
}
```

---

### 5.7 立即执行函数 (IIFE)

> 难度：beginner | topic_code: js_iife

```javascript
// Immediately Invoked Function Expression
(function() {
  const private = "外部不可见";
  console.log("立即执行");
})();

// 箭头函数 IIFE
(() => {
  console.log("箭头版 IIFE");
})();

// 用途：创建独立作用域（在模块化普及前的主要用法，现在更多用模块）
```

---

### 5.8-5.9 高阶函数与回调

> 难度：intermediate | topic_code: js_higher_order / js_callback

```javascript
// 高阶函数：接收函数作为参数 或 返回函数
const twice = (fn, value) => fn(fn(value));
const addOne = x => x + 1;
console.log(twice(addOne, 5));  // 7（5→6→7）

// 回调函数：作为参数传入，在某个时刻被调用
// 同步回调：
[1, 2, 3].map(x => x * 2);               // 立即执行
[1, 2, 3, 4].filter(x => x % 2 === 0);   // 立即执行

// 异步回调用法（事件监听）：
button.addEventListener("click", (event) => {
  console.log("按钮被点击了");
});
```

---

### 5.10 递归函数

> 难度：intermediate | topic_code: js_recursion

```javascript
// 阶乘
function factorial(n) {
  if (n <= 1) return 1;            // 基准条件（必须有，否则死循环）
  return n * factorial(n - 1);     // 递归调用
}
factorial(5);  // 120

// 尾递归优化（ES6 严格模式）
function factorialTail(n, acc = 1) {
  if (n <= 1) return acc;
  return factorialTail(n - 1, n * acc);
}

// 递归的缺点：深度过大导致栈溢出
// 解决方案：用循环替代，或用尾递归+严格模式
```

---

## 本章小结

- 箭头函数简洁但没有自己的 this，不能做构造函数
- 词法作用域由**书写位置**决定，闭包是 JS 最强大的特性
- 高阶函数接收/返回函数，是函数式编程的基础
- 递归要有基准条件，注意栈溢出风险

## 扩展阅读

- MDN 闭包详解：https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Closures
- 我如何解释闭包：https://stackoverflow.com/questions/111102/how-do-javascript-closures-work
