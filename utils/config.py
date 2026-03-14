"""
配置管理模块
"""

import yaml
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class ToolConfig:
    """工具配置"""
    enabled: bool = True
    path: str = ""
    timeout: int = 300
    max_retries: int = 3
    args: dict = field(default_factory=dict)


@dataclass
class GitConfig:
    """Git 配置"""
    auto_commit: bool = True
    auto_push: bool = True
    branch_prefix: str = "feature"
    commit_template: str = "{type}: {description}"
    user_name: str = ""
    user_email: str = ""


@dataclass
class TestConfig:
    """测试配置"""
    auto_test: bool = True
    coverage_threshold: float = 90.0
    test_framework: str = "pytest"
    timeout: int = 600


@dataclass
class EnvironmentConfig:
    """环境配置"""
    python_version: str = "3.13"
    node_version: str = "22"
    auto_install: bool = True
    check_ports: bool = True


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "DEBUG"
    save_json: bool = True
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5


@dataclass
class AgentConfig:
    """智能体主配置"""
    name: str = "auto-agent"
    version: str = "1.0.0"
    workspace: str = ""
    opencode: ToolConfig = field(default_factory=ToolConfig)
    qwencode: ToolConfig = field(default_factory=ToolConfig)
    git: GitConfig = field(default_factory=GitConfig)
    test: TestConfig = field(default_factory=TestConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    log: LogConfig = field(default_factory=LogConfig)
    
    @classmethod
    def from_yaml(cls, path: str) -> 'AgentConfig':
        """从 YAML 文件加载配置"""
        config_path = Path(path)
        if not config_path.exists():
            return cls()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        config = cls()
        
        # 解析基本配置
        for key, value in data.items():
            if hasattr(config, key) and value is not None:
                if isinstance(value, dict):
                    # 解析子配置
                    sub_config_class = getattr(config, key).__class__
                    if hasattr(sub_config_class, '__dataclass_fields__'):
                        sub_config = sub_config_class(**{
                            k: v for k, v in value.items() 
                            if k in sub_config_class.__dataclass_fields__
                        })
                        setattr(config, key, sub_config)
                else:
                    setattr(config, key, value)
        
        return config
    
    def to_yaml(self, path: str):
        """保存配置到 YAML 文件"""
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'name': self.name,
            'version': self.version,
            'workspace': self.workspace,
            'opencode': {
                'enabled': self.opencode.enabled,
                'path': self.opencode.path,
                'timeout': self.opencode.timeout,
                'max_retries': self.opencode.max_retries,
            },
            'qwencode': {
                'enabled': self.qwencode.enabled,
                'path': self.qwencode.path,
                'timeout': self.qwencode.timeout,
                'max_retries': self.qwencode.max_retries,
            },
            'git': {
                'auto_commit': self.git.auto_commit,
                'auto_push': self.git.auto_push,
                'branch_prefix': self.git.branch_prefix,
            },
            'test': {
                'auto_test': self.test.auto_test,
                'coverage_threshold': self.test.coverage_threshold,
                'test_framework': self.test.test_framework,
            },
            'environment': {
                'python_version': self.environment.python_version,
                'node_version': self.environment.node_version,
                'auto_install': self.environment.auto_install,
            },
            'log': {
                'level': self.log.level,
                'save_json': self.log.save_json,
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


# 默认配置路径
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


def load_config(config_path: Optional[str] = None) -> AgentConfig:
    """加载配置"""
    if config_path is None:
        config_path = str(DEFAULT_CONFIG_PATH)
    return AgentConfig.from_yaml(config_path)


def save_config(config: AgentConfig, config_path: Optional[str] = None):
    """保存配置"""
    if config_path is None:
        config_path = str(DEFAULT_CONFIG_PATH)
    config.to_yaml(config_path)
