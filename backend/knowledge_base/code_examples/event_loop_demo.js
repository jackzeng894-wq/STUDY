/**
 * 事件循环 (Event Loop) 演示
 * 演示：同步代码 → 微任务 → 宏任务的执行顺序
 */

console.log("=== 经典面试题：输出顺序 ===");

console.log("1");

setTimeout(() => {
  console.log("2");  // 宏任务
}, 0);

Promise.resolve()
  .then(() => {
    console.log("3");  // 微任务
  })
  .then(() => {
    console.log("4");  // 微任务
  });

console.log("5");

// 正确答案：1 → 5 → 3 → 4 → 2
// 解释：
//   同步代码：1, 5
//   清空微任务队列：3, 4
//   取一个宏任务执行：2

// === 进阶：async/await 中的微任务 ===
setTimeout(() => {
  console.log("\n=== async/await 微任务 ===");

  async function foo() {
    console.log("A");
    await bar();          // await = Promise.resolve().then(...)
    console.log("B");     // 这部分是微任务
  }

  async function bar() {
    console.log("C");
  }

  console.log("D");
  foo();
  console.log("E");
  // 答案：D → A → C → E → B
}, 200);

// === Promise 并发 ===
setTimeout(() => {
  console.log("\n=== Promise.all 并发 ===");

  async function delay(name, ms) {
    console.log(`${name} 开始`);
    await new Promise(r => setTimeout(r, ms));
    console.log(`${name} 完成 (${ms}ms)`);
    return name;
  }

  async function runAll() {
    console.time("total");
    const results = await Promise.all([
      delay("任务1", 500),
      delay("任务2", 300),
      delay("任务3", 700),
    ]);
    console.timeEnd("total");  // ~700ms（并发，不是 500+300+700）
    console.log("所有结果:", results);
  }

  runAll();
}, 400);
