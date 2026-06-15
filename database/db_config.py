"""
数据库配置与连接管理
支持SQLite(默认)和MySQL
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings

# 根据数据库类型配置引擎参数
if settings.DB_TYPE == 'sqlite':
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={'check_same_thread': False}  # SQLite允许多线程访问
    )
    # 启用外键支持 (SQLite默认不启用)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True
    )

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话依赖(Flask路由中使用)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """获取数据库会话实例(服务层使用)"""
    return SessionLocal()


def init_db():
    """初始化数据库(创建所有表)"""
    Base.metadata.create_all(bind=engine)
