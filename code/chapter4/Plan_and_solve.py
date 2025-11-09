import os
import ast
import json
from llm_client import HelloAgentsLLM
from dotenv import load_dotenv
from typing import Dict, Optional
from tools import ToolExecutor, search

# 加载 .env 文件中的环境变量，处理文件不存在异常
try:
    load_dotenv()
except FileNotFoundError:
    print("警告：未找到 .env 文件，将使用系统环境变量。")
except Exception as e:
    print(f"警告：加载 .env 文件时出错: {e}")

# --- 1. LLM客户端定义 ---
# 假设你已经有llm_client.py文件，里面定义了HelloAgentsLLM类

# --- 2. 规划器 (Planner) 定义 ---
PLANNER_PROMPT_TEMPLATE = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个Python列表, 其中每个元素都是一个描述子任务的字符串。

问题: {question}

请严格按照以下格式输出你的计划，```python与```作为前后缀是必要的:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""

class Planner:
    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def plan(self, question: str) -> list[str]:
        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)
        messages = [{"role": "user", "content": prompt}]
        
        print("--- 正在生成计划 ---")
        response_text = self.llm_client.think(messages=messages) or ""
        print(f"✅ 计划已生成:\n{response_text}")
        
        try:
            plan_str = response_text.split("```python")[1].split("```")[0].strip()
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []
        except (ValueError, SyntaxError, IndexError) as e:
            print(f"❌ 解析计划时出错: {e}")
            print(f"原始响应: {response_text}")
            return []
        except Exception as e:
            print(f"❌ 解析计划时发生未知错误: {e}")
            return []

# --- 3. 执行器 (Executor) 定义 ---
EXECUTOR_PROMPT_TEMPLATE = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
你可以使用下方的工具列表获取所需信息：
{tool_instructions}

使用工具时，请输出 JSON：{{"tool": "工具名称", "input": "工具输入"}}。
当你获得最终答案时，仅输出答案文本，不要再输出 JSON 或额外解释。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}
"""

class Executor:
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: Optional[ToolExecutor] = None, max_tool_iterations: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_tool_iterations = max_tool_iterations

    def _parse_tool_request(self, response_text: str) -> Optional[Dict[str, str]]:
        if not response_text:
            return None
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            try:
                data = ast.literal_eval(response_text)
            except (ValueError, SyntaxError):
                return None
        if isinstance(data, dict) and "tool" in data and "input" in data:
            tool_name = str(data["tool"]).strip()
            tool_input = str(data["input"])
            if tool_name:
                return {"tool": tool_name, "input": tool_input}
        return None

    def execute(self, question: str, plan: list[str]) -> str:
        history = ""
        final_answer = ""
        
        print("\n--- 正在执行计划 ---")
        for i, step in enumerate(plan, 1):
            print(f"\n-> 正在执行步骤 {i}/{len(plan)}: {step}")
            tool_instructions = (
                self.tool_executor.getAvailableTools()
                if self.tool_executor and self.tool_executor.tools
                else "（当前无可用工具）"
            )
            prompt = EXECUTOR_PROMPT_TEMPLATE.format(
                question=question,
                plan=plan,
                history=history if history else "无",
                current_step=step,
                tool_instructions=tool_instructions,
            )
            messages = [{"role": "user", "content": prompt}]
            tool_iterations = 0
            
            response_text = self.llm_client.think(messages=messages) or ""
            messages.append({"role": "assistant", "content": response_text})

            while self.tool_executor and tool_iterations < self.max_tool_iterations:
                tool_request = self._parse_tool_request(response_text)
                if not tool_request:
                    break

                tool_name = tool_request["tool"]
                tool_input = tool_request["input"]
                tool_func = self.tool_executor.getTool(tool_name)

                if not tool_func:
                    observation = f"错误：工具 '{tool_name}' 未注册。"
                else:
                    print(f"🛠️ 使用工具 '{tool_name}'，输入: {tool_input}")
                    observation = tool_func(tool_input)
                    print(f"📥 工具 '{tool_name}' 的输出: {observation}")

                history += f"步骤 {i}: {step}\n使用工具 {tool_name} -> {observation}\n\n"
                tool_iterations += 1

                messages.append({"role": "user", "content": f"工具 '{tool_name}' 的输出: {observation}"})
                response_text = self.llm_client.think(messages=messages) or ""
                messages.append({"role": "assistant", "content": response_text})

            history += f"步骤 {i}: {step}\n结果: {response_text}\n\n"
            final_answer = response_text
            print(f"✅ 步骤 {i} 已完成，结果: {final_answer}")

        return final_answer

# --- 4. 智能体 (Agent) 整合 ---
class PlanAndSolveAgent:
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: Optional[ToolExecutor] = None):
        self.llm_client = llm_client
        self.tool_executor = tool_executor or ToolExecutor()
        if not self.tool_executor.getTool("Search"):
            self.tool_executor.registerTool(
                "Search",
                "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。",
                search,
            )
        self.planner = Planner(self.llm_client)
        self.executor = Executor(self.llm_client, self.tool_executor)

    def run(self, question: str):
        print(f"\n--- 开始处理问题 ---\n问题: {question}")
        plan = self.planner.plan(question)
        if not plan:
            print("\n--- 任务终止 --- \n无法生成有效的行动计划。")
            return
        final_answer = self.executor.execute(question, plan)
        print(f"\n--- 任务完成 ---\n最终答案: {final_answer}")

# --- 5. 主函数入口 ---
if __name__ == '__main__':
    try:
        llm_client = HelloAgentsLLM()
        agent = PlanAndSolveAgent(llm_client)
        # question = "一个水果店周一卖出了15个苹果。周二卖出的苹果数量是周一的两倍。周三卖出的数量比周二少了5个。请问这三天总共卖出了多少个苹果？"
        question = "华为最新的手机是哪一款？它的主要卖点是什么？价格是多少？"
        agent.run(question)
    except ValueError as e:
        print(e)
