from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import logging
import uuid
from datetime import datetime

from app.core.database import get_db
from app.core.neo4j_database import neo4j_db
from app.models.entity import GraphData, GraphNode, GraphEdge, PersonResponse, OptimizedPersonNode, OptimizedGraphEdge, OptimizedGraphData
from app.services.user_service import get_user_by_email
from app.services.auth_service import verify_token
from app.api.auth import oauth2_scheme
from app.models.user import User


router = APIRouter(prefix="/graph", tags=["graph"])


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前认证用户
    """
    token_data = verify_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await get_user_by_email(db, email=token_data.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


async def get_current_user_or_none(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前认证用户，如果未认证则返回None
    用于允许匿名访问的端点
    """
    try:
        token_data = verify_token(token)
        if token_data is None:
            return None
        
        user = await get_user_by_email(db, email=token_data.email)
        if user is None or not user.is_active:
            return None
        
        return user
    except Exception:
        return None


@router.get("/nodes", response_model=List[GraphNode])
async def get_graph_nodes(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user)
):
    """
    获取所有人物节点
    """
    try:
        # 从Neo4j获取人物节点
        query = """
        MATCH (p:Person)
        RETURN p
        SKIP $skip
        LIMIT $limit
        """
        
        result = neo4j_db.execute_query(query, {"skip": skip, "limit": limit})
        
        nodes = []
        for record in result:
            person_data = record["p"]
            node = GraphNode(
                id=person_data.get("id"),
                label=person_data.get("name"),
                type="person",
                properties={
                    "name": person_data.get("name"),
                    "birth_year": person_data.get("birth_year"),
                    "death_year": person_data.get("death_year"),
                    "occupation": person_data.get("occupation"),
                    "specialty": person_data.get("specialty"),
                    "hobby": person_data.get("hobby"),
                    "achievement": person_data.get("achievement"),
                    "female_experience": person_data.get("female_experience"),
                    "type": person_data.get("type"),
                    "frequency": person_data.get("frequency"),
                    "degree": person_data.get("degree"),
                    "description": person_data.get("description"),
                    "human_readable_id": person_data.get("human_readable_id"),
                    "knowledge_source": person_data.get("knowledge_source"),
                    "source_type": person_data.get("source_type"),
                    "created_by": person_data.get("created_by"),
                    "is_verified": person_data.get("is_verified", False),
                    "created_at": person_data.get("created_at")
                }
            )
            nodes.append(node)
        
        return nodes
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graph nodes: {str(e)}"
        )


@router.get("/edges", response_model=List[GraphEdge])
async def get_graph_edges(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user)
):
    """
    获取所有关系
    """
    try:
        # 从Neo4j获取关系
        query = """
        MATCH (a:Person)-[r]->(b:Person)
        RETURN a.id as source_id, b.id as target_id, r
        SKIP $skip
        LIMIT $limit
        """
        
        result = neo4j_db.execute_query(query, {"skip": skip, "limit": limit})
        
        edges = []
        for i, record in enumerate(result):
            rel_data = record["r"]
            
            # 确保source和target字段不为None
            source_id = record.get("source_id")
            target_id = record.get("target_id")
            
            if source_id is None:
                source_id = f"source-{i}-{uuid.uuid4().hex[:8]}"
            if target_id is None:
                target_id = f"target-{i}-{uuid.uuid4().hex[:8]}"
            
            edge = GraphEdge(
                id=rel_data.get("id", str(uuid.uuid4())),  # 如果没有ID，则生成一个
                source=source_id,
                target=target_id,
                label=rel_data.get("type", "RELATED_TO"),
                type="relates_to",
                properties={
                    "type": rel_data.get("type", "RELATED_TO"),
                    "description": rel_data.get("description"),
                    "strength": rel_data.get("strength", 1),
                    "source_type": rel_data.get("source_type", "user_created"),
                    "created_by": rel_data.get("created_by"),
                    "created_at": rel_data.get("created_at")
                }
            )
            edges.append(edge)
        
        return edges
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graph edges: {str(e)}"
        )


@router.get("/network", response_model=GraphData)
async def get_graph_network(
    skip_nodes: int = 0,
    limit_nodes: int = 100,
    skip_edges: int = 0,
    limit_edges: int = 100,
    current_user = Depends(get_current_user_or_none)
):
    """
    获取完整的图网络数据（节点和关系）
    未认证用户可以访问，但只能看到公开数据
    """
    try:
        # 根据用户认证状态决定查询条件
        if current_user is None:
            # 未认证用户：只返回公开数据（source_type为'system'或'public'）
            nodes_query = """
            MATCH (p:Person)
            WHERE p.source_type IN ['system', 'public'] OR p.source_type IS NULL
            RETURN p
            SKIP $skip_nodes
            LIMIT $limit_nodes
            """
            
            edges_query = """
            MATCH (a:Person)-[r]->(b:Person)
            WHERE a.source_type IN ['system', 'public'] OR a.source_type IS NULL
              AND b.source_type IN ['system', 'public'] OR b.source_type IS NULL
              AND (r.source_type IN ['system', 'public'] OR r.source_type IS NULL)
            RETURN a.id as source_id, b.id as target_id, r
            SKIP $skip
            LIMIT $limit
            """
        else:
            # 认证用户：返回所有数据
            nodes_query = """
            MATCH (p:Person)
            RETURN p
            SKIP $skip_nodes
            LIMIT $limit_nodes
            """
            
            edges_query = """
            MATCH (a:Person)-[r]->(b:Person)
            RETURN a.id as source_id, b.id as target_id, r
            SKIP $skip
            LIMIT $limit
            """
        
        # 获取节点
        nodes_result = neo4j_db.execute_query(nodes_query, {"skip_nodes": skip_nodes, "limit_nodes": limit_nodes})
        
        nodes = []
        for i, record in enumerate(nodes_result):
            person_data = record["p"]
            # 确保label字段不为None
            name = person_data.get("name")
            label = name if name is not None else "未知"
            
            # 确保id字段不为None - 如果person_data.get("id")是None，则生成一个ID
            node_id = person_data.get("id")
            if node_id is None:
                # 使用name或生成UUID作为ID
                node_id = f"node-{i}-{uuid.uuid4().hex[:8]}"
                if name:
                    node_id = f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}"
            
            node = GraphNode(
                id=node_id,
                label=label,
                type="person",
                properties={
                    "name": name,
                    "birth_year": person_data.get("birth_year"),
                    "death_year": person_data.get("death_year"),
                    "occupation": person_data.get("occupation"),
                    "specialty": person_data.get("specialty"),
                    "hobby": person_data.get("hobby"),
                    "achievement": person_data.get("achievement"),
                    "female_experience": person_data.get("female_experience"),
                    "type": person_data.get("type"),
                    "frequency": person_data.get("frequency"),
                    "degree": person_data.get("degree"),
                    "description": person_data.get("description"),
                    "human_readable_id": person_data.get("human_readable_id"),
                    "knowledge_source": person_data.get("knowledge_source"),
                    "source_type": person_data.get("source_type"),
                    "created_by": person_data.get("created_by"),
                    "is_verified": person_data.get("is_verified", False),
                    "created_at": person_data.get("created_at")
                }
            )
            nodes.append(node)
        
        # 获取关系
        edges_result = neo4j_db.execute_query(edges_query, {"skip": skip_edges, "limit": limit_edges})
        
        edges = []
        for i, record in enumerate(edges_result):
            rel_data = record["r"]
            
            # 确保source和target字段不为None
            source_id = record.get("source_id")
            target_id = record.get("target_id")
            
            if source_id is None:
                source_id = f"source-{i}-{uuid.uuid4().hex[:8]}"
            if target_id is None:
                target_id = f"target-{i}-{uuid.uuid4().hex[:8]}"
            
            edge = GraphEdge(
                id=rel_data.get("id", str(uuid.uuid4())),
                source=source_id,
                target=target_id,
                label=rel_data.get("type", "RELATED_TO"),
                type="relates_to",
                properties={
                    "type": rel_data.get("type", "RELATED_TO"),
                    "description": rel_data.get("description"),
                    "strength": rel_data.get("strength", 1),
                    "source_type": rel_data.get("source_type", "user_created"),
                    "created_by": rel_data.get("created_by"),
                    "created_at": rel_data.get("created_at")
                }
            )
            edges.append(edge)
        
        graph_data = GraphData(nodes=nodes, edges=edges)
        return graph_data
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to retrieve graph network: {str(e)}")
        logger.error(f"Error details: {error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graph network: {str(e)}"
        )


@router.get("/nodes/search", response_model=List[GraphNode])
async def search_graph_nodes(
    q: str,
    current_user = Depends(get_current_user)
):
    """
    搜索图节点
    """
    try:
        # 在Neo4j中搜索节点
        query = """
        MATCH (p:Person)
        WHERE toLower(p.name) CONTAINS toLower($query)
           OR toLower(p.occupation[0]) CONTAINS toLower($query)
           OR toLower(p.specialty[0]) CONTAINS toLower($query)
           OR toLower(p.hobby[0]) CONTAINS toLower($query)
           OR toLower(p.achievement) CONTAINS toLower($query)
           OR toLower(p.description) CONTAINS toLower($query)
           OR toLower(p.type) CONTAINS toLower($query)
        RETURN p
        LIMIT 50
        """
        
        result = neo4j_db.execute_query(query, {"query": q})
        
        nodes = []
        for record in result:
            person_data = record["p"]
            node = GraphNode(
                id=person_data.get("id"),
                label=person_data.get("name"),
                type="person",
                properties={
                    "name": person_data.get("name"),
                    "birth_year": person_data.get("birth_year"),
                    "death_year": person_data.get("death_year"),
                    "occupation": person_data.get("occupation"),
                    "specialty": person_data.get("specialty"),
                    "hobby": person_data.get("hobby"),
                    "achievement": person_data.get("achievement"),
                    "female_experience": person_data.get("female_experience"),
                    "type": person_data.get("type"),
                    "frequency": person_data.get("frequency"),
                    "degree": person_data.get("degree"),
                    "description": person_data.get("description"),
                    "human_readable_id": person_data.get("human_readable_id"),
                    "knowledge_source": person_data.get("knowledge_source"),
                    "source_type": person_data.get("source_type"),
                    "created_by": person_data.get("created_by"),
                    "is_verified": person_data.get("is_verified", False),
                    "created_at": person_data.get("created_at")
                }
            )
            nodes.append(node)
        
        return nodes
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search graph nodes: {str(e)}"
        )


@router.get("/nodes/{node_id}/connections", response_model=List[dict])
async def get_node_connections(
    node_id: str,
    current_user = Depends(get_current_user_or_none)
):
    """
    获取特定节点的连接关系
    """
    try:
        # 根据用户认证状态决定查询条件
        if current_user is None:
            # 未认证用户：只返回公开数据的连接
            query = """
            MATCH (p:Person {id: $node_id})-[r:RELATED_TO]-(other:Person)
            WHERE p.source_type IN ['system', 'public'] OR p.source_type IS NULL
              AND other.source_type IN ['system', 'public'] OR other.source_type IS NULL
            RETURN other.id as target_id, r.strength as strength, r.description as description
            LIMIT 10
            """
        else:
            # 认证用户：返回所有连接
            query = """
            MATCH (p:Person {id: $node_id})-[r:RELATED_TO]-(other:Person)
            RETURN other.id as target_id, r.strength as strength, r.description as description
            LIMIT 10
            """
        
        result = neo4j_db.execute_query(query, {"node_id": node_id})
        
        connections = []
        for record in result:
            connections.append({
                "target_id": record["target_id"],
                "strength": record["strength"],
                "description": record["description"]
            })
        
        return {"connections": connections}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to retrieve node connections: {str(e)}")
        logger.error(f"Error details: {error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve node connections: {str(e)}"
        )


@router.get("/network/optimized", response_model=OptimizedGraphData)
async def get_optimized_graph_network(
    skip_nodes: int = 0,
    limit_nodes: int = 100,
    skip_edges: int = 0,
    limit_edges: int = 100,
    current_user = Depends(get_current_user_or_none)
):
    """
    获取优化后的图网络数据（直接用于前端）
    未认证用户可以访问，但只能看到公开数据
    """
    try:
        # 根据用户认证状态决定查询条件
        if current_user is None:
            # 未认证用户：只返回公开数据（source_type为'system'或'public'）
            nodes_query = """
            MATCH (p:Person)
            WHERE p.source_type IN ['system', 'public'] OR p.source_type IS NULL
            RETURN p
            SKIP $skip_nodes
            LIMIT $limit_nodes
            """
            
            edges_query = """
            MATCH (a:Person)-[r]->(b:Person)
            WHERE a.source_type IN ['system', 'public'] OR a.source_type IS NULL
              AND b.source_type IN ['system', 'public'] OR b.source_type IS NULL
              AND (r.source_type IN ['system', 'public'] OR r.source_type IS NULL)
            RETURN a.id as source_id, b.id as target_id, r
            SKIP $skip
            LIMIT $limit
            """
        else:
            # 认证用户：返回所有数据
            nodes_query = """
            MATCH (p:Person)
            RETURN p
            SKIP $skip_nodes
            LIMIT $limit_nodes
            """
            
            edges_query = """
            MATCH (a:Person)-[r]->(b:Person)
            RETURN a.id as source_id, b.id as target_id, r
            SKIP $skip
            LIMIT $limit
            """
        
        # 获取节点
        nodes_result = neo4j_db.execute_query(nodes_query, {"skip_nodes": skip_nodes, "limit_nodes": limit_nodes})
        
        nodes = []
        for record in nodes_result:
            person_node = record["p"]
            # 将Neo4j节点对象转换为字典
            if hasattr(person_node, '_properties'):
                # Neo4j的Node对象
                person_data = dict(person_node._properties)
                person_data['id'] = person_node.element_id if hasattr(person_node, 'element_id') else person_node.id
            else:
                # 已经是字典
                person_data = person_node
            
            # 使用优化模型创建节点
            optimized_node = OptimizedPersonNode.from_neo4j_node(person_data)
            nodes.append(optimized_node)
        
        # 获取关系
        edges_result = neo4j_db.execute_query(edges_query, {"skip": skip_edges, "limit": limit_edges})
        
        edges = []
        for record in edges_result:
            rel_data = record["r"]
            source_id = record.get("source_id")
            target_id = record.get("target_id")
            
            if source_id and target_id:
                # 使用优化模型创建边
                optimized_edge = OptimizedGraphEdge.from_neo4j_relationship(rel_data, source_id, target_id)
                edges.append(optimized_edge)
        
        graph_data = OptimizedGraphData(nodes=nodes, edges=edges)
        return graph_data
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to retrieve optimized graph network: {str(e)}")
        logger.error(f"Error details: {error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve optimized graph network: {str(e)}"
        )


@router.get("/nodes/search/optimized", response_model=List[OptimizedPersonNode])
async def search_optimized_graph_nodes(
    q: str,
    current_user = Depends(get_current_user)
):
    """
    搜索图节点（优化版本）
    """
    try:
        # 在Neo4j中搜索节点
        query = """
        MATCH (p:Person)
        WHERE toLower(p.name) CONTAINS toLower($query)
           OR toLower(p.occupation[0]) CONTAINS toLower($query)
           OR toLower(p.specialty[0]) CONTAINS toLower($query)
           OR toLower(p.hobby[0]) CONTAINS toLower($query)
           OR toLower(p.achievement) CONTAINS toLower($query)
           OR toLower(p.description) CONTAINS toLower($query)
           OR toLower(p.type) CONTAINS toLower($query)
        RETURN p
        LIMIT 50
        """
        
        result = neo4j_db.execute_query(query, {"query": q})
        
        nodes = []
        for record in result:
            person_node = record["p"]
            # 将Neo4j节点对象转换为字典
            if hasattr(person_node, '_properties'):
                # Neo4j的Node对象
                person_data = dict(person_node._properties)
                person_data['id'] = person_node.element_id if hasattr(person_node, 'element_id') else person_node.id
            else:
                # 已经是字典
                person_data = person_node
            
            # 使用优化模型创建节点
            optimized_node = OptimizedPersonNode.from_neo4j_node(person_data)
            nodes.append(optimized_node)
        
        return nodes
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search optimized graph nodes: {str(e)}"
        )
