"""
Graph Store - 图数据库接口
基于 Neo4j 实现实体关系存储和查询
"""
import re

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover - allows importing this module in unit tests
    GraphDatabase = None


class GraphStore:
    """
    图数据库存储和查询

    功能：
    1. 创建/更新节点
    2. 创建/更新关系
    3. 路径查询
    4. 子图查询
    """

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """
        初始化图存储

        Args:
            neo4j_uri: Neo4j 连接 URI
            neo4j_user: 用户名
            neo4j_password: 密码
        """
        if GraphDatabase is None:
            raise ImportError("neo4j package is required to use GraphStore")

        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )

    @staticmethod
    def _safe_label(value: str, fallback: str = "Entity") -> str:
        """Return a Cypher-safe label or relationship identifier."""
        candidate = re.sub(r"[^0-9A-Za-z_]", "_", value or "")
        if not candidate or candidate[0].isdigit():
            candidate = fallback
        return candidate

    def close(self):
        """关闭连接"""
        self.driver.close()

    async def upsert_node(
        self,
        node_type: str,
        node_id: str,
        properties: dict
    ) -> str | None:
        """
        创建或更新节点

        Args:
            node_type: 节点类型（Person, Project, Decision, Task, Document, Meeting）
            node_id: 节点 ID
            properties: 节点属性

        Returns:
            Optional[str]: 节点 ID
        """
        label = self._safe_label(node_type)
        properties = dict(properties or {})
        properties.setdefault("name", node_id)

        with self.driver.session() as session:
            result = session.run(
                f"""
                MERGE (n:{label} {{id: $node_id}})
                SET n += $properties
                SET n.updated_at = timestamp()
                RETURN n.id AS id
                """,
                node_id=node_id,
                properties=properties
            )
            record = result.single()
            return record["id"] if record else None

    async def upsert_edge(
        self,
        from_node: str,
        to_node: str,
        edge_type: str,
        properties: dict | None = None
    ) -> str | None:
        """
        创建或更新关系

        Args:
            from_node: 起始节点名称
            to_node: 目标节点名称
            edge_type: 关系类型
            properties: 关系属性

        Returns:
            Optional[str]: 边 ID
        """
        properties = properties or {}
        rel_type = self._safe_label(edge_type, "RELATED_TO").upper()

        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH (a), (b)
                WHERE (a.id = $from_node OR a.name = $from_node)
                  AND (b.id = $to_node OR b.name = $to_node)
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $properties
                SET r.updated_at = timestamp()
                RETURN id(r) AS edge_id
                """,
                from_node=from_node,
                to_node=to_node,
                properties=properties
            )
            record = result.single()
            return str(record["edge_id"]) if record else None

    async def find_node(
        self,
        node_type: str | None = None,
        name: str | None = None,
        limit: int = 10
    ) -> list[dict]:
        """
        查询节点

        Args:
            node_type: 节点类型过滤
            name: 名称过滤（模糊匹配）
            limit: 返回数量

        Returns:
            list[dict]: 节点列表
        """
        with self.driver.session() as session:
            # 构建查询
            query = "MATCH (n)"
            params: dict[str, object] = {}

            if node_type:
                label = self._safe_label(node_type)
                query = f"MATCH (n:{label})"

            if name:
                if node_type:
                    query += " AND"
                else:
                    query += " WHERE"
                query += " n.name CONTAINS $name"
                params["name"] = name

            query += " RETURN n, labels(n)[0] AS node_type LIMIT $limit"
            params["limit"] = limit

            result = session.run(query, **params)

            return [
                {
                    "type": record["node_type"],
                    "id": record["n"].get("id", ""),
                    "properties": dict(record["n"])
                }
                for record in result
            ]

    async def find_relations(
        self,
        from_name: str | None = None,
        to_name: str | None = None,
        relation_type: str | None = None,
        limit: int = 50
    ) -> list[dict]:
        """
        查询关系

        Args:
            from_name: 起始节点名称
            to_name: 目标节点名称
            relation_type: 关系类型
            limit: 返回数量

        Returns:
            list[dict]: 关系列表
        """
        with self.driver.session() as session:
            # 构建查询
            query = "MATCH (a)-[r]->(b)"
            params: dict[str, object] = {"limit": limit}
            where_clauses = []

            if from_name:
                where_clauses.append("a.name CONTAINS $from_name")
                params["from_name"] = from_name

            if to_name:
                where_clauses.append("b.name CONTAINS $to_name")
                params["to_name"] = to_name

            if relation_type:
                where_clauses.append("type(r) = $relation_type")
                params["relation_type"] = self._safe_label(
                    relation_type,
                    "RELATED_TO"
                ).upper()

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += " RETURN a.name AS from_node, type(r) AS relation, b.name AS to_node, r"

            result = session.run(query, **params)

            return [
                {
                    "from": record["from_node"],
                    "relation": record["relation"],
                    "to": record["to_node"],
                    "properties": dict(record["r"])
                }
                for record in result
            ]

    async def find_path(
        self,
        from_name: str,
        to_name: str,
        max_depth: int = 3
    ) -> list[dict]:
        """
        查找两个实体间的路径

        Args:
            from_name: 起始节点
            to_name: 目标节点
            max_depth: 最大路径深度

        Returns:
            list[dict]: 路径列表
        """
        depth = max(1, min(int(max_depth), 5))

        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH path = (a)-[*1..{depth}]-(b)
                WHERE a.name CONTAINS $from_name AND b.name CONTAINS $to_name
                RETURN path, length(path) AS depth
                ORDER BY depth
                LIMIT 10
                """,
                from_name=from_name,
                to_name=to_name
            )

            paths = []
            for record in result:
                path = record["path"]
                nodes = [dict(node) for node in path.nodes]
                relationships = [dict(rel) for rel in path.relationships]
                paths.append({
                    "nodes": nodes,
                    "relationships": relationships,
                    "depth": record["depth"]
                })

            return paths

    async def get_entity_context(
        self,
        entity_name: str,
        depth: int = 2
    ) -> dict:
        """
        获取实体的上下文（关联的实体和关系）

        Args:
            entity_name: 实体名称
            depth: 查询深度

        Returns:
            dict: 上下文信息
        """
        depth = max(1, min(int(depth), 5))

        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH path = (n)-[*1..{depth}]-(connected)
                WHERE n.name CONTAINS $entity_name
                RETURN path,
                       [node IN nodes(path) | {type: labels(node)[0], name: node.name}] AS node_list,
                       [rel IN relationships(path) | {type: type(rel), from: startNode(rel).name, to: endNode(rel).name}] AS rel_list
                LIMIT 20
                """,
                entity_name=entity_name
            )

            nodes = set()
            relations = []

            for record in result:
                for node in record["node_list"]:
                    nodes.add((node["type"], node["name"]))
                relations.extend(record["rel_list"])

            return {
                "center": entity_name,
                "nodes": [{"type": t, "name": n} for t, n in nodes],
                "relations": relations
            }

    async def get_statistics(self) -> dict:
        """获取图谱统计信息"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n)
                WITH labels(n)[0] AS type, count(*) AS count
                RETURN type, count
                UNION ALL
                MATCH ()-[r]->()
                WITH type(r) AS type, count(*) AS count
                RETURN type, count
                """
            )

            stats = {}
            for record in result:
                key = record["type"]
                stats[key] = record["count"]

            return stats
