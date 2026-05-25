# 第4章 流程控制

> 难度：beginner | 预计学习时间：90分钟 | 8个知识点

## 学习目标

- 掌握 if/else 和 switch 条件语句
- 掌握 for / while 循环及变体
- 理解 for...of 与 for...in 的区别适用场景
- 学会使用 break / continue 控制循环
- 掌握 try...catch 异常处理

---

## 知识点详解

### 4.1 条件语句：if/else

> 难度：beginner | topic_code: js_if_else

```javascript
// 基本形式
if (score >= 90) {
  console.log("优秀");
} else if (score >= 60) {
  console.log("及格");
} else {
  console.log("不及格");
}

// 真值(Falsy)和假值(Truthy)
// 以下 6 个值是 Falsy，其他都是 Truthy：
false, 0, -0, 0n, "", null, undefined, NaN

if ("") console.log("不会输出");     // "" 是 falsy
if (" ") console.log("会输出");       // " " 是 truthy
if ([]) console.log("会输出");        // [] 是 truthy
if ({}) console.log("会输出");        // {} 是 truthy
```

---

### 4.2 switch 语句

> 难度：beginner | topic_code: js_switch

```javascript
const fruit = "apple";

switch (fruit) {
  case "apple":
    console.log("苹果 5 元/斤");
    break;  // 不要忘记 break！否则会"穿透"到下一个 case
  case "banana":
    console.log("香蕉 3 元/斤");
    break;
  default:
    console.log("未知水果");
}

// switch 使用 === 比较，不会做类型转换
```

---

### 4.3-4.6 循环语句

> 难度：beginner-intermediate | topic_code: js_for / js_while / js_for_of / js_for_in

```javascript
// for 循环：知道循环次数时使用
for (let i = 0; i < 5; i++) {
  console.log(`第 ${i + 1} 次`);
}

// while：不知道次数，靠条件控制
let count = 0;
while (count < 5) {
  console.log(count);
  count++;
}

// for...of：遍历可迭代对象的值（数组、字符串、Map、Set）
const arr = ["a", "b", "c"];
for (const item of arr) { console.log(item); }  // a b c
for (const char of "hello") { console.log(char); }  // h e l l o

// for...in：遍历对象的键（key），用于普通对象
const obj = { name: "张三", age: 20 };
for (const key in obj) { console.log(key, obj[key]); }
// name 张三, age 20

// 注意：for...in 会遍历原型链，用 hasOwnProperty 过滤
for (const key in obj) {
  if (Object.hasOwn(obj, key)) {
    console.log(key, obj[key]);
  }
}
```

> 核心区别：**for...of 遍历值（数组），for...in 遍历键（对象）**。

---

### 4.7 break 与 continue

> 难度：beginner | topic_code: js_break_continue

```javascript
// break：立即终止整个循环
for (let i = 0; i < 10; i++) {
  if (i === 5) break;
  console.log(i);  // 0 1 2 3 4
}

// continue：跳过本次迭代，继续下一次
for (let i = 0; i < 5; i++) {
  if (i === 2) continue;
  console.log(i);  // 0 1 3 4
}

// 带标签的 break：跳出多层嵌套循环
outer: for (let i = 0; i < 3; i++) {
  for (let j = 0; j < 3; j++) {
    if (i === 1 && j === 1) break outer;  // 跳出外层循环
    console.log(i, j);
  }
}
```

---

### 4.8 try...catch 异常处理

> 难度：intermediate | topic_code: js_error_handling

```javascript
try {
  const result = riskyOperation();
  console.log("成功:", result);
} catch (error) {
  console.error("捕获到错误:", error.message);
  console.error("错误类型:", error.name);     // TypeError / ReferenceError / SyntaxError...
  console.error("错误栈:", error.stack);
} finally {
  // 无论成功失败都执行，常用于清理资源
  console.log("清理工作");
}

// 抛出错误
function divide(a, b) {
  if (b === 0) throw new Error("除数不能为0");
  return a / b;
}
```

---

## 本章小结

- 用 if/else 做条件分支，switch 处理多值匹配
- for 循环知道次数，while 循环靠条件
- for...of 遍历数组的值，for...in 遍历对象的键
- break 终止循环，continue 跳过当前迭代
- try...catch 捕获异常，finally 做清理

## 扩展阅读

- MDN 流程控制：https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Guide/Control_flow_and_error_handling
