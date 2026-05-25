/**
 * 闭包 (Closure) 经典示例
 * 演示：函数 + 其引用的外部变量 = 闭包
 */

// 示例1：计数器（数据私有化）
function createCounter(initial = 0) {
  let count = initial;           // 被"封闭"在内部的变量
  return {
    increment: () => ++count,
    decrement: () => --count,
    get: () => count,
    reset: () => { count = initial; }
  };
}

const counter = createCounter(10);
console.log(counter.increment()); // 11
console.log(counter.increment()); // 12
console.log(counter.decrement()); // 11
console.log(counter.get());       // 11
// console.log(count);            // ReferenceError! 外部无法访问

// 示例2：循环中的闭包问题与解决方案
console.log("\n=== var 的坑 ===");
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log(`var i = ${i}`), 100);
}
// 输出：var i = 3 (三遍)

setTimeout(() => {
  console.log("\n=== let 的解决方案 ===");
  for (let j = 0; j < 3; j++) {
    setTimeout(() => console.log(`let j = ${j}`), 100);
  }
  // 输出：let j = 0  let j = 1  let j = 2
}, 200);
