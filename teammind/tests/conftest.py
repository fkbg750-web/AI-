"""
Pytest Configuration
"""
import pytest


@pytest.fixture(scope="session")
def sample_content():
    """样例内容"""
    return """
    会议主题：技术方案评审
    参会人：张三、李四、王五

    讨论内容：
    1. 用户认证方案
       - 李四提议使用 Redis Session
       - 经过讨论，认为运维复杂度高
       - 张三建议采用 JWT 方案
       - 最终决定：采用 JWT

    2. 任务分配
       - 张三负责更新技术文档，1月20日前完成
       - 李四负责实现 JWT 认证模块
       - 王五负责前端对接

    决策：
    - 认证方案：JWT
    - 负责人：张三、李四、王五
    - 截止日期：1月20日
    """


@pytest.fixture(scope="session")
def sample_entities():
    """样例实体"""
    from src.agents.extractor import Entity

    return [
        Entity(name="张三", type="Person", properties={"role": "tech-lead"}),
        Entity(name="李四", type="Person", properties={"role": "backend"}),
        Entity(name="王五", type="Person", properties={"role": "frontend"}),
        Entity(name="JWT", type="Decision", properties={"status": "approved"}),
        Entity(name="Redis Session", type="Decision", properties={"status": "rejected"}),
        Entity(name="技术文档", type="Document", properties={"deadline": "1月20日"}),
    ]
