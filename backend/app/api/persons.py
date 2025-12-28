from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.neo4j_database import neo4j_db
from app.models.entity import PersonCreate, PersonUpdate, PersonResponse
from app.services.user_service import get_user_by_email
from app.services.auth_service import verify_token
from app.api.auth import oauth2_scheme
from app.models.user import User
import uuid
from datetime import datetime


router = APIRouter(prefix="/persons", tags=["persons"])


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


@router.post("/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
async def create_person(
    person_data: PersonCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建人物节点
    """
    try:
        # 生成唯一ID
        person_id = str(uuid.uuid4())
        
        # 创建Neo4j节点
        query = """
        CREATE (p:Person {
            id: $id,
            name: $name,
            birth_year: $birth_year,
            death_year: $death_year,
            occupation: $occupation,
            specialty: $specialty,
            hobby: $hobby,
            achievement: $achievement,
            female_experience: $female_experience,
            type: $type,
            frequency: $frequency,
            degree: $degree,
            description: $description,
            human_readable_id: $human_readable_id,
            knowledge_source: $knowledge_source,
            source_type: $source_type,
            created_by: $created_by,
            is_verified: $is_verified,
            created_at: $created_at
        })
        RETURN p
        """
        
        # 准备参数
        params = {
            "id": person_id,
            "name": person_data.name,
            "birth_year": person_data.birth_year,
            "death_year": person_data.death_year,
            "occupation": person_data.occupation,
            "specialty": person_data.specialty,
            "hobby": person_data.hobby,
            "achievement": person_data.achievement,
            "female_experience": person_data.female_experience,
            "type": person_data.type,
            "frequency": person_data.frequency,
            "degree": person_data.degree,
            "description": person_data.description,
            "human_readable_id": person_data.human_readable_id,
            "knowledge_source": person_data.knowledge_source,
            "source_type": person_data.source_type,
            "created_by": current_user.email,
            "is_verified": person_data.is_verified,
            "created_at": datetime.now().isoformat()
        }
        
        # 执行查询
        neo4j_db.execute_query(query, params)
        
        # 更新用户记录，标记为已在图中存在
        if current_user.neo4j_person_id is None:
            current_user.neo4j_person_id = person_id
            current_user.is_in_graph = True
            db.add(current_user)
            await db.commit()
            await db.refresh(current_user)
        
        # 返回创建的节点信息
        created_person = PersonResponse(
            id=person_id,
            name=person_data.name,
            birth_year=person_data.birth_year,
            death_year=person_data.death_year,
            occupation=person_data.occupation,
            specialty=person_data.specialty,
            hobby=person_data.hobby,
            achievement=person_data.achievement,
            female_experience=person_data.female_experience,
            type=person_data.type,
            frequency=person_data.frequency,
            degree=person_data.degree,
            description=person_data.description,
            human_readable_id=person_data.human_readable_id,
            knowledge_source=person_data.knowledge_source,
            source_type=person_data.source_type,
            created_by=current_user.email,
            is_verified=person_data.is_verified,
            created_at=datetime.now()
        )
        
        return created_person
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create person node: {str(e)}"
        )


@router.get("/", response_model=List[PersonResponse])
async def get_persons(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user)
):
    """
    获取人物列表
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
        
        persons = []
        for record in result:
            person_data = record["p"]
            person = PersonResponse(
                id=person_data.get("id"),
                name=person_data.get("name"),
                birth_year=person_data.get("birth_year"),
                death_year=person_data.get("death_year"),
                occupation=person_data.get("occupation"),
                specialty=person_data.get("specialty"),
                hobby=person_data.get("hobby"),
                achievement=person_data.get("achievement"),
                female_experience=person_data.get("female_experience"),
                type=person_data.get("type"),
                frequency=person_data.get("frequency"),
                degree=person_data.get("degree"),
                description=person_data.get("description"),
                human_readable_id=person_data.get("human_readable_id"),
                knowledge_source=person_data.get("knowledge_source"),
                source_type=person_data.get("source_type"),
                created_by=person_data.get("created_by"),
                is_verified=person_data.get("is_verified", False),
                created_at=datetime.fromisoformat(person_data.get("created_at")) if person_data.get("created_at") else None
            )
            persons.append(person)
        
        return persons
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve persons: {str(e)}"
        )


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: str,
    current_user = Depends(get_current_user)
):
    """
    获取特定人物
    """
    try:
        # 从Neo4j获取特定人物节点
        query = """
        MATCH (p:Person {id: $id})
        RETURN p
        """
        
        result = neo4j_db.execute_query(query, {"id": person_id})
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person not found"
            )
        
        person_data = result[0]["p"]
        person = PersonResponse(
            id=person_data.get("id"),
            name=person_data.get("name"),
            birth_year=person_data.get("birth_year"),
            death_year=person_data.get("death_year"),
            occupation=person_data.get("occupation"),
            specialty=person_data.get("specialty"),
            hobby=person_data.get("hobby"),
            achievement=person_data.get("achievement"),
            female_experience=person_data.get("female_experience"),
            type=person_data.get("type"),
            frequency=person_data.get("frequency"),
            degree=person_data.get("degree"),
            description=person_data.get("description"),
            human_readable_id=person_data.get("human_readable_id"),
            knowledge_source=person_data.get("knowledge_source"),
            source_type=person_data.get("source_type"),
            created_by=person_data.get("created_by"),
            is_verified=person_data.get("is_verified", False),
            created_at=datetime.fromisoformat(person_data.get("created_at")) if person_data.get("created_at") else None
        )
        
        return person
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve person: {str(e)}"
        )


@router.put("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: str,
    person_data: PersonUpdate,
    current_user = Depends(get_current_user)
):
    """
    更新人物节点
    """
    try:
        # 首先检查人物是否存在
        check_query = """
        MATCH (p:Person {id: $id})
        RETURN p
        """
        
        result = neo4j_db.execute_query(check_query, {"id": person_id})
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person not found"
            )
        
        # 准备更新参数
        update_params = {"id": person_id}
        update_fields = []
        
        # 检查哪些字段需要更新
        if person_data.name is not None:
            update_fields.append("p.name = $name")
            update_params["name"] = person_data.name
        if person_data.birth_year is not None:
            update_fields.append("p.birth_year = $birth_year")
            update_params["birth_year"] = person_data.birth_year
        if person_data.death_year is not None:
            update_fields.append("p.death_year = $death_year")
            update_params["death_year"] = person_data.death_year
        if person_data.occupation is not None:
            update_fields.append("p.occupation = $occupation")
            update_params["occupation"] = person_data.occupation
        if person_data.specialty is not None:
            update_fields.append("p.specialty = $specialty")
            update_params["specialty"] = person_data.specialty
        if person_data.hobby is not None:
            update_fields.append("p.hobby = $hobby")
            update_params["hobby"] = person_data.hobby
        if person_data.achievement is not None:
            update_fields.append("p.achievement = $achievement")
            update_params["achievement"] = person_data.achievement
        if person_data.female_experience is not None:
            update_fields.append("p.female_experience = $female_experience")
            update_params["female_experience"] = person_data.female_experience
        if person_data.type is not None:
            update_fields.append("p.type = $type")
            update_params["type"] = person_data.type
        if person_data.frequency is not None:
            update_fields.append("p.frequency = $frequency")
            update_params["frequency"] = person_data.frequency
        if person_data.degree is not None:
            update_fields.append("p.degree = $degree")
            update_params["degree"] = person_data.degree
        if person_data.description is not None:
            update_fields.append("p.description = $description")
            update_params["description"] = person_data.description
        if person_data.human_readable_id is not None:
            update_fields.append("p.human_readable_id = $human_readable_id")
            update_params["human_readable_id"] = person_data.human_readable_id
        if person_data.knowledge_source is not None:
            update_fields.append("p.knowledge_source = $knowledge_source")
            update_params["knowledge_source"] = person_data.knowledge_source
        if person_data.is_verified is not None:
            update_fields.append("p.is_verified = $is_verified")
            update_params["is_verified"] = person_data.is_verified
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # 构建更新查询
        update_query = f"""
        MATCH (p:Person {{id: $id}})
        SET {", ".join(update_fields)}
        RETURN p
        """
        
        # 执行更新查询
        result = neo4j_db.execute_query(update_query, update_params)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person not found"
            )
        
        person_data_result = result[0]["p"]
        updated_person = PersonResponse(
            id=person_data_result.get("id"),
            name=person_data_result.get("name"),
            birth_year=person_data_result.get("birth_year"),
            death_year=person_data_result.get("death_year"),
            occupation=person_data_result.get("occupation"),
            specialty=person_data_result.get("specialty"),
            hobby=person_data_result.get("hobby"),
            achievement=person_data_result.get("achievement"),
            female_experience=person_data_result.get("female_experience"),
            type=person_data_result.get("type"),
            frequency=person_data_result.get("frequency"),
            degree=person_data_result.get("degree"),
            description=person_data_result.get("description"),
            human_readable_id=person_data_result.get("human_readable_id"),
            knowledge_source=person_data_result.get("knowledge_source"),
            source_type=person_data_result.get("source_type"),
            created_by=person_data_result.get("created_by"),
            is_verified=person_data_result.get("is_verified", False),
            created_at=datetime.fromisoformat(person_data_result.get("created_at")) if person_data_result.get("created_at") else None
        )
        
        return updated_person
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update person: {str(e)}"
        )


@router.get("/me", response_model=PersonResponse)
async def get_my_person(
    current_user = Depends(get_current_user)
):
    """
    获取当前用户的Person节点
    """
    if not current_user.is_in_graph or not current_user.neo4j_person_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person node not found for current user"
        )
    
    try:
        # 从Neo4j获取当前用户的Person节点
        query = """
        MATCH (p:Person {id: $id})
        RETURN p
        """
        
        result = neo4j_db.execute_query(query, {"id": current_user.neo4j_person_id})
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person node not found"
            )
        
        person_data = result[0]["p"]
        person = PersonResponse(
            id=person_data.get("id"),
            name=person_data.get("name"),
            birth_year=person_data.get("birth_year"),
            death_year=person_data.get("death_year"),
            occupation=person_data.get("occupation"),
            specialty=person_data.get("specialty"),
            hobby=person_data.get("hobby"),
            achievement=person_data.get("achievement"),
            female_experience=person_data.get("female_experience"),
            type=person_data.get("type"),
            frequency=person_data.get("frequency"),
            degree=person_data.get("degree"),
            description=person_data.get("description"),
            human_readable_id=person_data.get("human_readable_id"),
            knowledge_source=person_data.get("knowledge_source"),
            source_type=person_data.get("source_type"),
            created_by=person_data.get("created_by"),
            is_verified=person_data.get("is_verified", False),
            created_at=datetime.fromisoformat(person_data.get("created_at")) if person_data.get("created_at") else None
        )
        
        return person
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve person: {str(e)}"
        )
