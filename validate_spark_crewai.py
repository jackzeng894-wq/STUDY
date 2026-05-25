"""
验证脚本：测试讯飞星火 OpenAI 兼容接口 + CrewAI 兼容性
========================================================
目标：
  1. 确认讯飞星火 OpenAI 兼容接口能正常调用
  2. 确认 CrewAI 能用星火作为 LLM 创建 Agent 并推理

使用方法：
  # 设置环境变量
  export SPARK_API_KEY="your_api_key_here"

  # 或者在同目录下创建 .env 文件：
  # SPARK_API_KEY=your_api_key_here

  # 运行验证
  python validate_spark_crewai.py
"""

import os
import sys

# 尝试从 .env 加载
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 未安装，跳过

SPARK_API_KEY = os.getenv("SPARK_API_KEY")
SPARK_API_BASE = os.getenv("SPARK_API_BASE", "https://spark-api-open.xf-yun.com/v1")
SPARK_MODEL = os.getenv("SPARK_MODEL", "4.0Ultra")


def check_config():
    """检查配置"""
    print("=" * 60)
    print("[STEP] 第0步：检查配置")
    print("=" * 60)

    if not SPARK_API_KEY:
        print("[FAIL] 错误：SPARK_API_KEY 未设置！")
        print()
        print("请通过以下方式之一设置：")
        print('  1. 环境变量: export SPARK_API_KEY="your_key"')
        print("  2. 创建 .env 文件: SPARK_API_KEY=your_key")
        print()
        print("讯飞星火 API Key 获取地址：")
        print("  https://console.xfyun.cn/services/spark")
        return False

    print(f"  API Base: {SPARK_API_BASE}")
    print(f"  Model: {SPARK_MODEL}")
    print(f"  API Key: {SPARK_API_KEY[:8]}...{SPARK_API_KEY[-4:]}")
    print("[OK] 配置检查通过")
    print()
    return True


def test_raw_openai_api():
    """第1步：测试原始 OpenAI 兼容 API 调用"""
    print("=" * 60)
    print("[TEST] 第1步：测试讯飞星火 OpenAI 兼容 API（原生调用）")
    print("=" * 60)

    try:
        from openai import OpenAI
    except ImportError:
        print("[FAIL] 请先安装 openai: pip install openai")
        return False

    client = OpenAI(
        api_key=SPARK_API_KEY,
        base_url=SPARK_API_BASE,
    )

    try:
        response = client.chat.completions.create(
            model=SPARK_MODEL,
            messages=[
                {"role": "system", "content": "你是一位JavaScript教学助手。"},
                {"role": "user", "content": "用一句话解释什么是闭包。"},
            ],
            max_tokens=200,
            temperature=0.7,
            stream=False,
        )

        answer = response.choices[0].message.content
        print(f"  提问：用一句话解释什么是闭包。")
        print(f"  回答：{answer}")
        print(f"  Token 使用：{response.usage}")
        print("[OK] 原生 OpenAI API 调用成功！")
        print()
        return True

    except Exception as e:
        print(f"[FAIL] API 调用失败：{e}")
        print()
        print("常见排查：")
        print("  1. API Key 是否正确？")
        print("  2. API Base URL 是否正确？")
        print("     - 星火4.0: https://spark-api-open.xf-yun.com/v1")
        print("     - 星火3.5: https://spark-api-open.xf-yun.com/v1")
        print("  3. 是否有余额/配额？")
        print("  4. 是否需要先在控制台开通 OpenAI 兼容接口？")
        return False


def test_raw_openai_stream():
    """第2步：测试流式输出"""
    print("=" * 60)
    print("[TEST] 第2步：测试讯飞星火 流式输出（Streaming）")
    print("=" * 60)

    from openai import OpenAI
    client = OpenAI(
        api_key=SPARK_API_KEY,
        base_url=SPARK_API_BASE,
    )

    try:
        stream = client.chat.completions.create(
            model=SPARK_MODEL,
            messages=[
                {"role": "user", "content": "用3句话介绍JavaScript的事件循环。"},
            ],
            max_tokens=300,
            temperature=0.7,
            stream=True,
        )

        print("  回答（流式）: ", end="", flush=True)
        full_text = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                print(text, end="", flush=True)
                full_text += text
        print()
        print(f"  总长度：{len(full_text)} 字符")
        print("[OK] 流式输出成功！")
        print()
        return True

    except Exception as e:
        print(f"[FAIL] 流式调用失败：{e}")
        return False


def test_crewai_agent():
    """第3步：测试 CrewAI Agent 使用星火 LLM"""
    print("=" * 60)
    print("[TEST] 第3步：测试 CrewAI + 讯飞星火（创建 Agent + 执行任务）")
    print("=" * 60)

    try:
        from crewai import Agent, Task, Crew, LLM
    except ImportError:
        print("[FAIL] 请先安装 crewai: pip install crewai")
        print("   如果安装失败，可能需要：pip install 'crewai[tools]'")
        return False

    try:
        # 创建星火 LLM 实例（通过 OpenAI 兼容接口）
        spark_llm = LLM(
            model=f"openai/{SPARK_MODEL}",
            base_url=SPARK_API_BASE,
            api_key=SPARK_API_KEY,
            temperature=0.7,
        )

        print("  创建 LLM 实例... [OK]")

        # 创建简单 Agent
        tutor = Agent(
            role="JavaScript教学助手",
            goal="用通俗易懂的方式解释JavaScript概念",
            backstory="你是一位经验丰富的编程教师，擅长用例子解释复杂概念。",
            llm=spark_llm,
            verbose=False,
        )

        print("  创建 Agent... [OK]")

        # 创建 Task
        task = Task(
            description="用中文简要解释JavaScript的let和const的区别，控制在100字以内。",
            expected_output="一段简洁的中文解释，说明let和const的区别。",
            agent=tutor,
        )

        print("  创建 Task... [OK]")

        # 创建 Crew 并执行
        crew = Crew(
            agents=[tutor],
            tasks=[task],
            verbose=False,
        )

        print("  执行 Crew...", end=" ", flush=True)
        result = crew.kickoff()
        print("[OK]")
        print(f"  Agent 回答：{str(result)}")
        print("[OK] CrewAI + 星火集成测试成功！")
        print()
        return True

    except Exception as e:
        print(f"[FAIL] CrewAI 测试失败：{e}")
        print()
        print("常见排查：")
        print("  1. CrewAI 版本是否支持 LLM() 的 base_url 参数？")
        print("  2. model 命名格式是否正确？(openai/model_name)")
        print("  3. 星火 OpenAI 兼容接口是否支持 /chat/completions？")
        return False


def test_crewai_tool_use():
    """第4步：测试 Agent 使用工具（进阶验证）"""
    print("=" * 60)
    print("[TEST] 第4步：测试 CrewAI Agent + 工具调用")
    print("=" * 60)

    from crewai import Agent, Task, Crew, LLM
    from crewai.tools import tool

    # 定义一个简单工具
    @tool("get_js_version")
    def get_js_version(query: str) -> str:
        """查询 JavaScript 版本信息。当被问到 JS 版本时使用。"""
        return "ECMAScript 2024 (ES15) 是最新标准，发布于2024年6月。ES6 (ECMAScript 2015) 是最大的更新。当前主流浏览器支持 ES2023。"

    try:
        spark_llm = LLM(
            model=f"openai/{SPARK_MODEL}",
            base_url=SPARK_API_BASE,
            api_key=SPARK_API_KEY,
            temperature=0.3,
        )

        agent = Agent(
            role="JavaScript信息助手",
            goal="准确回答JavaScript相关问题",
            backstory="你是一个JavaScript知识库助手，可以查询JS版本和特性信息。",
            tools=[get_js_version],
            llm=spark_llm,
            verbose=False,
        )

        task = Task(
            description="用户问：JavaScript最新版本是什么？请用工具查询后回答。",
            expected_output="包含JavaScript版本信息的回答。",
            agent=agent,
        )

        crew = Crew(agents=[agent], tasks=[task], verbose=False)

        print("  执行 Agent + 工具...", end=" ", flush=True)
        result = crew.kickoff()
        print("[OK]")
        print(f"  回答：{str(result)}")
        print("[OK] Agent 工具调用测试成功！")
        print()
        return True

    except Exception as e:
        print(f"[WARN] 工具调用测试失败：{e}")
        print("  （这一步失败不影响基本使用，工具调用是进阶功能）")
        print()
        return False  # 工具调用失败不算致命


def main():
    print()
    print("[==========================================================]")
    print("|  讯飞星火 + CrewAI 兼容性验证                           |")
    print("|  项目：基于大模型的个性化学习智能体系统                   |")
    print("[==========================================================]")
    print()

    if not check_config():
        sys.exit(1)

    results = {}

    # 第1步：原生API调用（必须先过）
    results["原生API"] = test_raw_openai_api()
    if not results["原生API"]:
        print("=" * 60)
        print("[FAIL] 第1步失败了。后面的测试没有意义，请先解决 API 连通性问题。")
        print("=" * 60)
        sys.exit(1)

    # 第2步：流式输出（重要，SSE的基础）
    results["流式输出"] = test_raw_openai_stream()

    # 第3步：CrewAI Agent（核心验证）
    results["CrewAI Agent"] = test_crewai_agent()

    # 第4步：工具调用（加分）
    results["Agent工具调用"] = test_crewai_tool_use()

    # 总结
    print("=" * 60)
    print("[TEST] 验证结果总结")
    print("=" * 60)
    for step, success in results.items():
        icon = "[OK]" if success else "[WARN]"
        status = "通过" if success else "未通过"
        print(f"  {icon} {step}: {status}")

    required = ["原生API", "流式输出", "CrewAI Agent"]
    all_required_pass = all(results.get(r, False) for r in required)

    print()
    if all_required_pass:
        print("[OK] 所有核心验证通过！可以开始搭建项目。")
        print()
        print("  下一步：")
        print("    1. 初始化后端项目骨架")
        print("    2. 编写知识库")
        print("    3. 实现 RAG 管线")
    else:
        print("[WARN] 部分核心验证未通过，搭建项目前请先解决上述问题。")

    print()


if __name__ == "__main__":
    main()
