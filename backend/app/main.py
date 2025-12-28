from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api import auth, users
from app.api.persons import router as persons_router
from app.api.graph import router as graph_router
from app.core.database import Base, engine
from app.core.config import settings


# 创建FastAPI应用
app = FastAPI(
    title="Hackson API",
    description="用户认证和管理API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(persons_router, prefix="/api")
app.include_router(graph_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("Starting up...")
    # 创建数据库表（仅开发环境使用，生产环境应使用迁移工具）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created (if not exist)")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    print("Shutting down...")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Hackson API",
        "docs": "/api/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
