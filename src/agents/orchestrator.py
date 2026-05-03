"""
Orchestrator Agent - 任务编排器
负责任务理解、分解、调度和结果聚合
"""
import json
from dataclasses import dataclass, field
from enum import Enum

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - used when running mocked tests without deps
    Anthropic = object

from src.agents.utils import maybe_await, parse_json_object, to_plain_dict


class IntentType(Enum):
    """用户意图类型"""
    QUERY = "query"              # 查询
    STORE = "store"              # 存储知识
    QA = "query"                 # 兼容旧命名
    ADD_KNOWLEDGE = "store"      # 兼容旧命名
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
    success: bool = True
    final_response: str | None = None
    context_used: list[dict] = field(default_factory=list)
    answer: str | None = None
    sources: list[dict] = field(default_factory=list)
    extracted_entities: list[dict] = field(default_factory=list)
    comprehended_summary: str = ""
    related_relations: list[dict] = field(default_factory=list)
    storage_result: dict | None = None
    error: str | None = None


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
    "intent": "query|store|query_relations|summary|other",
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

    def __init__(
        self,
        anthropic_client: Anthropic,
        extract_agent=None,
        comprehend_agent=None,
        relate_agent=None,
        store_agent=None,
        vector_store=None,
        graph_store=None,
    ):
        self.client = anthropic_client
        self.extract_agent = extract_agent
        self.comprehend_agent = comprehend_agent
        self.relate_agent = relate_agent
        self.store_agent = store_agent
        self.vector_store = vector_store
        self.graph_store = graph_store

    async def process(self, user_input: str, context: dict | None = None) -> OrchestratorResult:
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

        try:
            response = await maybe_await(self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            ))
            result_json = parse_json_object(response.content[0].text)
        except Exception:
            return self._fallback_process(user_input)

        intent = self._parse_intent(result_json.get("intent", "other"))
        sub_tasks = self._parse_tasks(result_json.get("sub_tasks", []))
        if not sub_tasks:
            sub_tasks = self._default_tasks_for_intent(intent, user_input)

        if intent == IntentType.STORE:
            return await self._process_store(user_input, sub_tasks, context or {})

        if intent == IntentType.QUERY:
            return await self.query(user_input, context=context)

        return OrchestratorResult(
            intent=intent,
            sub_tasks=sub_tasks,
            success=True,
        )

    async def query(self, question: str, context: dict | None = None) -> OrchestratorResult:
        """Run a minimal query flow over configured stores."""
        context = context or {}
        sources = list(context.get("sources", []))

        if self.vector_store:
            try:
                sources.extend(await self.vector_store.search(question, limit=5))
            except Exception as exc:
                sources.append({"info_type": "error", "content": f"向量检索失败: {exc}"})

        answer = context.get("answer")
        if not answer and sources:
            first = sources[0]
            summary = first.get("summary") or first.get("content", "")
            answer = summary or "已找到相关知识，但缺少摘要内容。"
        if not answer:
            answer = "查询流程已识别，等待接入混合检索结果。"

        return OrchestratorResult(
            intent=IntentType.QUERY,
            sub_tasks=[
                Task(name="检索知识", agent="retrieve", input_data={"query": question}),
                Task(name="生成回答", agent="generate", input_data={"query": question}),
            ],
            success=True,
            answer=answer,
            final_response=answer,
            sources=sources,
            context_used=sources,
        )

    async def _process_store(
        self,
        content: str,
        sub_tasks: list[Task],
        context: dict,
    ) -> OrchestratorResult:
        """Execute the store pipeline when agents are available."""
        from src.agents.comprehender import ComprehendAgent
        from src.agents.extractor import ExtractAgent
        from src.agents.relater import RelateAgent

        extract_agent = self.extract_agent or ExtractAgent(self.client)
        comprehend_agent = self.comprehend_agent or ComprehendAgent(self.client)
        relate_agent = self.relate_agent or RelateAgent(self.client)

        metadata = context.get("metadata", {})
        source_type = context.get("source_type", "manual")
        source_id = context.get("source_id", "")

        extract_result = await extract_agent.extract(
            content=content,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata,
        )
        extract_dict = extract_agent.to_dict(extract_result)

        comprehend_result = await comprehend_agent.comprehend(
            content=content,
            extract_result=extract_dict,
        )
        comprehend_dict = comprehend_agent.to_dict(comprehend_result)

        relate_result = await relate_agent.relate(
            entities=extract_result.entities,
            comprehend_result=comprehend_dict,
            existing_context=context.get("existing_context"),
        )
        relate_dict = relate_agent.to_dict(relate_result)

        storage_dict = None
        storage_error = None
        if self.store_agent:
            storage_result = await maybe_await(self.store_agent.process(
                content=content,
                extract_result=extract_dict,
                comprehend_result=comprehend_dict,
                relate_result=relate_dict,
                metadata=metadata,
            ))
            storage_dict = to_plain_dict(storage_result)
            storage_error = storage_dict.get("error")

        stored = bool(storage_dict and (
            storage_dict.get("vector_stored") or storage_dict.get("graph_stored")
        ))
        final_response = "知识已解析"
        if stored:
            final_response += "并写入知识库。"
        elif storage_error:
            final_response += f"，但存储失败：{storage_error}"
        else:
            final_response += "，但当前未配置存储后端。"

        return OrchestratorResult(
            intent=IntentType.STORE,
            sub_tasks=sub_tasks,
            success=storage_error is None,
            final_response=final_response,
            extracted_entities=extract_dict.get("entities", []),
            comprehended_summary=comprehend_dict.get("summary", ""),
            related_relations=relate_dict.get("relations", []),
            storage_result=storage_dict,
            error=storage_error,
        )

    def _parse_intent(self, value: str) -> IntentType:
        """Normalize old and new intent names."""
        normalized = (value or "other").lower()
        aliases = {
            "qa": "query",
            "add_knowledge": "store",
            "knowledge": "store",
        }
        normalized = aliases.get(normalized, normalized)
        try:
            return IntentType(normalized)
        except ValueError:
            return IntentType.OTHER

    def _parse_tasks(self, tasks: list[dict]) -> list[Task]:
        """Convert raw task dictionaries into Task objects."""
        parsed = []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            parsed.append(Task(
                name=task.get("name", task.get("agent", "task")),
                agent=task.get("agent", "unknown"),
                input_data=task.get("input_data", {}),
                depends_on=task.get("depends_on", []),
            ))
        return parsed

    def _default_tasks_for_intent(self, intent: IntentType, user_input: str) -> list[Task]:
        """Create a deterministic fallback plan for each supported intent."""
        if intent == IntentType.STORE:
            return [
                Task(name="提取信息", agent="extract", input_data={"content": user_input}),
                Task(name="理解语义", agent="comprehend", input_data={}, depends_on=["提取信息"]),
                Task(name="关联关系", agent="relate", input_data={}, depends_on=["理解语义"]),
                Task(name="存储知识", agent="store", input_data={}, depends_on=["关联关系"]),
            ]
        if intent == IntentType.QUERY:
            return [
                Task(name="检索知识", agent="retrieve", input_data={"query": user_input}),
                Task(name="生成回答", agent="generate", input_data={"query": user_input}),
            ]
        return []

    def _fallback_process(self, user_input: str) -> OrchestratorResult:
        """降级处理：简单规则匹配"""
        # 简单关键词判断
        if any(kw in user_input for kw in ["是什么", "怎么", "为什么", "谁", "?", "？"]):
            intent = IntentType.QUERY
        elif any(kw in user_input for kw in ["添加", "记录", "告诉", "分享", "决定", "负责", "会议"]):
            intent = IntentType.STORE
        else:
            intent = IntentType.OTHER
        tasks = self._default_tasks_for_intent(intent, user_input)

        return OrchestratorResult(intent=intent, sub_tasks=tasks, success=True)

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
