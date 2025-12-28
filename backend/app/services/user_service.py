from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.neo4j_database import neo4j_db
import uuid
from datetime import datetime


# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """通过邮箱获取用户"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    """创建新用户"""
    # 检查邮箱是否已存在
    existing_user = await get_user_by_email(db, user_create.email)
    if existing_user:
        raise ValueError("Email already registered")
    
    # 创建用户对象
    db_user = User(
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
        full_name=user_create.full_name,
        is_active=True
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # 在Neo4j中创建对应的Person节点
    try:
        person_id = str(uuid.uuid4())
        query = """
        CREATE (p:Person {
            id: $id,
            name: $name,
            birth_year: $birth_year,
            occupation: $occupation,
            specialty: $specialty,
            achievement: $achievement,
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
            "name": user_create.full_name or user_create.email.split("@")[0],  # 使用全名或邮箱用户名部分
            "birth_year": 1995,  # 默认出生年份
            "occupation": ["User"],
            "specialty": ["User"],
            "achievement": "New user registration",
            "type": "user",  # 设置为'user'类型，与前端创建时一致
            "frequency": 1,
            "degree": 1,
            "description": f"用户 {user_create.full_name or user_create.email.split('@')[0]} 的个人档案",
            "human_readable_id": "0",
            "knowledge_source": "用户创建",
            "source_type": "user_created",  # 设置为'user_created'，与前端创建时一致
            "created_by": user_create.email,
            "is_verified": False,
            "created_at": datetime.now().isoformat()
        }
        
        # 执行查询
        result = neo4j_db.execute_query(query, params)
        
        if not result:
            raise Exception("Failed to create Person node in Neo4j")
        
        # 更新用户记录，关联Neo4j Person节点
        db_user.neo4j_person_id = person_id
        db_user.is_in_graph = True
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        print(f"Successfully created Person node for user {user_create.email} with ID: {person_id}")
    except Exception as e:
        # Neo4j操作失败，记录错误但不阻止用户注册
        print(f"Failed to create Neo4j Person node for user {user_create.email}: {str(e)}")
        # 设置用户为未在图中状态
        db_user.is_in_graph = False
        db_user.neo4j_person_id = None
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
    
    return db_user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """验证用户凭据"""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
