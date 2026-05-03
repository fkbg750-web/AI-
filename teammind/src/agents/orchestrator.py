"""
Orchestrator Agent - 任务编排器
负责任务理解、分解、调度和结果聚合
"""
import json
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from anthropic import Anthropic


class IntentType(Enum):
    """用户意图类型"""
    QA = "qa"                    # 问答
    ADD_KNOWLEDGE = "add_knowledge"  # 添加知识
    QUERY_RELATIONS = "query_relations"  # 查询关系
    SUMMARY = "summary"          # 摘要总结
    OTHER = "other"


@dataclass
class Task:
    """子任务"""
    name: str
    agent: str
    input_data: dict
    depends_on: list[str] = field(default_factory=list)


@dataclass
class OrchestratorResult:
    """编排结果"""
    intent: IntentType
    sub_tasks: list[Task]
    final_response: Optional[str] = None
    context_used: list[dict] = field(default_factory=list)


class OrchestratorAgent:
    """
    编排器 Agent

    职责：
    1. 理解用户输入，判断意图
    2. 分解为可执行的子任务
    3. 确定 Agent 调度顺序
    4. 聚合结果生成响应
    """

    SYSTEM_PROMPT = """你是一个团队知识助手的编排器（Orchestrator）。

你的职责：
1. 理解用户意图
2. 将复杂任务分解为可并行/顺序执行的子任务
3. 调度专业的 Agent 完成任务
4. 聚合结果生成最终响应

可用的 Agent：
- extract: 从文本中提取实体和关键信息
- comprehend: 理解语义，识别决策点和行动项
- relate: 识别实体间关系，构建知识图谱
- store: 存储到知识库

用户输入只会包含自然语言，你需要将其转化为结构化的任务计划。

请用 JSON 格式输出：
{
    "intent": "qa|add_knowledge|query_relations|summary|other",
    "sub_tasks": [
        {
            "name": "任务名称",
            "agent": "agent_name",
            "input_data": {"key": "value"},
            "depends_on": ["前置任务名称"]
        }
    ]
}
"""

    def __init__(self, anthropic_client: Anthropic):
        self.client = anthropic_client

    async def process(self, user_input: str, context: Optional[dict] = None) -> OrchestratorResult:
        """
        处理用户输入

        Args:
            user_input: 用户输入
            context: 当前上下文（对话历史等）

        Returns:
            OrchestratorResult: 编排结果
        """
        # 构建 Prompt
        context_str = json.dumps(context or {}, ensure_ascii=False, indent=2)
        prompt = f"""用户输入：{user_input}

当前上下文：
{context_str}

请分析用户意图并制定任务计划。"""

        # 调用 LLM
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        # 解析响应
        result_text = response.content[0].text
        try:
            result_json = json.loads(result_text)
        except json.JSONDecodeError:
            # 降级处理：简单分类
            return self._fallback_process(user_input)

        # 构建返回结果
        intent = IntentType(result_json.get("intent", "other"))
        sub_tasks = [
            Task(
                name=t["name"],
                agent=t["agent"],
                input_data=t.get("input_data", {}),
                depends_on=t.get("depends_on", [])
            )
            for t in result_json.get("sub_tasks", [])
        ]

        return OrchestratorResult(
            intent=intent,
            sub_tasks=sub_tasks
        )

    def _fallback_process(self, user_input: str) -> OrchestratorResult:
        """降级处理：简单规则匹配"""
        # 简单关键词判断
        if any(kw in user_input for kw in ["是什么", "怎么", "为什么", "谁", "?"]):
            intent = IntentType.QA
            tasks = [
                Task(
                    name="检索知识",
                    agent="retrieve",
                    input_data={"query": user_input}
                )
            ]
        elif any(kw in user_input for kw in ["添加", "记录", "告诉", "分享"]):
            intent = IntentType.ADD_KNOWLEDGE
            tasks = [
                Task(name="提取信息", agent="extract", input_data={"content": user_input}),
                Task(name="理解语义", agent="comprehend", input_data={}, depends_on=["提取信息"]),
                Task(name="关联关系", agent="relate", input_data={}, depends_on=["理解语义"]),
                Task(name="存储知识", agent="store", input_data={}, depends_on=["关联关系"]),
            ]
        else:
            intent = IntentType.OTHER
            tasks = []

        return OrchestratorResult(intent=intent, sub_tasks=tasks)

    async def dispatch_task(self, task: Task, previous_results: dict) -> dict:
        """
        调度单个任务

        Args:
            task: 任务定义
            previous_results: 前置任务的结果

        Returns:
            dict: 任务执行结果
        """
        # 根据 agent 类型分发
        agent_map = {
            "extract": self._run_extractor,
            "comprehend": self._run_comprehender,
            "relate": self._run_relater,
            "store": self._run_store,
            "retrieve": self._run_retriever,
        }

        agent_func = agent_map.get(task.agent)
        if not agent_func:
            return {"error": f"Unknown agent: {task.agent}"}

        # 注入前置任务结果
        task.input_data["previous_results"] = previous_results

        return await agent_func(task.input_data)

    async def _run_extractor(self, input_data: dict) -> dict:
        """运行提取 Agent"""
        from src.agents.extractor import ExtractAgent
        # 实际调用时需要注入 client
        return {"status": "extracted", "entities": []}

    async def _run_comprehender(self, input_data: dict) -> dict:
        """运行理解 Agent"""
        return {"status": "understood", "summary": ""}

    async def _run_relater(self, input_data: dict) -> dict:
        """运行关联 Agent"""
        return {"status": "related", "relations": []}

    async def _run_store(self, input_data: dict) -> dict:
        """运行存储 Agent"""
        return {"status": "stored"}

    async def _run_retriever(self, input_data: dict) -> dict:
        """运行检索"""
        return {"status": "retrieved", "results": []}
