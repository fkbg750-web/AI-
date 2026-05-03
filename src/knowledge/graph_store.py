"""
Graph Store - 图数据库接口
基于 Neo4j 实现实体关系存储和查询
"""
from typing import Optional
from datetime import datetime

from neo4j import GraphDatabase


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
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )

    def close(self):
        """关闭连接"""
        self.driver.close()

    async def upsert_node(
        self,
        node_type: str,
        node_id: str,
        properties: dict
    ) -> Optional[str]:
        """
        创建或更新节点

        Args:
            node_type: 节点类型（Person, Project, Decision, Task, Document, Meeting）
            node_id: 节点 ID
            properties: 节点属性

        Returns:
            Optional[str]: 节点 ID
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MERGE (n:$node_type {id: $node_id})
                SET n += $properties
                SET n.updated_at = timestamp()
                RETURN n.id AS id
                """,
                node_type=node_type,
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
        properties: Optional[dict] = None
    ) -> Optional[str]:
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

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (a), (b)
                WHERE a.name = $from_name AND b.name = $to_name
                MERGE (a)-[r:$edge_type]->(b)
                SET r += $properties
                SET r.updated_at = timestamp()
                RETURN id(r) AS edge_id
                """,
                from_name=from_node,
                to_name=to_node,
                edge_type=edge_type.upper(),
                properties=properties
            )
            record = result.single()
            return str(record["edge_id"]) if record else None

    async def find_node(
        self,
        node_type: Optional[str] = None,
        name: Optional[str] = None,
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
            params = {}

            if node_type:
                query += f" WHERE n:{node_type}"

            if name:
                if node_type:
                    query += " AND"
                else:
                    query += " WHERE"
                query += " n.name CONTAINS $name"
                params["name"] = name

            query += " RETURN n LIMIT $limit"
            params["limit"] = limit

            result = session.run(query, **params)

            return [
                {
                    "type": record["n"].type,
                    "id": record["n"].get("id", ""),
                    "properties": dict(record["n"])
                }
                for record in result
            ]

    async def find_relations(
        self,
        from_name: Optional[str] = None,
        to_name: Optional[str] = None,
        relation_type: Optional[str] = None,
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
            params = {"limit": limit}
            where_clauses = []

            if from_name:
                where_clauses.append("a.name CONTAINS $from_name")
                params["from_name"] = from_name

            if to_name:
                where_clauses.append("b.name CONTAINS $to_name")
                params["to_name"] = to_name

            if relation_type:
                where_clauses.append(f"type(r) = '${relation_type.upper()}'")

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
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH path = (a)-[*1..$max_depth]-(b)
                WHERE a.name CONTAINS $from_name AND b.name CONTAINS $to_name
                RETURN path, length(path) AS depth
                ORDER BY depth
                LIMIT 10
                """,
                from_name=from_name,
                to_name=to_name,
                max_depth=max_depth
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
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH path = (n)-[*1..$depth]-(connected)
                WHERE n.name CONTAINS $entity_name
                RETURN path,
                       [node IN nodes(path) | {type: labels(node)[0], name: node.name}] AS node_list,
                       [rel IN relationships(path) | {type: type(rel), from: startNode(rel).name, to: endNode(rel).name}] AS rel_list
                LIMIT 20
                """,
                entity_name=entity_name,
                depth=depth
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
