# 第9章 DOM 与浏览器 API

> 难度：intermediate | 预计学习时间：120分钟 | 10个知识点

## 学习目标

- 理解 DOM 树结构和节点关系
- 掌握 DOM 选择、增删、修改、样式操作
- 理解事件模型、冒泡/捕获、事件委托
- 掌握定时器和 Web Storage
- 熟练使用 Fetch API

---

## 知识点详解

### 9.1-9.3 DOM 基础操作

> 难度：beginner | topic_code: js_dom_tree / js_dom_select / js_dom_modify

```javascript
// DOM 选择器
document.getElementById("app");
document.querySelector(".class-name");     // 返回第一个匹配
document.querySelectorAll(".item");         // 返回 NodeList（类数组）
element.querySelector("span");             // 在 element 内部查找

// DOM 增删改
const div = document.createElement("div");  // 创建
div.textContent = "Hello";                  // 设置文本（安全，自动转义）
div.innerHTML = "<strong>Hello</strong>";   // 设置 HTML（注意 XSS 风险！）
div.classList.add("active");                // 添加 class
div.setAttribute("data-id", "123");         // 设置属性
parent.appendChild(div);                    // 添加到父节点末尾
parent.insertBefore(div, referenceNode);   // 插入到参考节点之前
div.remove();                               // 删除自身（现代 API）
parent.removeChild(div);                    // 删除子节点（旧 API）
```

---

### 9.4 DOM 样式操作

> 难度：beginner | topic_code: js_dom_style

```javascript
// 内联样式（优先级最高，但耦合度高）
element.style.backgroundColor = "red";
element.style.transform = "translateX(100px)";

// class 操作（推荐！样式与逻辑分离）
element.classList.add("highlight");
element.classList.remove("hidden");
element.classList.toggle("dark");
element.classList.contains("active");  // true/false

// 读取计算后的样式
const styles = getComputedStyle(element);
console.log(styles.width);      // 实际渲染宽度（含 CSS 中的值）
console.log(styles.fontSize);   // "16px"
```

---

### 9.5-9.7 事件模型

> 难度：intermediate | topic_code: js_events / js_event_bubbling / js_event_delegation

```javascript
// 事件监听
element.addEventListener("click", (event) => {
  console.log("点击了", event.target);
  console.log("事件类型:", event.type);
  console.log("坐标:", event.clientX, event.clientY);
});

// 事件传播三阶段：捕获 → 目标 → 冒泡
// addEventListener 第三个参数：
//   false（默认）：冒泡阶段触发
//   true：捕获阶段触发
parent.addEventListener("click", handler, true);    // 捕获阶段
child.addEventListener("click", handler, false);    // 冒泡阶段（默认）

// 阻止事件传播
event.stopPropagation();    // 阻止继续冒泡/捕获
event.stopImmediatePropagation(); // 阻止同级其他监听器
event.preventDefault();     // 阻止默认行为（链接跳转、表单提交等）

// 事件委托：利用冒泡，在父元素上监听所有子元素的事件
// 优点：减少监听器数量，动态添加的元素也能响应
document.getElementById("list").addEventListener("click", (event) => {
  if (event.target.matches("li")) {
    console.log("点击了:", event.target.textContent);
  }
});
```

---

### 9.8 定时器

> 难度：beginner | topic_code: js_timers

```javascript
// setTimeout：延迟执行一次
const timerId = setTimeout(() => {
  console.log("1 秒后执行");
}, 1000);
clearTimeout(timerId);  // 取消

// setInterval：每间隔 N 毫秒重复执行
const intervalId = setInterval(() => {
  console.log("每 2 秒执行一次");
}, 2000);
clearInterval(intervalId); // 停止

// 注意：定时器的时间不是精确的，是最小延迟时间。
// 如果主线程繁忙，实际延迟会>设定值。
// setTimeout(..., 0) 不是立即执行，而是把任务加入宏任务队列。
```

---

### 9.9 Web Storage

> 难度：beginner | topic_code: js_storage

```javascript
// localStorage：持久化存储（关浏览器也不丢失）
localStorage.setItem("token", "abc123");
const token = localStorage.getItem("token");
localStorage.removeItem("token");
localStorage.clear();  // 清空所有

// sessionStorage：会话级存储（关标签页即丢失，刷新还在）
sessionStorage.setItem("tempData", JSON.stringify({ id: 1 }));

// JSON 序列化存储对象
const user = { name: "张三", age: 20 };
localStorage.setItem("user", JSON.stringify(user));
const saved = JSON.parse(localStorage.getItem("user"));

// 限制：只能存字符串，大小约 5-10MB
```

---

### 9.10 Fetch API

> 难度：intermediate | topic_code: js_fetch

```javascript
// GET 请求
const response = await fetch("/api/users");
if (!response.ok) {
  throw new Error(`HTTP ${response.status}: ${response.statusText}`);
}
const data = await response.json();

// POST 请求
const response2 = await fetch("/api/users", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name: "张三", age: 20 }),
});
const created = await response2.json();

// 上传文件
const formData = new FormData();
formData.append("avatar", fileInput.files[0]);
await fetch("/api/upload", { method: "POST", body: formData });

// 请求超时（Fetch 原生不支持超时，用 AbortController）
const controller = new AbortController();
setTimeout(() => controller.abort(), 5000);  // 5 秒超时
try {
  const res = await fetch("/api/data", { signal: controller.signal });
} catch (err) {
  if (err.name === "AbortError") console.log("请求超时");
}
```

---

## 本章小结

- 选择元素用 querySelector(All)，增删改用 appendChild/remove/createElement
- 样式操作推荐改 class 而非直接改 style
- 事件传播：捕获 → 目标 → 冒泡，利用冒泡做事件委托
- localStorage 持久化 / sessionStorage 会话级，只能存字符串
- Fetch 是现代 HTTP 请求首选，注意超时用 AbortController

## 扩展阅读

- MDN DOM 教程：https://developer.mozilla.org/zh-CN/docs/Web/API/Document_Object_Model
- MDN Fetch API：https://developer.mozilla.org/zh-CN/docs/Web/API/Fetch_API
