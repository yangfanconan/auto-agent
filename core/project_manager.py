"""
本地项目管理模块
支持项目收藏、分类、快速访问
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

try:
    from ..utils import get_logger
except ImportError:
    from utils import get_logger


@dataclass
class Project:
    """项目信息"""
    id: str
    name: str
    path: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: Optional[str] = None
    is_favorite: bool = False
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Project':
        return cls(**data)


class ProjectManager:
    """项目管理器"""
    
    def __init__(self, config_path: str = "~/.auto-agent/projects.json"):
        self.logger = get_logger()
        self.config_path = Path(config_path).expanduser()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._projects: Dict[str, Project] = {}
        self._load()
        
        self.logger.info(f"项目管理器已初始化，共 {len(self._projects)} 个项目")
    
    def _load(self):
        """加载项目数据"""
        if not self.config_path.exists():
            self._save()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for proj_data in data.get("projects", []):
                project = Project.from_dict(proj_data)
                self._projects[project.id] = project
            
            self.logger.info(f"已加载 {len(self._projects)} 个项目")
        
        except Exception as e:
            self.logger.error(f"加载项目数据失败：{e}")
    
    def _save(self):
        """保存项目数据"""
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "projects": [p.to_dict() for p in self._projects.values()],
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            self.logger.error(f"保存项目数据失败：{e}")
    
    def add_project(
        self,
        path: str,
        name: Optional[str] = None,
        description: str = "",
        tags: List[str] = None,
        is_favorite: bool = False
    ) -> Project:
        """添加项目"""
        path = str(Path(path).expanduser().resolve())
        
        # 检查是否已存在
        for project in self._projects.values():
            if project.path == path:
                self.logger.info(f"项目已存在：{path}")
                return project
        
        # 自动生成名称
        if not name:
            name = Path(path).name
        
        # 扫描项目信息
        metadata = self._scan_project_info(path)
        
        project = Project(
            id=f"proj_{datetime.now().strftime('%Y%m%d%H%M%S')}_{name[:4]}",
            name=name,
            path=path,
            description=description,
            tags=tags or [],
            is_favorite=is_favorite,
            metadata=metadata,
        )
        
        self._projects[project.id] = project
        self._save()
        
        self.logger.info(f"已添加项目：{project.name}")
        return project
    
    def remove_project(self, project_id: str) -> bool:
        """删除项目"""
        if project_id not in self._projects:
            return False
        
        project = self._projects[project_id]
        del self._projects[project_id]
        self._save()
        
        self.logger.info(f"已删除项目：{project.name}")
        return True
    
    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_favorite: Optional[bool] = None,
        notes: Optional[str] = None
    ) -> Optional[Project]:
        """更新项目"""
        if project_id not in self._projects:
            return None
        
        project = self._projects[project_id]
        
        if name:
            project.name = name
        if description is not None:
            project.description = description
        if tags is not None:
            project.tags = tags
        if is_favorite is not None:
            project.is_favorite = is_favorite
        if notes is not None:
            project.notes = notes
        
        project.updated_at = datetime.now().isoformat()
        self._save()
        
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """获取项目"""
        return self._projects.get(project_id)
    
    def get_project_by_path(self, path: str) -> Optional[Project]:
        """根据路径获取项目"""
        path = str(Path(path).expanduser())
        for project in self._projects.values():
            if project.path == path:
                return project
        return None
    
    def list_projects(
        self,
        favorite_only: bool = False,
        tag: Optional[str] = None
    ) -> List[Project]:
        """列出项目"""
        projects = list(self._projects.values())
        
        if favorite_only:
            projects = [p for p in projects if p.is_favorite]
        
        if tag:
            projects = [p for p in projects if tag in p.tags]
        
        # 按最后访问时间排序
        projects.sort(
            key=lambda p: p.last_accessed or p.created_at,
            reverse=True
        )
        
        return projects
    
    def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        tags = set()
        for project in self._projects.values():
            tags.update(project.tags)
        return sorted(list(tags))
    
    def access_project(self, project_id: str):
        """记录项目访问"""
        if project_id not in self._projects:
            return
        
        project = self._projects[project_id]
        project.last_accessed = datetime.now().isoformat()
        self._save()
    
    def _scan_project_info(self, path: str) -> Dict[str, Any]:
        """扫描项目信息"""
        path = Path(path)
        metadata = {
            "type": "unknown",
            "has_git": False,
            "has_python": False,
            "has_node": False,
            "has_rust": False,
            "has_go": False,
        }
        
        if not path.exists():
            metadata["exists"] = False
            return metadata
        
        metadata["exists"] = True
        
        # 检查 Git
        if (path / ".git").exists():
            metadata["has_git"] = True
        
        # 检查 Python
        if (path / "requirements.txt").exists() or \
           (path / "setup.py").exists() or \
           (path / "pyproject.toml").exists():
            metadata["type"] = "python"
            metadata["has_python"] = True
        
        # 检查 Node.js
        if (path / "package.json").exists():
            metadata["type"] = "nodejs"
            metadata["has_node"] = True
        
        # 检查 Rust
        if (path / "Cargo.toml").exists():
            metadata["type"] = "rust"
            metadata["has_rust"] = True
        
        # 检查 Go
        if (path / "go.mod").exists():
            metadata["type"] = "go"
            metadata["has_go"] = True
        
        # 自动添加标签
        tags = []
        if metadata["has_git"]:
            tags.append("git")
        if metadata["has_python"]:
            tags.append("python")
        if metadata["has_node"]:
            tags.append("nodejs")
        if metadata["has_rust"]:
            tags.append("rust")
        if metadata["has_go"]:
            tags.append("go")
        
        metadata["auto_tags"] = tags
        
        return metadata
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        projects = list(self._projects.values())
        
        return {
            "total": len(projects),
            "favorites": sum(1 for p in projects if p.is_favorite),
            "by_type": {
                "python": sum(1 for p in projects if p.metadata.get("has_python")),
                "nodejs": sum(1 for p in projects if p.metadata.get("has_node")),
                "rust": sum(1 for p in projects if p.metadata.get("has_rust")),
                "go": sum(1 for p in projects if p.metadata.get("has_go")),
            },
            "tags": self.get_all_tags(),
        }
    
    def search_projects(self, query: str) -> List[Project]:
        """搜索项目"""
        query_lower = query.lower()
        results = []
        
        for project in self._projects.values():
            # 搜索名称、描述、标签、路径
            if query_lower in project.name.lower() or \
               query_lower in project.description.lower() or \
               query_lower in project.path.lower() or \
               any(query_lower in tag.lower() for tag in project.tags):
                results.append(project)
        
        return results


# 全局项目管理器实例
_global_manager: Optional[ProjectManager] = None


def get_project_manager(config_path: str = "~/.auto-agent/projects.json") -> ProjectManager:
    """获取全局项目管理器实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = ProjectManager(config_path)
    return _global_manager
