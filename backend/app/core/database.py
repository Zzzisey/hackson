import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings

# 设置 SQLAlchemy 日志级别为 WARNING，这样就不会显示 INFO 级别的 SQL 查询日志
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # 设置为 False 也可以关闭 SQL 日志
    pool_pre_ping=True,  # 自动检测断开的连接
    pool_size=5,  # 连接池大小， 保持 5 个连接处于可用状态
    max_overflow=10,  # 最大溢出连接数
    pool_recycle=3600,  # 连接回收时间（秒）
    pool_timeout=30,  # 连接超时时间
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
    }
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# 创建基类
Base = declarative_base()

# 获取数据库会话的依赖函数
async def get_db():
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logging.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()

# 数据库连接测试函数
async def test_database_connection():
    """测试数据库连接"""
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logging.error(f"Database connection test failed: {e}")
        return False

# 关闭数据库引擎
async def close_database():
    """关闭数据库引擎"""
    try:
        await engine.dispose()
        logging.info("Database engine disposed successfully")
    except Exception as e:
        logging.error(f"Error disposing database engine: {e}") 