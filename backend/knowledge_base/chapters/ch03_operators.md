# 第3章 运算符与表达式

> 难度：beginner | 预计学习时间：90分钟 | 8个知识点

## 学习目标

- 掌握算术、比较、逻辑三类核心运算符
- 理解 `===` 与 `==` 的区别
- 掌握短路求值的应用场景
- 学会使用可选链(?.)和空值合并(??)
- 了解运算符优先级

---

## 知识点详解

### 3.1 算术运算符

> 难度：beginner | topic_code: js_arithmetic

| 运算符 | 含义 | 示例 |
|--------|------|------|
| `+` | 加法 / 字符串拼接 | `5 + 3 → 8` / `"a" + "b" → "ab"` |
| `-` | 减法 | `10 - 3 → 7` |
| `*` | 乘法 | `4 * 5 → 20` |
| `/` | 除法 | `10 / 3 → 3.333...` |
| `%` | 取余（模） | `10 % 3 → 1` |
| `**` | 指数（ES7） | `2 ** 10 → 1024` |
| `++` / `--` | 自增/自减 | `i++` / `++i` |

```javascript
// 前置 vs 后置：关键区别
let a = 1;
console.log(a++);  // 1（先返回再自增）
console.log(a);    // 2

let b = 1;
console.log(++b);  // 2（先自增再返回）

// + 运算符的双重身份
console.log(1 + 2);       // 3（两边都是数字，做加法）
console.log("1" + 2);     // "12"（有一边是字符串，转为拼接）
console.log("1" + "2");   // "12"
```

---

### 3.2 比较运算符与相等性

> 难度：beginner | topic_code: js_comparison

```javascript
// 大小比较
5 > 3;     // true
5 >= 5;    // true
3 < 5;     // true

// 相等性：== 会做类型转换，=== 不会
5 == "5";   // true  (字符串"5"被转为数字5)
5 === "5";  // false (类型不同，直接返回false)
0 == false; // true  (false被转为0)
0 === false; // false

// 特殊值的比较
NaN === NaN;          // false！NaN 不等于任何值，包括自己
Number.isNaN(NaN);    // true  正确判断 NaN 的方式
Object.is(NaN, NaN);  // true  更精确的比较
Object.is(0, -0);     // false 能区分 +0 和 -0
```

> 核心原则：永远用 `===`，永远用 `===`，永远用 `===`。

---

### 3.3 逻辑运算符与短路求值

> 难度：intermediate | topic_code: js_logical

```javascript
// 逻辑与 &&：全真才真
true && true;    // true
true && false;   // false

// 逻辑或 ||：有真即真
true || false;   // true
false || false;  // false

// 逻辑非 !
!true;           // false
!!"hello";       // true（双重否定转布尔）

// 短路求值：&& 遇假即停，|| 遇真即停
// 实用模式：
const name = userInput || "默认名称";     // 提供默认值（注意：0和""会被跳过）
const name2 = userInput ?? "默认名称";    // ?? 只在 null/undefined 时用默认值

const user = isLoggedIn && getUserInfo(); // 条件执行：只有 isLoggedIn 为 true 才调用
obj && obj.method && obj.method();        // 安全调用（现代写法：obj?.method?.()）
```

---

### 3.4 位运算符

> 难度：intermediate | topic_code: js_bitwise

位运算符直接操作 32 位二进制，平时较少使用，但某些场景性能极高：

| 运算符 | 含义 | 用途示例 |
|--------|------|----------|
| `&` | 按位与 | 权限掩码 |
| `|` | 按位或 | 标志位合并 |
| `^` | 按位异或 | 简单加密 |
| `~` | 按位非 | 判断 indexOf |
| `<<` / `>>` | 左移/右移 | 乘除2^n |
| `>>>` | 无符号右移 | - |

```javascript
// 实用技巧1：取整（只对32位整数有效）
console.log(3.7 | 0);       // 3
console.log(-3.7 | 0);      // -3

// 实用技巧2：判断奇偶
console.log(5 & 1);         // 1（奇数）
console.log(4 & 1);         // 0（偶数）

// 实用技巧3：~ 配合 indexOf（-1 变 0）
if (~[1,2,3].indexOf(2)) { /* 找到了 */ }
```

---

### 3.5 三元运算符

> 难度：beginner | topic_code: js_ternary

```javascript
// 语法：条件 ? 真时值 : 假时值
const age = 20;
const type = age >= 18 ? "成年人" : "未成年人";

// 可以链式（但不要太长，影响可读性）
const grade = score >= 90 ? "A" : score >= 80 ? "B" : score >= 60 ? "C" : "D";

// 对比：if-else vs 三元
// 赋值时用三元更简洁：
const msg = isLoggedIn ? `欢迎回来，${username}` : "请先登录";

// 执行操作用 if（不要用三元做副作用）：
// 不推荐：isLoggedIn ? showDashboard() : redirectToLogin();
// 推荐：
if (isLoggedIn) {
  showDashboard();
} else {
  redirectToLogin();
}
```

---

### 3.6 空值合并运算符 (??)

> 难度：intermediate | topic_code: js_nullish

`??` 只在左侧是 `null` 或 `undefined` 时取右侧值，区别于 `||` 的假值判断：

```javascript
// || 的问题：把合法值当作"假"
const count = 0;
console.log(count || 10);    // 10（0 被当作 false！）
console.log(count ?? 10);    // 0（正确！0 是合法值）

const name = "";
console.log(name || "匿名");  // "匿名"（空字符串被当作 false！）
console.log(name ?? "匿名");  // ""（正确！空字符串是合法值）

// 结论：提供默认值时，优先用 ??，除非你明确想过滤空字符串和0
```

---

### 3.7 可选链操作符 (?.)

> 难度：intermediate | topic_code: js_optional_chaining

`?.` 安全访问深层嵌套的属性，遇 null/undefined 返回 undefined 而不报错：

```javascript
const user = {
  name: "张三",
  address: {
    city: "北京"
  }
};

// 旧写法：层层判断
const city = user && user.address && user.address.city;

// 新写法：可选链
const city2 = user?.address?.city;        // "北京"
const street = user?.address?.street;     // undefined（不会报错！）
const postal = user?.contact?.postal;     // undefined（contact 不存在，不会报错）

// 可选链也支持方法和数组：
obj?.method?.();     // 方法存在才调用
arr?.[0];            // 安全的数组索引
```

---

### 3.8 运算符优先级

> 难度：intermediate | topic_code: js_operator_precedence

不要求全部记住，但需要知道基本顺序（从高到低）：

1. `()` 括号
2. `!` `++` `--` 一元
3. `*` `/` `%` 乘除
4. `+` `-` 加减
5. `>` `<` `>=` `<=` 比较
6. `===` `!==` `==` `!=` 相等
7. `&&` 逻辑与
8. `||` 逻辑或
9. `??` 空值合并
10. `=` 赋值

```javascript
// 不确定优先级时，直接加括号
const result = (a && b) || (c && d);  // 清晰明了
```

---

## 本章小结

- `===` 严格比较，`==` 有隐式转换陷阱
- `??` 提供默认值比 `||` 更安全（不会误判 0 和 ""）
- `?.` 可选链让深层属性访问更安全
- 不确定优先级就加括号

## 扩展阅读

- MDN 运算符优先级表：https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Reference/Operators/Operator_Precedence
