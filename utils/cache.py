"""
缓存层模块
提供代码生成缓存、任务结果缓存等功能
"""

import hashlib
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from dataclasses import dataclass

try:
    from ..utils import get_logger
except ImportError:
    from utils import get_logger


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    ttl: int  # 秒
    hits: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.created_at > self.ttl
    
    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at,
            "ttl": self.ttl,
            "hits": self.hits,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CacheEntry':
        return cls(
            key=data["key"],
            value=data["value"],
            created_at=data.get("created_at", time.time()),
            ttl=data.get("ttl", 3600),
            hits=data.get("hits", 0)
        )


class CacheLayer:
    """缓存层"""
    
    def __init__(self, cache_dir: str = ".cache", ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.ttl = ttl  # 默认 TTL（秒）
        self.logger = get_logger()
        
        # 内存缓存
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._memory_cache_enabled = True
        
        # 统计
        self._stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "deletes": 0,
        }
        
        self.logger.info(f"缓存层已初始化，目录：{self.cache_dir}")
    
    def _get_key(self, content: str) -> str:
        """生成缓存键"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cache_file(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        # 先检查内存缓存
        if self._memory_cache_enabled and key in self._memory_cache:
            entry = self._memory_cache[key]
            if entry.is_expired():
                del self._memory_cache[key]
            else:
                entry.hits += 1
                self._stats["hits"] += 1
                self.logger.debug(f"内存缓存命中：{key}")
                return entry.value
        
        # 检查文件缓存
        cache_file = self._get_cache_file(key)
        if not cache_file.exists():
            self._stats["misses"] += 1
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            entry = CacheEntry.from_dict(data)
            
            if entry.is_expired():
                cache_file.unlink()
                self._stats["misses"] += 1
                self.logger.debug(f"缓存已过期：{key}")
                return None
            
            # 更新命中数
            entry.hits += 1
            self._stats["hits"] += 1
            
            # 写回内存缓存
            if self._memory_cache_enabled:
                self._memory_cache[key] = entry
            
            self.logger.debug(f"缓存命中：{key}")
            return entry.value
        
        except Exception as e:
            self.logger.error(f"读取缓存失败：{e}")
            self._stats["misses"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存"""
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl or self.ttl
        )
        
        # 写入文件缓存
        cache_file = self._get_cache_file(key)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)
            
            self._stats["writes"] += 1
            
            # 写入内存缓存
            if self._memory_cache_enabled:
                self._memory_cache[key] = entry
            
            self.logger.debug(f"缓存已设置：{key}")
        
        except Exception as e:
            self.logger.error(f"写入缓存失败：{e}")
    
    def delete(self, key: str):
        """删除缓存"""
        cache_file = self._get_cache_file(key)
        if cache_file.exists():
            cache_file.unlink()
            self._stats["deletes"] += 1
        
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        self.logger.debug(f"缓存已删除：{key}")
    
    def clear(self):
        """清空缓存"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        
        self._memory_cache.clear()
        self.logger.info("缓存已清空")
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                entry = CacheEntry.from_dict(data)
                if entry.is_expired():
                    cache_file.unlink()
                    count += 1
            except:
                pass
        
        # 清理内存缓存
        expired_keys = [k for k, v in self._memory_cache.items() if v.is_expired()]
        for key in expired_keys:
            del self._memory_cache[key]
        
        if count > 0:
            self.logger.info(f"清理了 {count} 个过期缓存")
        
        return count
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            **self._stats,
            "memory_entries": len(self._memory_cache),
            "file_entries": len(cache_files),
            "total_size_bytes": total_size,
            "hit_rate": self._stats["hits"] / (self._stats["hits"] + self._stats["misses"]) if (self._stats["hits"] + self._stats["misses"]) > 0 else 0,
        }
    
    # ============ 便捷方法 ============
    
    def cache_code(self, description: str, code: str, language: str = "python") -> str:
        """缓存生成的代码"""
        key = f"code:{language}:{self._get_key(description)}"
        self.set(key, {
            "code": code,
            "language": language,
            "description": description,
        }, ttl=86400 * 7)  # 7 天
        return key
    
    def get_cached_code(self, description: str, language: str = "python") -> Optional[str]:
        """获取缓存的代码"""
        key = f"code:{language}:{self._get_key(description)}"
        data = self.get(key)
        return data["code"] if data else None
    
    def cache_task_result(self, task_id: str, result: Dict) -> str:
        """缓存任务结果"""
        key = f"task:{task_id}"
        self.set(key, result, ttl=86400 * 30)  # 30 天
        return key
    
    def get_cached_task_result(self, task_id: str) -> Optional[Dict]:
        """获取缓存的任务结果"""
        key = f"task:{task_id}"
        return self.get(key)
    
    def cache_tool_response(self, tool_name: str, prompt: str, response: str) -> str:
        """缓存工具响应"""
        key = f"tool:{tool_name}:{self._get_key(prompt)}"
        self.set(key, {
            "response": response,
            "tool": tool_name,
            "prompt": prompt,
        }, ttl=86400)  # 1 天
        return key
    
    def get_cached_tool_response(self, tool_name: str, prompt: str) -> Optional[str]:
        """获取缓存的工具响应"""
        key = f"tool:{tool_name}:{self._get_key(prompt)}"
        data = self.get(key)
        return data["response"] if data else None


# 全局缓存实例
_global_cache: Optional[CacheLayer] = None


def get_cache(cache_dir: str = ".cache", ttl: int = 3600) -> CacheLayer:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheLayer(cache_dir, ttl)
    return _global_cache


def cache_code(description: str, code: str, language: str = "python"):
    """便捷函数：缓存代码"""
    return get_cache().cache_code(description, code, language)


def get_cached_code(description: str, language: str = "python") -> Optional[str]:
    """便捷函数：获取缓存代码"""
    return get_cache().get_cached_code(description, language)
