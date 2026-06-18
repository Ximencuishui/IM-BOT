"""
数据库配置与连接管理
支持SQLite(默认)和MySQL

性能优化:
    - SQLite: WAL模式 + 缓存调优 + 同步模式优化
    - MySQL: 连接池调优 + 健康检查
    - 连接自动回收，防止泄漏
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings


def _configure_sqlite_engine():
    """配置SQLite引擎 - 性能优化"""
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={
            'check_same_thread': False,  # 允许多线程访问
            'timeout': 15,               # 连接超时(秒)
        }
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """SQLite连接时设置性能优化参数"""
        cursor = dbapi_connection.cursor()
        # 启用外键约束
        cursor.execute("PRAGMA foreign_keys=ON")
        # WAL模式 - 大幅提升并发读写性能
        cursor.execute("PRAGMA journal_mode=WAL")
        # 64MB缓存 (~64000页, 每页1KB)
        cursor.execute("PRAGMA cache_size=-64000")
        # 同步模式设为NORMAL (WAL模式下安全)
        cursor.execute("PRAGMA synchronous=NORMAL")
        # 临时表存储在内存中
        cursor.execute("PRAGMA temp_store=MEMORY")
        # 内存映射 (-1=禁用, 0=系统默认, n=n页)
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
        cursor.close()

    return engine


def _configure_mysql_engine():
    """配置MySQL引擎 - 连接池优化"""
    return create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=10,                  # 连接池大小
        max_overflow=20,               # 最大溢出连接数
        pool_recycle=3600,             # 连接回收时间(1小时)
        pool_pre_ping=True,            # 使用前ping检测连接有效性
        pool_timeout=30,               # 等待连接超时(秒)
        connect_args={
            'connect_timeout': 10,      # 连接超时(秒)
        }
    )


# 根据数据库类型配置引擎参数
if settings.DB_TYPE == 'sqlite':
    engine = _configure_sqlite_engine()
else:
    engine = _configure_mysql_engine()

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