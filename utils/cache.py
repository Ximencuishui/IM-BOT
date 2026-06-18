"""
轻量级本地缓存工具

用于缓存高频访问的查询结果，减少数据库压力。
特点:
    - 基于字典的内存缓存
    - TTL自动过期
    - 线程安全
    - 支持缓存统计
"""
import time
import threading
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class CacheEntry:
    """缓存条目"""
    __slots__ = ('value', 'expires_at')

    def __init__(self, value, ttl: float):
        self.value = value
        self.expires_at = time.time() + ttl

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class MemoryCache:
    """线程安全的内存缓存"""

    def __init__(self, default_ttl: float = 60.0, cleanup_interval: float = 300.0):
        """
        初始化缓存

        Args:
            default_ttl: 默认过期时间(秒)
            cleanup_interval: 清理过期条目间隔(秒)
        """
        self._default_ttl = default_ttl
        self._data: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

        # 启动后台清理线程
        if cleanup_interval > 0:
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                args=(cleanup_interval,),
                daemon=True,
                name='cache-cleanup'
            )
            self._cleanup_thread.start()

    def get(self, key: str, default=None):
        """获取缓存值"""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._misses += 1
                return default

            if entry.is_expired:
                del self._data[key]
                self._misses += 1
                return default

            self._hits += 1
            return entry.value

    def set(self, key: str, value, ttl: float = None):
        """设置缓存值"""
        with self._lock:
            ttl = ttl if ttl is not None else self._default_ttl
            self._data[key] = CacheEntry(value, ttl)

    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            self._data.pop(key, None)

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._data.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> dict:
        """获取缓存统计"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                'size': len(self._data),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 4),
            }

    def _cleanup_loop(self, interval: float):
        """定期清理过期条目"""
        while True:
            time.sleep(interval)
            self._cleanup_expired()

    def _cleanup_expired(self):
        """清理所有过期条目"""
        with self._lock:
            now = time.time()
            expired_keys = [
                k for k, v in self._data.items()
                if now > v.expires_at
            ]
            for k in expired_keys:
                del self._data[k]
            if expired_keys:
                logger.debug(f"缓存清理: 移除了 {len(expired_keys)} 个过期条目")


# 全局缓存实例
cache = MemoryCache(default_ttl=60.0)


# ==================== 缓存装饰器 ====================

def cached(ttl: float = 60.0, key_prefix: str = '', ignore_args: tuple = ()):
    """
    函数结果缓存装饰器

    Args:
        ttl: 缓存生存时间(秒)
        key_prefix: 缓存键前缀
        ignore_args: 忽略的参数索引/名称（不纳入缓存键），如 (0, 'db') 忽略第一个位置参数和名为db的参数

    Usage:
        @cached(ttl=30, ignore_args=(0,))
        def get_dashboard_stats(db, user_id):
            ...

        @cached(ttl=300, key_prefix='user', ignore_args=('db',))
        def get_user(db, user_id):
            ...
    """
    def decorator(func):
        # 获取参数名称（用于ignore_args按名称排除）
        import inspect
        func_sig = inspect.signature(func)
        param_names = list(func_sig.parameters.keys())

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key_parts = [key_prefix or func.__name__]

            # 处理位置参数
            for idx, arg in enumerate(args):
                if idx in ignore_args or (idx < len(param_names) and param_names[idx] in ignore_args):
                    continue
                key_parts.append(str(arg))

            # 处理关键字参数
            for k, v in sorted(kwargs.items()):
                if k in ignore_args:
                    continue
                key_parts.append(f'{k}={v}')

            cache_key = ':'.join(key_parts)

            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 执行函数并缓存
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        # 添加清除缓存方法
        def invalidate(*args, **kwargs):
            key_parts = [key_prefix or func.__name__]
            for idx, arg in enumerate(args):
                if idx in ignore_args or (idx < len(param_names) and param_names[idx] in ignore_args):
                    continue
                key_parts.append(str(arg))
            for k, v in sorted(kwargs.items()):
                if k in ignore_args:
                    continue
                key_parts.append(f'{k}={v}')
            cache_key = ':'.join(key_parts)
            cache.delete(cache_key)

        wrapper.invalidate = invalidate
        wrapper.cache_stats = cache.get_stats

        return wrapper
    return decorator