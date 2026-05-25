# 第8章 异步编程

> 难度：advanced | 预计学习时间：180分钟 | 10个知识点

## 学习目标

- 理解同步与异步的本质区别
- 掌握 Promise 的创建、链式调用和错误处理
- 熟练使用 async/await 编写异步代码
- **深入理解事件循环机制（Event Loop）**
- 区分微任务与宏任务，理解执行顺序

---

## 知识点详解

### 8.1 同步与异步概念

> 难度：beginner | topic_code: js_async_intro

JavaScript 是**单线程**语言，一次只能做一件事。如果某个操作耗时很长（如网络请求），同步执行会卡死页面。异步机制解决了这个问题。

```javascript
// 同步：逐行执行，前一行完成才执行下一行
console.log("第一步");
const result = heavyCalculation();  // 假设耗时 3 秒
console.log(result);
console.log("这一步要等 3 秒才能输出");

// 异步：启动任务后不等待，继续执行
console.log("第一步");
fetch("https://api.example.com/data")  // 发起网络请求
  .then(res => console.log("数据到了"));
console.log("第二步（不会等待网络请求）");
// 输出顺序：第一步 → 第二步 → 数据到了
```

---

### 8.2-8.5 Promise

> 难度：intermediate | topic_code: js_promise / js_promise_chain / js_promise_methods

Promise 表示一个**将来会完成（或失败）**的异步操作：

```javascript
// 创建 Promise
const promise = new Promise((resolve, reject) => {
  setTimeout(() => {
    const success = Math.random() > 0.3;  // 70% 成功率
    if (success) {
      resolve("成功了！");
    } else {
      reject(new Error("失败了！"));
    }
  }, 1000);
});

// 消费 Promise：链式调用
fetch("/api/user")
  .then(response => response.json())     // 解析 JSON
  .then(user => fetch(`/api/posts/${user.id}`))  // 第二个请求
  .then(response => response.json())
  .then(posts => console.log(posts))
  .catch(error => console.error("出错了:", error))
  .finally(() => console.log("请求结束（成功或失败都执行）"));

// Promise 静态方法
Promise.all([p1, p2, p3]);           // 全部成功 → 成功，有任一失败 → 失败
Promise.allSettled([p1, p2, p3]);    // 全部完成（不论成功失败），{status, value|reason}[]
Promise.race([p1, p2, p3]);          // 第一个完成的（不论成功失败）
Promise.any([p1, p2, p3]);           // 第一个成功的，全失败才 reject
Promise.resolve(value);              // 创建已成功的 Promise
Promise.reject(error);               // 创建已失败的 Promise
```

---

### 8.6 async / await

> 难度：intermediate | topic_code: js_async_await

async/await 是 Promise 的语法糖，让异步代码**看起来像同步代码**：

```javascript
// Promise 链写法
function getUserPosts(userId) {
  return fetch(`/api/users/${userId}`)
    .then(res => res.json())
    .then(user => fetch(`/api/posts?userId=${user.id}`))
    .then(res => res.json());
}

// async/await 写法：更直观
async function getUserPosts(userId) {
  const userRes = await fetch(`/api/users/${userId}`);
  const user = await userRes.json();
  const postsRes = await fetch(`/api/posts?userId=${user.id}`);
  const posts = await postsRes.json();
  return posts;
}

// async 函数始终返回 Promise
async function foo() { return 42; }
foo().then(v => console.log(v));  // 42
```

---

### 8.7 异步错误处理

> 难度：intermediate | topic_code: js_async_error

```javascript
// async/await 错误处理：用 try...catch
async function fetchData() {
  try {
    const response = await fetch("/api/data");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("获取数据失败:", error.message);
    return null;  // 返回安全的默认值
  }
}

// Promise 中未捕获的 rejection 会导致 UnhandledPromiseRejectionWarning
// 永远记得加 .catch() 或 try...catch
```

---

### 8.8-8.9 事件循环 (Event Loop) 与任务队列

> 难度：advanced | topic_code: js_event_loop / js_micro_macro

这是 JavaScript 面试中最高频的概念：

**事件循环工作流程**：
1. 执行**调用栈**中的所有同步代码
2. 调用栈清空后，检查**微任务队列**
3. 执行**所有**微任务（一个不剩），微任务执行过程中产生的新微任务也会被处理
4. 从**宏任务队列**取出**一个**宏任务执行
5. 重复 2-4

| 类型 | 包含 | 优先级 |
|------|------|--------|
| 宏任务 (MacroTask) | setTimeout, setInterval, I/O, UI渲染 | **低**（每次只取一个） |
| 微任务 (MicroTask) | Promise.then/catch/finally, queueMicrotask, MutationObserver | **高**（清空整个队列） |

```javascript
// 经典面试题：输出顺序是什么？
console.log("1");

setTimeout(() => console.log("2"), 0);

Promise.resolve()
  .then(() => console.log("3"))
  .then(() => console.log("4"));

console.log("5");

// 答案：1 → 5 → 3 → 4 → 2
// 解释：
//   同步代码：1, 5
//   微任务队列：3, 4（Promise.then）
//   宏任务队列：2（setTimeout）
```

```javascript
// 进阶：async/await 中的微任务
async function foo() {
  console.log("A");
  await bar();         // await = Promise.then() 的语法糖
  console.log("B");    // 这部分是微任务！
}
async function bar() { console.log("C"); }
console.log("D");
foo();
console.log("E");
// 输出：D → A → C → E → B
// 解释：await bar() 之后的代码 (console.log("B")) 被包装为微任务
```

---

### 8.10 异步编程模式总结

> 难度：intermediate | topic_code: js_async_patterns

| 模式 | 时代 | 特点 | 当前推荐 |
|------|------|------|----------|
| 回调函数 | ES5之前 | 简单但是容易"地狱嵌套" | 不推荐（除非事件监听） |
| Promise | ES6 | 链式调用，统一错误处理 | 适合组合操作 |
| async/await | ES2017 | 像同步代码一样写异步 | **日常首选** |
| 事件监听 | 始终可用 | 观察者模式 | UI 交互场景 |

```javascript
// 推荐写法：async/await + Promise.all 并发
async function loadDashboard() {
  const [user, posts, notifications] = await Promise.all([
    fetchUser(),
    fetchPosts(),
    fetchNotifications()
  ]);
  return { user, posts, notifications };
}
```

---

## 本章小结

- Promise 代表异步操作的最终结果，链式调用用 then/catch
- async/await 让异步代码可读性接近同步代码，日常首选
- 事件循环执行顺序：**同步代码 → 全部微任务 → 一个宏任务 → 全部微任务 → ...**
- Promise.then/await 之后的内容是微任务，setTimeout 是宏任务

## 扩展阅读

- Jake Archibald: In The Loop (JSConf.Asia) — 讲事件循环最好的演讲
- MDN 异步编程：https://developer.mozilla.org/zh-CN/docs/Learn/JavaScript/Asynchronous
