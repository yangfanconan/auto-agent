# Auto-Agent Setup

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="auto-agent",
    version="1.0.0",
    author="Auto-Agent Team",
    description="全自动工程化编程智能体",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.13",
    install_requires=[
        "PyYAML>=6.0",
        "pytest>=7.4.0",
    ],
    extras_require={
        "git": ["GitPython>=3.1.40"],
        "test": ["pytest-cov>=4.1.0"],
    },
    entry_points={
        "console_scripts": [
            "auto-agent=main:main",
        ],
    },
)
