"""
日志系统模块
提供结构化日志记录功能

增强版：集成事件总线
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str = "auto-agent", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 生成日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{name}_{timestamp}.log"
        self.json_log_file = self.log_dir / f"{name}_{timestamp}.json"

        # 配置日志
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # 文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)

        # JSON 日志存储
        self.json_logs = []

    def _log_json(self, level: str, message: str, extra: dict = None):
        """记录 JSON 格式日志并推送事件"""
        log_entry = {
            "timestamp": datetime.now().timestamp(),
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "message": message,
            "extra": extra or {}
        }
        self.json_logs.append(log_entry)
        
        # 延迟导入，避免循环依赖
        try:
            from core.events import publish_event
            publish_event(
                event_type="system.log",
                payload=log_entry,
                source="logger"
            )
        except (ImportError, Exception):
            pass  # 如果事件总线不可用，只记录日志

    def debug(self, message: str, extra: dict = None):
        self.logger.debug(message)
        self._log_json("DEBUG", message, extra)

    def info(self, message: str, extra: dict = None):
        self.logger.info(message)
        self._log_json("INFO", message, extra)

    def warning(self, message: str, extra: dict = None):
        self.logger.warning(message)
        self._log_json("WARNING", message, extra)

    def error(self, message: str, extra: dict = None):
        self.logger.error(message)
        self._log_json("ERROR", message, extra)

    def critical(self, message: str, extra: dict = None):
        self.logger.critical(message)
        self._log_json("CRITICAL", message, extra)

    def task_start(self, task_id: str, task_name: str):
        """记录任务开始"""
        self.info(f"任务开始：{task_name}", {"task_id": task_id, "task_name": task_name})

    def task_end(self, task_id: str, task_name: str, status: str, duration: float):
        """记录任务结束"""
        self.info(
            f"任务结束：{task_name}",
            {"task_id": task_id, "task_name": task_name, "status": status, "duration": duration}
        )

    def tool_call(self, tool_name: str, params: dict, result: str, success: bool):
        """记录工具调用"""
        level = "INFO" if success else "ERROR"
        self._log_json(level, f"工具调用：{tool_name}", {
            "tool_name": tool_name,
            "params": params,
            "result": result,
            "success": success
        })

    def save_json_log(self):
        """保存 JSON 日志到文件"""
        with open(self.json_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.json_logs, f, ensure_ascii=False, indent=2)

    def get_log_path(self) -> str:
        """获取日志文件路径"""
        return str(self.log_file)

    def get_json_log_path(self) -> str:
        """获取 JSON 日志文件路径"""
        return str(self.json_log_file)
    
    def get_recent_logs(self, limit: int = 100) -> list:
        """获取最近的日志"""
        return self.json_logs[-limit:]


# 全局日志实例
_global_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "auto-agent", log_dir: str = "logs") -> StructuredLogger:
    """获取全局日志实例"""
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(name, log_dir)
    return _global_logger
