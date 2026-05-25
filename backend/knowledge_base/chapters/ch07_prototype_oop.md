# 第7章 原型与面向对象

> 难度：intermediate | 预计学习时间：120分钟 | 7个知识点

## 学习目标

- 理解原型链是 JavaScript 继承的底层机制
- 掌握构造函数和 new 运算符的工作流程
- 掌握 ES6 class 语法及继承
- 深入理解 this 的四种绑定规则
- 熟练使用 call / apply / bind

---

## 知识点详解

### 7.1 原型与原型链

> 难度：advanced | topic_code: js_prototype

每个 JavaScript 对象都有一个隐藏的 `[[Prototype]]` 属性（通过 `__proto__` 或 `Object.getPrototypeOf` 访问），指向它的"原型对象"。当访问对象上不存在的属性时，会沿着原型链向上查找。

```javascript
const arr = [1, 2, 3];
// arr → Array.prototype → Object.prototype → null
console.log(arr.__proto__ === Array.prototype);  // true
console.log(Array.prototype.__proto__ === Object.prototype); // true

// 验证原型链查找
const parent = { shared: "来自原型" };
const child = Object.create(parent);  // child.__proto__ → parent
child.own = "来自自身";

console.log(child.own);     // "来自自身"（在自身属性上找到）
console.log(child.shared);  // "来自原型"（沿着原型链找到）
console.log(child.unknown); // undefined（原型链到头了）
```

> 总结：**所有对象都通过原型链连接。Array → Array.prototype → Object.prototype → null**

---

### 7.2-7.3 构造函数与 class

> 难度：intermediate | topic_code: js_constructor / js_class

```javascript
// ES5 构造函数写法
function Person(name, age) {
  this.name = name;
  this.age = age;
}
Person.prototype.greet = function() {
  return `你好，我是${this.name}`;
};

// ES6 class 写法（语法糖，底层还是原型链）
class Person {
  constructor(name, age) {
    this.name = name;
    this.age = age;
  }

  greet() {
    return `你好，我是${this.name}`;
  }

  // 静态方法（类方法，实例不能调用）
  static species() {
    return "Homo Sapiens";
  }
}

const p = new Person("张三", 20);
console.log(p.greet());          // "你好，我是张三"
console.log(Person.species());   // "Homo Sapiens"
console.log(typeof Person);      // "function"（class 本质还是函数）
```

---

### 7.4 继承

> 难度：advanced | topic_code: js_inheritance

```javascript
class Animal {
  constructor(name) { this.name = name; }
  speak() { return `${this.name} 发出声音`; }
}

class Dog extends Animal {
  constructor(name, breed) {
    super(name);           // 必须调用 super() 才能使用 this
    this.breed = breed;
  }
  speak() {
    return `${super.speak()} —— 汪汪！`;  // super.method() 调用父类方法
  }
}

const dog = new Dog("旺财", "金毛");
console.log(dog.speak());  // "旺财 发出声音 —— 汪汪！"
console.log(dog instanceof Dog);    // true
console.log(dog instanceof Animal); // true
console.log(dog instanceof Object); // true
```

---

### 7.5 静态方法与私有字段

> 难度：advanced | topic_code: js_static_private

```javascript
class Counter {
  static #instances = 0;  // ES2022 静态私有字段
  #value = 0;             // ES2022 实例私有字段（用 # 前缀）

  constructor() {
    Counter.#instances++;
  }

  increment() { this.#value++; }
  get value() { return this.#value; }         // getter
  set value(v) {                              // setter
    if (v < 0) throw new Error("不能为负");
    this.#value = v;
  }

  static get instances() { return Counter.#instances; }
}
```

---

### 7.6-7.7 this 绑定规则 & call/apply/bind

> 难度：advanced | topic_code: js_this_binding / js_call_apply_bind

**this 四种绑定规则**（优先级从高到低）：

```javascript
// 1. new 绑定：this → 新创建的实例对象
function Foo() { this.name = "foo"; }
const f = new Foo();  // this → f

// 2. 显式绑定：call / apply / bind 强制指定 this
function greet(greeting) { return `${greeting}, ${this.name}`; }
const user = { name: "张三" };
greet.call(user, "你好");   // "你好, 张三"（逐个传参）
greet.apply(user, ["嗨"]);  // "嗨, 张三"（数组传参）
const bound = greet.bind(user);
bound("哈喽");              // "哈喽, 张三"（返回新函数）

// 3. 隐式绑定：obj.method()，this → obj
const obj = { name: "李四", say: greet };
obj.say("Hi");  // this → obj

// 4. 默认绑定：独立调用，this → undefined（严格模式）或 window（非严格）
const fn = obj.say;
fn("Hey");  // this → undefined（严格模式）
```

**箭头函数的 this**：不遵循以上四条规则，**继承定义时的外层 this**。

---

## 本章小结

- 原型链是 JS 继承的底层机制，class 只是语法糖
- `extends` + `super` 实现类继承
- this 指向：new > 显式绑定 > 隐式绑定 > 默认绑定，箭头函数不在此列
- bind 创建永久绑定 this 的新函数，call/apply 仅单次调用

## 扩展阅读

- MDN 原型继承：https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Inheritance_and_the_prototype_chain
- You-Dont-Know-JS: this & Object Prototypes
