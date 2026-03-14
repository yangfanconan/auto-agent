"""
交付打包模块
生成交付产物、文档、报告
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

try:
    from ..utils import get_logger, DeliveryException
except ImportError:
    from utils import get_logger, DeliveryException


@dataclass
class DeliveryItem:
    """交付项"""
    name: str
    path: str
    type: str  # file, directory
    description: str = ""


@dataclass
class DeliveryPackage:
    """交付包"""
    id: str
    name: str
    version: str
    created_at: str
    items: List[DeliveryItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "created_at": self.created_at,
            "items": [item.__dict__ for item in self.items],
            "metadata": self.metadata
        }


class DeliveryManager:
    """交付管理器"""
    
    def __init__(self, workspace: str = "."):
        self.logger = get_logger()
        self.workspace = Path(workspace)
        self.delivery_dir = self.workspace / "deliveries"
        self.delivery_dir.mkdir(parents=True, exist_ok=True)
    
    def create_package(
        self,
        name: str,
        version: str = "1.0.0",
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> DeliveryPackage:
        """
        创建交付包
        
        Args:
            name: 包名称
            version: 版本号
            include_patterns: 包含模式
            exclude_patterns: 排除模式
        
        Returns:
            DeliveryPackage: 交付包
        """
        self.logger.info(f"创建交付包：{name} v{version}")
        
        package_id = f"pkg_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        package = DeliveryPackage(
            id=package_id,
            name=name,
            version=version,
            created_at=datetime.now().isoformat()
        )
        
        # 默认包含模式
        if not include_patterns:
            include_patterns = [
                "*.py", "*.js", "*.ts", "*.java", "*.go",  # 源代码
                "*.md", "*.txt", "*.rst",  # 文档
                "requirements.txt", "package.json", "Cargo.toml",  # 依赖配置
                "config/*.yaml", "config/*.yml", "config/*.json",  # 配置
            ]
        
        # 默认排除模式
        if not exclude_patterns:
            exclude_patterns = [
                "__pycache__", "*.pyc", "*.pyo",  # Python 缓存
                "node_modules",  # Node 依赖
                ".git", ".svn",  # 版本控制
                "*.log",  # 日志
                "dist", "build", "target",  # 构建输出
                ".env", "*.env",  # 环境变量
                "*~", "*.swp",  # 编辑器临时文件
            ]
        
        # 收集文件
        items = self._collect_files(include_patterns, exclude_patterns)
        package.items = items
        
        # 创建交付目录
        package_path = self.delivery_dir / f"{name}_{version}"
        package_path.mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        self._copy_files(items, package_path)
        
        # 生成元数据
        self._generate_metadata(package, package_path)
        
        # 生成 README
        self._generate_readme(package, package_path)
        
        package.metadata["output_path"] = str(package_path)
        
        self.logger.info(f"交付包创建完成：{package_path}")
        
        return package
    
    def _collect_files(
        self,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> List[DeliveryItem]:
        """收集文件"""
        items = []
        excluded_paths = set()
        
        # 处理排除模式
        for pattern in exclude_patterns:
            for path in self.workspace.glob(f"**/{pattern}"):
                excluded_paths.add(path)
        
        # 处理包含模式
        for pattern in include_patterns:
            for path in self.workspace.glob(f"**/{pattern}"):
                # 检查是否在排除列表中
                if any(excluded in path.parents or excluded == path 
                       for excluded in excluded_paths):
                    continue
                
                # 跳过交付目录本身
                if self.delivery_dir in path.parents:
                    continue
                
                rel_path = path.relative_to(self.workspace)
                
                items.append(DeliveryItem(
                    name=rel_path.name,
                    path=str(rel_path),
                    type="directory" if path.is_dir() else "file",
                    description=f"项目文件：{rel_path}"
                ))
        
        return items
    
    def _copy_files(self, items: List[DeliveryItem], dest: Path):
        """复制文件到交付目录"""
        for item in items:
            src = self.workspace / item.path
            dst = dest / item.path
            
            try:
                if item.type == "directory":
                    if src.exists():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            except Exception as e:
                self.logger.warning(f"复制文件失败 {item.path}: {e}")
    
    def _generate_metadata(self, package: DeliveryPackage, dest: Path):
        """生成元数据文件"""
        metadata_file = dest / "delivery.json"
        
        metadata = {
            "package": package.to_dict(),
            "build_info": {
                "workspace": str(self.workspace),
                "timestamp": datetime.now().isoformat(),
            }
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def _generate_readme(self, package: DeliveryPackage, dest: Path):
        """生成 README 文件"""
        readme_content = f"""# {package.name} v{package.version}

**交付时间**: {package.created_at}

## 文件清单

"""
        for item in package.items[:50]:  # 限制显示数量
            icon = "📁" if item.type == "directory" else "📄"
            readme_content += f"- {icon} `{item.path}` - {item.description}\n"
        
        if len(package.items) > 50:
            readme_content += f"\n... 还有 {len(package.items) - 50} 个文件\n"
        
        readme_content += f"""

## 使用说明

请参考项目文档或源代码了解详细使用方法。

## 交付信息

- 交付包 ID: {package.id}
- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        readme_file = dest / "DELIVERY_README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def generate_report(
        self,
        plan_id: str,
        task_report: Dict,
        test_report: Optional[Dict] = None,
        git_report: Optional[Dict] = None
    ) -> str:
        """
        生成交付报告
        
        Args:
            plan_id: 计划 ID
            task_report: 任务报告
            test_report: 测试报告
            git_report: Git 报告
        
        Returns:
            str: 报告内容
        """
        report = f"""# 项目交付报告

**任务 ID**: {plan_id}
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 任务完成总览

"""
        # 任务状态
        status = task_report.get("status", "unknown")
        progress = task_report.get("overall_progress", 0)
        
        status_icon = {"completed": "✅", "failed": "❌", "in_progress": "🔄"}.get(status, "⏳")
        report += f"- **状态**: {status_icon} {status}\n"
        report += f"- **进度**: {progress:.1f}%\n"
        
        # 子任务完成情况
        subtasks = task_report.get("subtasks", [])
        completed = sum(1 for t in subtasks if t.get("status") == "completed")
        report += f"- **子任务**: {completed}/{len(subtasks)} 完成\n"
        
        # 测试报告
        if test_report:
            report += f"""
---

## 测试报告

- **总测试数**: {test_report.get('total', 0)}
- **通过**: {test_report.get('passed', 0)}
- **失败**: {test_report.get('failed', 0)}
- **覆盖率**: {test_report.get('coverage', 0):.1f}%
"""
        
        # Git 提交记录
        if git_report and git_report.get("success"):
            report += f"""
---

## Git 提交

- **分支**: {git_report.get('branch', 'N/A')}
- **提交**: {git_report.get('commit_hash', 'N/A')}
- **信息**: {git_report.get('message', 'N/A')}
"""
        
        # 交付产物
        report += """
---

## 交付产物

"""
        deliveries = list(self.delivery_dir.iterdir())
        if deliveries:
            for d in deliveries[-5:]:  # 最近 5 个交付
                report += f"- 📦 `{d.name}`\n"
        else:
            report += "- 暂无交付产物\n"
        
        # 异常说明
        report += """
---

## 异常与修复说明

全流程无异常

---

*报告由 Auto-Agent 自动生成*
"""
        
        return report
    
    def save_report(self, report: str, plan_id: str) -> str:
        """保存报告到文件"""
        report_dir = self.delivery_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"report_{plan_id}_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.logger.info(f"报告已保存：{report_file}")
        return str(report_file)
    
    def package_task(self, plan_id: str, subtask) -> str:
        """
        任务处理器接口
        
        Args:
            plan_id: 计划 ID
            subtask: 子任务
        
        Returns:
            str: 执行结果
        """
        try:
            name = subtask.metadata.get("package_name", "auto-agent-delivery")
            version = subtask.metadata.get("version", "1.0.0")
            
            # 创建交付包
            package = self.create_package(name, version)
            
            result = f"交付打包完成\n\n"
            result += f"包名称：{package.name}\n"
            result += f"版本：{package.version}\n"
            result += f"文件数：{len(package.items)}\n"
            result += f"输出路径：{package.metadata.get('output_path')}"
            
            return result
            
        except Exception as e:
            raise DeliveryException(f"交付打包失败：{e}")
