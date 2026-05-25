# 第6章 对象与数组

> 难度：intermediate | 预计学习时间：150分钟 | 11个知识点

## 学习目标

- 掌握对象的基础操作和 this 的指向规则
- 掌握解构赋值和展开运算符
- 熟练使用 map/filter/reduce 三大数组方法
- 理解 Map/Set 与普通对象/数组的区别
- 了解 Proxy 和可迭代协议

---

## 知识点详解

### 6.1 对象基础

> 难度：beginner | topic_code: js_object_basics

```javascript
// 创建对象
const user = {
  name: "张三",
  age: 20,
  "full-name": "张三丰",  // 特殊属性名需要引号
  greet() {               // 方法简写（ES6）
    return `你好，我是${this.name}`;
  }
};

// 访问属性
console.log(user.name);            // "张三"（点号）
console.log(user["full-name"]);    // "张三丰"（方括号，支持特殊字符）
const key = "age";
console.log(user[key]);            // 20（动态属性名用方括号）

// 属性存在性检查
console.log("name" in user);       // true
console.log(user.hasOwnProperty("name")); // true
console.log(Object.hasOwn(user, "name")); // ES2022 推荐写法

// 遍历对象
Object.keys(user);      // ["name", "age", "full-name", "greet"]
Object.values(user);    // ["张三", 20, "张三丰", function()...]
Object.entries(user);   // [["name","张三"], ["age",20], ...]
```

---

### 6.2 对象方法与 this

> 难度：intermediate | topic_code: js_object_methods

```javascript
// this 的指向由调用方式决定，不由定义位置决定
const obj = {
  name: "obj",
  showThis() {
    console.log(this.name);
  }
};

obj.showThis();  // "obj"（方法调用，this 指向 obj）

const fn = obj.showThis;
fn();  // undefined（普通函数调用，this → undefined，严格模式）
       // 非严格模式 this → window / global

// 箭头函数的 this：继承定义时的外层 this
const obj2 = {
  name: "obj2",
  showThis: () => {
    console.log(this.name);  // this 是外层作用域的 this，不是 obj2
  }
};
obj2.showThis();  // undefined（箭头函数没有自己的 this）
```

---

### 6.3-6.4 解构赋值与展开运算符

> 难度：intermediate | topic_code: js_destructuring / js_spread

```javascript
// 对象解构
const { name, age, email = "未填写" } = user;
// name = "张三", age = 20, email = "未填写"

const { name: userName } = user;  // 重命名：userName = "张三"

// 数组解构
const [first, second, ...rest] = [1, 2, 3, 4, 5];
// first = 1, second = 2, rest = [3, 4, 5]

// 交换变量（不用中间变量！）
let a = 1, b = 2;
[a, b] = [b, a];  // a = 2, b = 1

// 展开运算符 ...
const arr1 = [1, 2];
const arr2 = [3, 4];
const merged = [...arr1, ...arr2];  // [1, 2, 3, 4]

const objA = { x: 1, y: 2 };
const objB = { y: 3, z: 4 };
const mergedObj = { ...objA, ...objB };  // { x: 1, y: 3, z: 4 }（后面的覆盖前面的）
```

---

### 6.5-6.6 数组与三大方法

> 难度：beginner-intermediate | topic_code: js_array_basics / js_array_methods

```javascript
// 数组基础
const arr = [1, 2, 3];
arr.push(4);       // [1,2,3,4] 末尾添加
arr.pop();         // [1,2,3]   末尾删除
arr.unshift(0);    // [0,1,2,3] 开头添加
arr.shift();       // [1,2,3]   开头删除
arr.splice(1, 1);  // [1,3]     删除索引1处的1个元素

// 三大方法：map 变换 / filter 筛选 / reduce 聚合
const nums = [1, 2, 3, 4, 5];

// map：每个元素映射为新值
nums.map(x => x * 2);        // [2, 4, 6, 8, 10]

// filter：筛选满足条件的元素
nums.filter(x => x % 2 === 0); // [2, 4]

// reduce：累积计算
nums.reduce((sum, x) => sum + x, 0);  // 15

// 链式调用：获取所有偶数的平方
nums.filter(x => x % 2 === 0).map(x => x * x);  // [4, 16]

// 其他常用方法
nums.find(x => x > 3);      // 4（第一个匹配的元素）
nums.findIndex(x => x > 3); // 3（第一个匹配的索引）
nums.some(x => x > 3);      // true（有满足条件的吗）
nums.every(x => x < 10);    // true（所有都满足吗）
nums.flatMap(x => [x, x * 2]); // [1,2,2,4,3,6,4,8,5,10]
```

---

### 6.7-6.8 Map / Set / WeakMap

> 难度：intermediate-advanced | topic_code: js_map_set / js_weakmap

```javascript
// Map：键可以是任意类型
const map = new Map();
map.set("name", "张三");
map.set(obj, "关联数据");  // 对象作为键！
map.set(NaN, "value");   // Map 中 NaN === NaN
console.log(map.size);   // 3
console.log(map.get("name")); // "张三"
map.has("name");  // true
map.delete("name");
// 遍历
for (const [key, value] of map) { console.log(key, value); }

// Set：自动去重的集合
const set = new Set([1, 2, 2, 3, 3, 3]);
console.log(set);  // Set { 1, 2, 3 }
set.add(4);
set.has(2);  // true
// 数组去重一行代码：
const unique = [...new Set([1,2,2,3,3,3])];  // [1,2,3]
```

WeakMap 的键必须是对象，且是**弱引用**（不阻止垃圾回收），用于存储关联的元数据：
```javascript
const wm = new WeakMap();
let obj = { id: 1 };
wm.set(obj, "元数据");
obj = null;  // obj 可以被垃圾回收，WeakMap 中的条目自动消失
```

---

### 6.9 JSON 序列化

> 难度：beginner | topic_code: js_json

```javascript
const obj = { name: "张三", age: 20, skills: ["JS", "HTML"] };

// 序列化
const json = JSON.stringify(obj);
// '{"name":"张三","age":20,"skills":["JS","HTML"]}'

JSON.stringify(obj, null, 2);  // 格式化（2空格缩进）

// 反序列化
const parsed = JSON.parse(json);

// JSON 的限制：
// 不能序列化 undefined / Symbol / function / 循环引用
// Date 会转为字符串，RegExp 会转为空对象 {}
```

---

### 6.10-6.11 Proxy 与可迭代对象

> 难度：advanced | topic_code: js_proxy_reflect / js_iterable

```javascript
// Proxy：拦截对象的基本操作
const target = { name: "张三", age: 20 };
const handler = {
  get(obj, prop) {
    console.log(`读取属性: ${String(prop)}`);
    return prop in obj ? obj[prop] : `属性 ${String(prop)} 不存在`;
  },
  set(obj, prop, value) {
    if (prop === "age" && typeof value !== "number") {
      throw new TypeError("age 必须是数字");
    }
    obj[prop] = value;
    return true;
  }
};
const proxy = new Proxy(target, handler);
proxy.name;     // 输出: "读取属性: name"
proxy.age = 25; // 正常
// proxy.age = "25"; // TypeError!

// 可迭代协议：实现 [Symbol.iterator] 方法让对象可被 for...of 遍历
const range = {
  from: 1,
  to: 5,
  [Symbol.iterator]() {
    let current = this.from;
    const last = this.to;
    return {
      next() {
        return current <= last
          ? { value: current++, done: false }
          : { value: undefined, done: true };
      }
    };
  }
};
for (const num of range) { console.log(num); }  // 1 2 3 4 5
```

---

## 本章小结

- 普通对象用点号/方括号访问，深层次用可选链 `?.`
- this 指向**调用者**（谁调用就指向谁），箭头函数没有自己的 this
- map/filter/reduce 是数组三剑客，学会链式调用
- Map 的键可以是任意类型，Set 自动去重
- Proxy 可以拦截几乎所有对象操作

## 扩展阅读

- MDN 数组方法：https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Reference/Global_Objects/Array
- MDN Proxy：https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Reference/Global_Objects/Proxy
