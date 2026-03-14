"""
环境自动化模块
扫描、检测、修复运行环境

增强版：虚拟环境管理、Docker 支持
"""

import subprocess
import sys
import platform
import venv
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

try:
    from ..utils import get_logger, EnvironmentException, ToolConfig
    from ..adapters import get_tool
except ImportError:
    from utils import get_logger, EnvironmentException, ToolConfig
    from adapters import get_tool


@dataclass
class EnvironmentStatus:
    """环境状态"""
    component: str
    installed: bool
    version: Optional[str] = None
    path: Optional[str] = None
    status: str = "unknown"  # ok, warning, error, missing
    message: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class EnvironmentReport:
    """环境报告"""
    os_info: str
    python_version: str
    node_version: Optional[str]
    git_version: Optional[str]
    opencode_available: bool
    qwencode_available: bool
    components: List[EnvironmentStatus] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "os_info": self.os_info,
            "python_version": self.python_version,
            "node_version": self.node_version,
            "git_version": self.git_version,
            "opencode_available": self.opencode_available,
            "qwencode_available": self.qwencode_available,
            "components": [c.__dict__ for c in self.components],
            "issues": self.issues,
            "recommendations": self.recommendations
        }


class EnvironmentManager:
    """环境管理器（增强版）"""

    def __init__(self, workspace: str = "."):
        self.logger = get_logger()
        self.workspace = Path(workspace)
        self._report: Optional[EnvironmentReport] = None
    
    def create_venv(
        self,
        venv_path: Optional[str] = None,
        python_version: Optional[str] = None,
        with_pip: bool = True
    ) -> bool:
        """
        创建虚拟环境
        
        Args:
            venv_path: 虚拟环境路径（默认：./.venv）
            python_version: Python 版本（可选）
            with_pip: 是否安装 pip
        
        Returns:
            bool: 是否创建成功
        """
        venv_path = Path(venv_path) if venv_path else self.workspace / ".venv"
        
        try:
            self.logger.info(f"创建虚拟环境：{venv_path}")
            
            # 创建虚拟环境
            builder = venv.EnvBuilder(
                system_site_packages=False,
                clear=False,
                symlinks=False,
                with_pip=with_pip,
            )
            builder.create(str(venv_path))
            
            # 验证创建
            pip_path = venv_path / "bin" / "pip" if platform.system() != "Windows" else venv_path / "Scripts" / "pip.exe"
            if pip_path.exists():
                self.logger.info(f"虚拟环境创建成功：{venv_path}")
                return True
            else:
                self.logger.warning(f"虚拟环境已创建但未找到 pip: {venv_path}")
                return True
        
        except Exception as e:
            self.logger.error(f"创建虚拟环境失败：{e}")
            return False
    
    def check_venv(self, venv_path: Optional[str] = None) -> bool:
        """检查虚拟环境是否存在"""
        venv_path = Path(venv_path) if venv_path else self.workspace / ".venv"
        
        if platform.system() != "Windows":
            python_path = venv_path / "bin" / "python"
            pip_path = venv_path / "bin" / "pip"
        else:
            python_path = venv_path / "Scripts" / "python.exe"
            pip_path = venv_path / "Scripts" / "pip.exe"
        
        return python_path.exists() and pip_path.exists()
    
    def install_requirements(
        self,
        requirements_path: Optional[str] = None,
        venv_path: Optional[str] = None
    ) -> bool:
        """
        安装依赖
        
        Args:
            requirements_path: requirements.txt 路径
            venv_path: 虚拟环境路径
        
        Returns:
            bool: 是否安装成功
        """
        requirements_path = Path(requirements_path) if requirements_path else self.workspace / "requirements.txt"
        
        if not requirements_path.exists():
            self.logger.warning(f"requirements.txt 不存在：{requirements_path}")
            return False
        
        try:
            # 确定 pip 路径
            if venv_path:
                venv = Path(venv_path)
                pip_path = venv / "bin" / "pip" if platform.system() != "Windows" else venv / "Scripts" / "pip.exe"
            else:
                pip_path = Path(sys.executable).parent / "pip"
            
            if not pip_path.exists():
                pip_path = Path("pip")  # 回退到系统 pip
            
            self.logger.info(f"安装依赖：{requirements_path}")
            
            result = subprocess.run(
                [str(pip_path), "install", "-r", str(requirements_path), "-q"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.workspace)
            )
            
            if result.returncode == 0:
                self.logger.info("依赖安装成功")
                return True
            else:
                self.logger.error(f"依赖安装失败：{result.stderr}")
                return False
        
        except Exception as e:
            self.logger.error(f"安装依赖异常：{e}")
            return False
    
    def check_docker_support(self) -> bool:
        """检查 Docker 支持"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def run_in_docker(
        self,
        image: str,
        command: str,
        volumes: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        在 Docker 容器中运行命令
        
        Args:
            image: Docker 镜像
            command: 要执行的命令
            volumes: 挂载卷列表
        
        Returns:
            Tuple[bool, str]: (成功与否，输出)
        """
        try:
            cmd = ["docker", "run", "--rm"]
            
            # 添加卷挂载
            if volumes:
                for vol in volumes:
                    cmd.extend(["-v", vol])
            
            # 添加工作目录
            cmd.extend(["-w", "/workspace"])
            
            # 添加镜像和命令
            cmd.extend([image, "bash", "-c", command])
            
            self.logger.info(f"在 Docker 中执行：{' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(self.workspace)
            )
            
            return result.returncode == 0, result.stdout
        
        except Exception as e:
            return False, str(e)
    
    def scan(self) -> EnvironmentReport:
        """
        扫描当前环境
        
        Returns:
            EnvironmentReport: 环境报告
        """
        self.logger.info("开始扫描环境...")
        
        # 操作系统信息
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        
        # Python 版本
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # 检查各组件
        components = []
        issues = []
        recommendations = []
        
        # Node.js
        node_version, node_path = self._check_command("node", "--version")
        node_status = EnvironmentStatus(
            component="Node.js",
            installed=node_version is not None,
            version=node_version,
            path=node_path,
            status="ok" if node_version else "missing",
            message=node_version or "Node.js 未安装",
            auto_fixable=True
        )
        components.append(node_status)
        if not node_version:
            issues.append("Node.js 未安装")
            recommendations.append("建议安装 Node.js 22+")
        
        # Git
        git_version, git_path = self._check_command("git", "--version")
        git_status = EnvironmentStatus(
            component="Git",
            installed=git_version is not None,
            version=git_version,
            path=git_path,
            status="ok" if git_version else "missing",
            message=git_version or "Git 未安装",
            auto_fixable=False
        )
        components.append(git_status)
        if not git_version:
            issues.append("Git 未安装")
            recommendations.append("建议安装 Git")
        
        # Opencode
        opencode = get_tool("opencode")
        opencode_available = opencode is not None and hasattr(opencode, 'is_available') and opencode.is_available
        opencode_status = EnvironmentStatus(
            component="Opencode",
            installed=opencode_available,
            version=opencode.version if opencode_available else None,
            path=str(opencode._path) if opencode_available else None,
            status="ok" if opencode_available else "missing",
            message="Opencode 可用" if opencode_available else "Opencode 未找到",
            auto_fixable=True
        )
        components.append(opencode_status)
        if not opencode_available:
            issues.append("Opencode 不可用")
            recommendations.append("检查 Opencode 安装路径配置")
        
        # Qwencode
        qwencode = get_tool("qwencode")
        qwencode_available = qwencode is not None and hasattr(qwencode, 'is_available') and qwencode.is_available
        qwencode_status = EnvironmentStatus(
            component="Qwencode",
            installed=qwencode_available,
            version=qwencode.version if qwencode_available else None,
            path=str(qwencode._path) if qwencode_available else None,
            status="ok" if qwencode_available else "warning",
            message="Qwencode 可用" if qwencode_available else "Qwencode 未找到（可选）",
            auto_fixable=True
        )
        components.append(qwencode_status)
        if not qwencode_available:
            recommendations.append("Qwencode 为可选工具，安装后可支持批量代码生成")
        
        # 检查 Python 依赖
        self._check_python_dependencies(components, issues, recommendations)
        
        # 检查项目依赖
        self._check_project_dependencies(components, issues, recommendations)
        
        # 创建环境报告
        self._report = EnvironmentReport(
            os_info=os_info,
            python_version=python_version,
            node_version=node_version.strip().lstrip('v') if node_version else None,
            git_version=git_version.split()[-1] if git_version else None,
            opencode_available=opencode_available,
            qwencode_available=qwencode_available,
            components=components,
            issues=issues,
            recommendations=recommendations
        )
        
        self.logger.info(f"环境扫描完成：{len(issues)} 个问题，{len(recommendations)} 条建议")
        
        return self._report
    
    def _check_command(self, cmd: str, version_arg: str) -> Tuple[Optional[str], Optional[str]]:
        """检查命令是否存在并获取版本"""
        try:
            # 查找命令路径
            which_result = subprocess.run(
                ["which", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if which_result.returncode != 0:
                return None, None
            
            cmd_path = which_result.stdout.strip()
            
            # 获取版本
            version_result = subprocess.run(
                [cmd_path, version_arg],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if version_result.returncode == 0:
                return version_result.stdout.strip(), cmd_path
            
            return None, cmd_path
            
        except Exception as e:
            self.logger.debug(f"检查命令 {cmd} 失败：{e}")
            return None, None
    
    def _check_python_dependencies(
        self,
        components: List[EnvironmentStatus],
        issues: List[str],
        recommendations: List[str]
    ):
        """检查 Python 依赖"""
        required_packages = [
            ("pyyaml", "PyYAML", "YAML 配置文件支持"),
            ("git", "GitPython", "Git 操作支持"),
            ("pytest", "pytest", "测试框架"),
        ]
        
        for import_name, package_name, description in required_packages:
            try:
                __import__(import_name)
                status = EnvironmentStatus(
                    component=package_name,
                    installed=True,
                    status="ok",
                    message=f"{package_name} 已安装"
                )
            except ImportError:
                status = EnvironmentStatus(
                    component=package_name,
                    installed=False,
                    status="warning",
                    message=f"{package_name} 未安装",
                    auto_fixable=True
                )
                issues.append(f"{package_name} 未安装")
                recommendations.append(f"运行 pip install {package_name.lower()} 安装")
            
            components.append(status)
    
    def _check_project_dependencies(
        self,
        components: List[EnvironmentStatus],
        issues: List[str],
        recommendations: List[str]
    ):
        """检查项目依赖"""
        # 检查 requirements.txt
        requirements_file = self.workspace / "requirements.txt"
        if requirements_file.exists():
            components.append(EnvironmentStatus(
                component="requirements.txt",
                installed=True,
                status="ok",
                message="项目依赖文件存在"
            ))
        else:
            components.append(EnvironmentStatus(
                component="requirements.txt",
                installed=False,
                status="info",
                message="未找到 requirements.txt"
            ))
        
        # 检查 package.json
        package_json = self.workspace / "package.json"
        if package_json.exists():
            components.append(EnvironmentStatus(
                component="package.json",
                installed=True,
                status="ok",
                message="Node.js 项目配置文件存在"
            ))
        else:
            components.append(EnvironmentStatus(
                component="package.json",
                installed=False,
                status="info",
                message="未找到 package.json"
            ))
    
    def fix(self, report: Optional[EnvironmentReport] = None) -> bool:
        """
        自动修复环境问题
        
        Args:
            report: 环境报告，如不提供则先扫描
        
        Returns:
            bool: 是否成功修复所有可修复的问题
        """
        if report is None:
            report = self.scan()
        
        self.logger.info("开始修复环境问题...")
        
        fixed_count = 0
        total_fixable = 0
        
        for component in report.components:
            if component.status in ["missing", "warning"] and component.auto_fixable:
                total_fixable += 1
                
                if component.component == "PyYAML":
                    if self._install_package("pyyaml"):
                        fixed_count += 1
                elif component.component == "GitPython":
                    if self._install_package("gitpython"):
                        fixed_count += 1
                elif component.component == "pytest":
                    if self._install_package("pytest"):
                        fixed_count += 1
        
        success = fixed_count == total_fixable if total_fixable > 0 else True
        
        self.logger.info(f"环境修复完成：{fixed_count}/{total_fixable} 已修复")
        
        return success
    
    def _install_package(self, package: str) -> bool:
        """安装 Python 包"""
        try:
            self.logger.info(f"安装 Python 包：{package}")
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "-q"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                self.logger.info(f"{package} 安装成功")
                return True
            else:
                self.logger.error(f"{package} 安装失败：{result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"安装 {package} 异常：{e}")
            return False
    
    def get_report(self) -> Optional[EnvironmentReport]:
        """获取环境报告"""
        return self._report
    
    def setup(self, plan_id: str, subtask) -> str:
        """
        任务处理器接口
        
        Args:
            plan_id: 计划 ID
            subtask: 子任务
        
        Returns:
            str: 执行结果
        """
        try:
            report = self.scan()
            
            # 尝试自动修复
            if report.issues:
                self.fix(report)
                report = self.scan()  # 重新扫描
            
            # 生成报告
            result = f"环境检查完成\n\n"
            result += f"操作系统：{report.os_info}\n"
            result += f"Python: {report.python_version}\n"
            result += f"Node.js: {report.node_version or '未安装'}\n"
            result += f"Git: {report.git_version or '未安装'}\n"
            result += f"Opencode: {'可用' if report.opencode_available else '不可用'}\n"
            result += f"Qwencode: {'可用' if report.qwencode_available else '不可用'}\n"
            
            if report.issues:
                result += f"\n问题：{', '.join(report.issues)}"
            
            return result
            
        except Exception as e:
            raise EnvironmentException(f"环境检查失败：{e}")
