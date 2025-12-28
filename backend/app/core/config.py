try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

from enum import Enum
from pathlib import Path
from typing import Optional

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    # settings (可选)
    API_KEY: Optional[str] = None
    API_SECRET: Optional[str] = None
    APP_ID: Optional[str] = None
    SPARKAI_URL: Optional[str] = None
    SPARKAI_DOMAIN: Optional[str] = None
    
    # mysql settings (必需)
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "1234"
    DB_NAME: str = "woman"

    # Neo4j settings (必需)
    NEO4J_URL: str = "bolt://localhost:7687"  # Bolt协议使用7687端口，HTTP使用7474端口
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "moyuanwoaini3"
    NEO4J_DATABASE: str = "neo4j"
    
    # JWT settings (必需)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Embedding settings (可选)
    EMBEDDING_TYPE: str = "ollama"
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_THRESHOLD: float = 0.90
    
    # GraphRAG settings (可选)
    GRAPHRAG_PROJECT_DIR: str = "llm_backend/app/graphrag"
    GRAPHRAG_DATA_DIR: str = "data"
    GRAPHRAG_QUERY_TYPE: str = "local"
    GRAPHRAG_RESPONSE_TYPE: str = "text"
    GRAPHRAG_COMMUNITY_LEVEL: int = 3
    GRAPHRAG_DYNAMIC_COMMUNITY: bool = False
    
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def NEO4J_CONN_URL(self) -> str:
        """构建Neo4j连接URL"""
        return f"{self.NEO4J_URL}"
    
    @property
    def PSYCOPG2_DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = str(ENV_FILE) if ENV_FILE.exists() else None
        env_file_encoding = "utf-8"
        case_sensitive = True



settings = Settings()
