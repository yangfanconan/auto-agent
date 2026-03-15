好的，由于权限限制，我无法直接执行命令或创建文件。让我为你提供完整的系统配置分析代码，你可以手动保存并运行：

## 系统配置分析脚本

创建文件 `system_info.py`，代码如下：

```python
#!/usr/bin/env python3
"""
系统配置分析工具
用于获取和展示电脑的硬件和软件配置信息
"""

import platform
import subprocess
import shutil
import os
import sys


def get_os_info():
    """获取操作系统信息"""
    info = {
        "系统": platform.system(),
        "版本": platform.version(),
        "机器": platform.machine(),
        "处理器": platform.processor() or "未知",
    }
    
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["sw_vers", "-productVersion"],
                capture_output=True, text=True, check=True
            )
            info["macOS 版本"] = result.stdout.strip()
        except subprocess.SubprocessError:
            pass
        info["架构"] = platform.machine()
        
    elif platform.system() == "Windows":
        info["Windows 版本"] = platform.win32_ver()[0]
        
    elif platform.system() == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        info["发行版"] = line.split("=")[1].strip().strip('"')
                        break
        except FileNotFoundError:
            pass
    
    return info


def get_cpu_info():
    """获取 CPU 信息"""
    info = {}
    
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, check=True
            )
            info["处理器名称"] = result.stdout.strip()
        except subprocess.SubprocessError:
            info["处理器名称"] = platform.processor()
        
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.physicalcpu"],
                capture_output=True, text=True, check=True
            )
            info["物理核心数"] = int(result.stdout.strip())
        except subprocess.SubprocessError:
            pass
        
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.logicalcpu"],
                capture_output=True, text=True, check=True
            )
            info["逻辑核心数"] = int(result.stdout.strip())
        except subprocess.SubprocessError:
            pass
            
    elif platform.system() == "Windows":
        info["处理器名称"] = platform.processor()
        info["逻辑核心数"] = os.cpu_count() or "未知"
        
    elif platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                content = f.read()
                for line in content.split("\n"):
                    if line.startswith("model name"):
                        info["处理器名称"] = line.split(":")[1].strip()
                        break
                info["逻辑核心数"] = content.count("processor")
        except FileNotFoundError:
            info["处理器名称"] = platform.processor()
            info["逻辑核心数"] = os.cpu_count() or "未知"
    
    return info


def get_memory_info():
    """获取内存信息"""
    info = {}
    
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, check=True
            )
            mem_bytes = int(result.stdout.strip())
            info["总内存"] = f"{mem_bytes / (1024**3):.2f} GB"
        except subprocess.SubprocessError:
            pass
            
    elif platform.system() == "Windows":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong),
                ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
            ]
        
        memoryStatus = MEMORYSTATUSEX()
        memoryStatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(memoryStatus))
        
        total_mem = memoryStatus.ullTotalPhys
        info["总内存"] = f"{total_mem / (1024**3):.2f} GB"
        info["可用内存"] = f"{memoryStatus.ullAvailPhys / (1024**3):.2f} GB"
        info["使用率"] = f"{memoryStatus.dwMemoryLoad}%"
        
    elif platform.system() == "Linux":
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_kb = int(line.split()[1])
                        info["总内存"] = f"{mem_kb / (1024**2):.2f} GB"
                        break
        except FileNotFoundError:
            pass
    
    return info


def get_disk_info():
    """获取磁盘信息"""
    info = {}
    
    try:
        usage = shutil.disk_usage("/")
        total_gb = usage.total / (1024**3)
        used_gb = usage.used / (1024**3)
        free_gb = usage.free / (1024**3)
        usage_percent = (usage.used / usage.total) * 100
        
        info["总容量"] = f"{total_gb:.2f} GB"
        info["已使用"] = f"{used_gb:.2f} GB ({usage_percent:.1f}%)"
        info["可用空间"] = f"{free_gb:.2f} GB"
    except Exception as e:
        info["错误"] = str(e)
    
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["diskutil", "info", "/"],
                capture_output=True, text=True
            )
            for line in result.stdout.split("\n"):
                if "File System Personality" in line:
                    info["文件系统"] = line.split(":")[1].strip()
                    break
        except subprocess.SubprocessError:
            pass
    
    return info


def get_gpu_info():
    """获取显卡信息"""
    info = {}
    
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True
            )
            for line in result.stdout.split("\n"):
                if "Chipset Model" in line:
                    gpu_name = line.split(":")[1].strip()
                    info["显卡型号"] = gpu_name
                    break
        except subprocess.SubprocessError:
            pass
            
    elif platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                info["显卡型号"] = lines[1].strip()
        except subprocess.SubprocessError:
            pass
            
    elif platform.system() == "Linux":
        try:
            result = subprocess.run(
                ["lspci", "-v"],
                capture_output=True, text=True
            )
            for line in result.stdout.split("\n"):
                if "VGA compatible controller" in line or "3D controller" in line:
                    info["显卡型号"] = line.split(":")[2].strip() if ":" in line else line
                    break
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    return info


def get_python_info():
    """获取 Python 环境信息"""
    info = {
        "Python 版本": platform.python_version(),
        "实现": platform.python_implementation(),
        "编译器": platform.python_compiler(),
        "可执行文件": sys.executable,
    }
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True, text=True
        )
        packages = len(result.stdout.strip().split("\n"))
        info["已安装包数"] = packages
    except subprocess.SubprocessError:
        pass
    
    return info


def get_network_info():
    """获取网络信息"""
    info = {}
    
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["ifconfig", "en0"],
                capture_output=True, text=True
            )
            for line in result.stdout.split("\n"):
                if "inet " in line and "netmask" in line:
                    ip = line.split()[1]
                    info["本地 IP"] = ip
                    break
        except subprocess.SubprocessError:
            pass
            
    elif platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["ipconfig"],
                capture_output=True, text=True
            )
            for line in result.stdout.split("\n"):
                if "IPv4" in line:
                    info["本地 IP"] = line.split(":")[1].strip()
                    break
        except subprocess.SubprocessError:
            pass
    
    info["主机名"] = platform.node()
    
    return info


def print_section(title: str, data: dict, icon: str = "📌"):
    """打印一个信息区块"""
    print(f"\n{icon} {title}")
    print("─" * 50)
    for key, value in data.items():
        print(f"  {key}: {value}")


def main():
    """主函数"""
    print("=" * 50)
    print("🖥️  系统配置分析报告")
    print("=" * 50)
    print(f"生成时间：{platform.node()}")
    
    print_section("操作系统", get_os_info(), "🖥️")
    print_section("处理器 (CPU)", get_cpu_info(), "⚙️")
    print_section("内存 (RAM)", get_memory_info(), "💾")
    print_section("磁盘存储", get_disk_info(), "💿")
    print_section("显卡 (GPU)", get_gpu_info(), "🎮")
    print_section("Python 环境", get_python_info(), "🐍")
    print_section("网络信息", get_network_info(), "🌐")
    
    print("\n" + "=" * 50)
    print("✅ 分析完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
```

### 使用方法

```bash
# 1. 保存为 system_info.py
# 2. 运行脚本
python3 system_info.py
```

### 功能说明

该脚本会分析并展示以下信息：

| 类别 | 内容 |
|------|------|
| 🖥️ 操作系统 | 系统类型、版本、架构 |
| ⚙️ 处理器 | CPU 型号、核心数 |
| 💾 内存 | 总内存容量 |
| 💿 磁盘 | 总容量、已用空间、可用空间 |
| 🎮 显卡 | GPU 型号 |
| 🐍 Python 环境 | Python 版本、安装包数 |
| 🌐 网络 | 本地 IP、主机名 |

支持 **macOS**、**Windows**、**Linux** 三大操作系统。