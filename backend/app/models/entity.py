"""
Neo4j数据模型定义
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field


class PersonBase(BaseModel):
    """Person节点基础模型"""
    name: str = Field(..., description="姓名")
    birth_year: Optional[int] = Field(None, description="生年")
    death_year: Optional[int] = Field(None, description="卒年")
    occupation: Optional[List[str]] = Field(None, description="职业")
    specialty: Optional[List[str]] = Field(None, description="专业领域")
    hobby: Optional[List[str]] = Field(None, description="爱好")
    achievement: Optional[str] = Field(None, description="成就")
    female_experience: Optional[List[str]] = Field(None, description="女性经验")
    type: Optional[str] = Field(None, description="人物类型")
    frequency: Optional[int] = Field(None, description="频率")
    degree: Optional[int] = Field(None, description="度数")
    description: Optional[str] = Field(None, description="描述")
    human_readable_id: Optional[str] = Field(None, description="人类可读ID")
    knowledge_source: Optional[str] = Field(None, description="知识来源")



class PersonCreate(PersonBase):
    """创建Person节点的输入模型"""
    source_type: str = Field("user_created", description="来源类型: system或user_created")
    created_by: Optional[str] = Field(None, description="创建者用户ID（如果是用户创建）")
    is_verified: bool = Field(False, description="是否已验证")


class PersonUpdate(BaseModel):
    """更新Person节点的输入模型"""
    name: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    occupation: Optional[List[str]] = None
    specialty: Optional[List[str]] = None
    hobby: Optional[List[str]] = None
    achievement: Optional[str] = None
    female_experience: Optional[List[str]] = None
    type: Optional[str] = None
    frequency: Optional[int] = None
    degree: Optional[int] = None
    description: Optional[str] = None
    human_readable_id: Optional[str] = None
    knowledge_source: Optional[str] = None
    is_verified: Optional[bool] = None


class PersonInDB(PersonBase):
    """数据库中的Person节点模型"""
    id: str = Field(..., description="节点ID")
    source_type: str = Field(..., description="来源类型")
    created_by: Optional[str] = Field(None, description="创建者用户ID")
    is_verified: bool = Field(False, description="是否已验证")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        from_attributes = True


class PersonResponse(PersonInDB):
    """API响应的Person节点模型"""
    pass


class RelationshipBase(BaseModel):
    """关系基础模型"""
    type: str = Field(..., description="关系类型")
    description: Optional[str] = Field(None, description="关系描述")
    strength: int = Field(1, ge=1, le=10, description="关系强度(1-10)")


class RelationshipCreate(RelationshipBase):
    """创建关系的输入模型"""
    source_type: str = Field("user_created", description="来源类型: system或user_created")
    created_by: Optional[str] = Field(None, description="创建者用户ID（如果是用户创建）")


class RelationshipInDB(RelationshipBase):
    """数据库中的关系模型"""
    id: str = Field(..., description="关系ID")
    source_type: str = Field(..., description="来源类型")
    created_by: Optional[str] = Field(None, description="创建者用户ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    class Config:
        from_attributes = True


class GraphNode(BaseModel):
    """图节点表示"""
    id: str
    label: str
    type: str = "person"
    properties: Dict[str, Any]
    
    @classmethod
    def from_person(cls, person: PersonInDB):
        """从Person创建图节点"""
        return cls(
            id=person.id,
            label=person.name,
            type="person",
            properties={
                "name": person.name,
                "birth_year": person.birth_year,
                "death_year": person.death_year,
                "occupation": person.occupation,
                "specialty": person.specialty,
                "hobby": person.hobby,
                "achievement": person.achievement,
                "female_experience": person.female_experience,
                "type": person.type,
                "frequency": person.frequency,
                "degree": person.degree,
                "description": person.description,
                "human_readable_id": person.human_readable_id,
                "knowledge_source": person.knowledge_source,
                "source_type": person.source_type,
                "created_by": person.created_by,
                "is_verified": person.is_verified,
                "created_at": person.created_at.isoformat() if person.created_at else None,
                "updated_at": person.updated_at.isoformat() if person.updated_at else None,
            }
        )


class GraphEdge(BaseModel):
    """图边表示"""
    id: str
    source: str
    target: str
    label: str
    type: str = "relates_to"
    properties: Dict[str, Any]
    
    @classmethod
    def from_relationship(cls, relationship: RelationshipInDB, source_id: str, target_id: str):
        """从Relationship创建图边"""
        return cls(
            id=relationship.id,
            source=source_id,
            target=target_id,
            label=relationship.type,
            type="relates_to",
            properties={
                "type": relationship.type,
                "description": relationship.description,
                "strength": relationship.strength,
                "source_type": relationship.source_type,
                "created_by": relationship.created_by,
                "created_at": relationship.created_at.isoformat() if relationship.created_at else None,
            }
        )


class GraphData(BaseModel):
    """图数据响应"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    
    def to_visjs_format(self):
        """转换为vis.js格式"""
        vis_nodes = []
        for node in self.nodes:
            # 根据source_type设置颜色
            color = "#4CAF50" if node.properties.get("source_type") == "system" else "#2196F3"
            vis_nodes.append({
                "id": node.id,
                "label": node.label,
                "title": f"{node.properties.get('profession', '')} - {node.properties.get('achievements', '')}",
                "color": color,
                "properties": node.properties
            })
        
        vis_edges = []
        for edge in self.edges:
            vis_edges.append({
                "id": edge.id,
                "from": edge.source,
                "to": edge.target,
                "label": edge.label,
                "title": edge.properties.get("description", ""),
                "value": edge.properties.get("strength", 1),
                "properties": edge.properties
            })
        
        return {
            "nodes": vis_nodes,
            "edges": vis_edges
        }


class OptimizedPersonNode(BaseModel):
    """优化后的Person节点表示 - 直接用于前端"""
    id: str
    name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    industry: Optional[str] = None  # 从specialty提取
    occupation: Optional[str] = None  # 从occupation提取
    achievement: Optional[str] = None
    description: Optional[str] = None
    source_type: str = "system"
    type: Optional[str] = None
    years: Optional[str] = None  # 格式化后的生卒年
    created_by: Optional[str] = None
    is_verified: bool = False
    created_at: Optional[str] = None
    
    @classmethod
    def from_neo4j_node(cls, person_data: Dict[str, Any]) -> "OptimizedPersonNode":
        """从Neo4j节点数据创建优化节点"""
        # 提取specialty作为industry
        specialty = person_data.get("specialty")
        industry = None
        if specialty:
            if isinstance(specialty, list) and len(specialty) > 0:
                industry = specialty[0]
            elif isinstance(specialty, str):
                industry = specialty
        
        # 提取occupation
        occupation_data = person_data.get("occupation")
        occupation = None
        if occupation_data:
            if isinstance(occupation_data, list) and len(occupation_data) > 0:
                occupation = occupation_data[0]
            elif isinstance(occupation_data, str):
                occupation = occupation_data
        
        # 格式化years
        birth_year = person_data.get("birth_year")
        death_year = person_data.get("death_year")
        years = None
        if birth_year and death_year:
            years = f"{birth_year}-{death_year}"
        elif birth_year:
            years = f"{birth_year}-至今"
        
        return cls(
            id=person_data.get("id", str(uuid4())),
            name=person_data.get("name", "未知"),
            birth_year=birth_year,
            death_year=death_year,
            industry=industry,
            occupation=occupation,
            achievement=person_data.get("achievement"),
            description=person_data.get("description"),
            source_type=person_data.get("source_type", "system"),
            type=person_data.get("type"),
            years=years,
            created_by=person_data.get("created_by"),
            is_verified=person_data.get("is_verified", False),
            created_at=person_data.get("created_at")
        )


class OptimizedGraphEdge(BaseModel):
    """优化后的图边表示"""
    id: str
    source: str
    target: str
    label: str = "RELATED_TO"
    strength: int = 1
    description: Optional[str] = None
    
    @classmethod
    def from_neo4j_relationship(cls, rel_data: Dict[str, Any], source_id: str, target_id: str) -> "OptimizedGraphEdge":
        """从Neo4j关系数据创建优化边"""
        # 处理Neo4j关系对象
        if hasattr(rel_data, '_properties'):
            # Neo4j的Relationship对象
            rel_dict = dict(rel_data._properties)
            rel_dict['id'] = rel_data.element_id if hasattr(rel_data, 'element_id') else rel_data.id
            rel_dict['type'] = rel_data.type if hasattr(rel_data, 'type') else 'RELATED_TO'
        else:
            # 已经是字典
            rel_dict = rel_data
        
        return cls(
            id=rel_dict.get("id", str(uuid4())),
            source=source_id,
            target=target_id,
            label=rel_dict.get("type", "RELATED_TO"),
            strength=rel_dict.get("strength", 1),
            description=rel_dict.get("description")
        )


class OptimizedGraphData(BaseModel):
    """优化后的图数据响应"""
    nodes: List[OptimizedPersonNode]
    edges: List[OptimizedGraphEdge]
