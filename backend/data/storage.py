from contextlib import contextmanager
from typing import Generator

from config import config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# ─── 引擎单例 ──────────────────────────────────────────────────────────────────
_engine: Engine | None = None


def get_engine() -> Engine:
    """获取 SQLAlchemy Engine 单例（懒加载）"""
    global _engine
    if _engine is None:
        import os

        os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{config.DB_PATH}",
            # SQLite 连接参数
            connect_args={
                "check_same_thread": False,  # FastAPI 多线程环境需要
                "timeout": 30,  # 等锁超时（秒）
            },
            # 连接池配置（SQLite 用 StaticPool 或默认即可）
            pool_pre_ping=True,
            echo=False,  # 设为 True 可打印所有 SQL，调试时用
        )

        # 开启 WAL 模式：提升并发读写性能，减少锁竞争
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    SQLAlchemy Session 上下文管理器。

    用法：
        with get_session() as session:
            session.add(some_obj)
            # commit 在 __exit__ 自动执行
            # 若发生异常则自动 rollback

    注意：
        - 不要在 with 块外部继续使用 session
        - 查询结果如需在块外使用，请先转换为普通 Python 对象
    """
    session = Session(get_engine(), expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engine() -> None:
    """释放连接池（应用关闭时调用）"""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
