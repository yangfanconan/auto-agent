import shutil
import subprocess
import platform
我已尝试创建脚本但未获得执行权限。让我为你提供完整的代码，你可以手动运行：

```python
#!/usr/bin/env python3
"""系统配置信息获取脚本 - system_info.py"""


def get_system_info():
    print("=" * 60)
    print("🖥️  系统配置信息")
    print("=" * 60)

    # 操作系统
    print("\n📌 操作系统")
    print("-" * 40)
    print(f"  系统：{platform.system()}")
    print(f"  版本：{platform.version()}")
    print(f"  机器：{platform.machine()}")
    print(f"  架构：{platform.architecture()[0]}")

    if platform.system() == "Darwin":
        result = subprocess.run(["sw_vers"], capture_output=True, text=True)
        print(f"  {result.stdout.strip()}")

    # CPU
    print("\n📌 CPU")
    print("-" * 40)
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
        print(f"  型号：{result.stdout.strip()}")
        result = subprocess.run(
            ["sysctl", "-n", "hw.ncpu"], capture_output=True, text=True)
        print(f"  核心数：{result.stdout.strip()}")

    # 内存
    print("\n📌 内存")
    print("-" * 40)
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
        mem_gb = int(result.stdout.strip()) / (1024**3)
        print(f"  总内存：{mem_gb:.1f} GB")

    # 磁盘
    print("\n📌 磁盘")
    print("-" * 40)
    total, used, free = shutil.disk_usage("/")
    print(f"  总容量：{total / (1024**3):.1f} GB")
    print(f"  已用：{used / (1024**3):.1f} GB")
    print(f"  可用：{free / (1024**3):.1f} GB")
    print(f"  使用率：{(used / total) * 100:.1f}%")

    # GPU
    print("\n📌 GPU")
    print("-" * 40)
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"], capture_output=True, text=True)
        for line in result.stdout.split("\n"):
            if "Chipset Model" in line or "Total Number of Cores" in line or "VRAM" in line:
                print(f"  {line.strip()}")

    # Python
    print("\n📌 Python 环境")
    print("-" * 40)
    print(f"  版本：{platform.python_version()}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    get_system_info()
```

**运行方法：**
```bash
python3 system_info.py
```

这个脚本会显示：
- 🖥️ 操作系统信息（系统、版本、架构）
- 💻 CPU 型号和核心数
- 🧠 内存大小
- 💾 磁盘容量和使用情况
- 🎮 GPU 显卡信息
- 🐍 Python 环境版本
