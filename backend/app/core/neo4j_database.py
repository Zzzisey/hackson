"""
Neo4j数据库连接管理
"""
import logging
from typing import Optional
from neo4j import GraphDatabase, AsyncGraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jDatabase:
    """Neo4j数据库连接管理器"""
    
    def __init__(self):
        self._driver = None
        self._async_driver = None
        self._uri = settings.NEO4J_URL
        self._username = settings.NEO4J_USERNAME
        self._password = settings.NEO4J_PASSWORD
        self._database = settings.NEO4J_DATABASE
        
    def get_driver(self):
        """获取同步驱动"""
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    self._uri,
                    auth=(self._username, self._password),
                    database=self._database
                )
                # 测试连接
                self._driver.verify_connectivity()
                logger.info("Neo4j同步驱动连接成功")
            except Exception as e:
                logger.error(f"Neo4j同步驱动连接失败: {e}")
                raise
        return self._driver
    
    def get_async_driver(self):
        """获取异步驱动"""
        if self._async_driver is None:
            try:
                self._async_driver = AsyncGraphDatabase.driver(
                    self._uri,
                    auth=(self._username, self._password),
                    database=self._database
                )
                logger.info("Neo4j异步驱动创建成功")
            except Exception as e:
                logger.error(f"Neo4j异步驱动创建失败: {e}")
                raise
        return self._async_driver
    
    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j同步驱动已关闭")
        
        if self._async_driver:
            # 异步驱动需要异步关闭，这里只标记为None
            self._async_driver = None
            logger.info("Neo4j异步驱动已标记关闭")
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            driver = self.get_driver()
            with driver.session() as session:
                result = session.run("RETURN 1 AS test")
                value = result.single()["test"]
                return value == 1
        except Exception as e:
            logger.error(f"Neo4j连接测试失败: {e}")
            return False
    
    async def async_test_connection(self) -> bool:
        """异步测试数据库连接"""
        try:
            driver = self.get_async_driver()
            async with driver.session() as session:
                result = await session.run("RETURN 1 AS test")
                record = await result.single()
                value = record["test"]
                return value == 1
        except Exception as e:
            logger.error(f"Neo4j异步连接测试失败: {e}")
            return False
    
    def execute_query(self, query: str, parameters: Optional[dict] = None):
        """执行同步查询"""
        driver = self.get_driver()
        with driver.session() as session:
            try:
                result = session.run(query, parameters or {})
                return list(result)
            except Neo4jError as e:
                logger.error(f"Neo4j查询执行失败: {e}")
                raise
    
    async def execute_async_query(self, query: str, parameters: Optional[dict] = None):
        """执行异步查询"""
        driver = self.get_async_driver()
        async with driver.session() as session:
            try:
                result = await session.run(query, parameters or {})
                return await result.data()
            except Neo4jError as e:
                logger.error(f"Neo4j异步查询执行失败: {e}")
                raise


# 全局Neo4j数据库实例
neo4j_db = Neo4jDatabase()


def get_neo4j():
    """获取Neo4j数据库实例（依赖注入使用）"""
    return neo4j_db


async def get_neo4j_async():
    """获取异步Neo4j数据库实例"""
    return neo4j_db


async def close_neo4j():
    """关闭Neo4j连接"""
    neo4j_db.close()


# 初始化时测试连接
if __name__ == "__main__":
    # 简单测试
    db = Neo4jDatabase()
    if db.test_connection():
        print("Neo4j连接测试成功")
    else:
        print("Neo4j连接测试失败")
    db.close()
