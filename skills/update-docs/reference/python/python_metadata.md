# Python メタデータファイル読み取りガイド

## 概要

Pythonプロジェクトのメタデータ（スクリプト、依存関係、設定）を読み取る方法を説明します。

---

## メタデータファイル一覧

| ファイル | 用途 | 優先度 |
|----------|------|--------|
| `pyproject.toml` | 現代的なPython設定ファイル（推奨） | 高 |
| `setup.py` | 従来型のセットアップスクリプト | 中 |
| `setup.cfg` | 宣言的なセットアップ設定 | 中 |
| `requirements.txt` | 依存関係リスト | 中 |
| `Pipfile` | Pipenv用の依存関係 | 低 |
| `poetry.lock` | Poetry用のロックファイル | 低 |

---

## pyproject.toml からの情報抽出

### 基本構造

```toml
[project]
name = "my-project"
version = "1.0.0"
description = "プロジェクトの説明"
readme = "README.md"
requires-python = ">=3.9"

[project.scripts]
my-cli = "my_project.cli:main"
my-server = "my_project.server:run"

[project.dependencies]
requests = ">=2.28.0"
pydantic = ">=2.0.0"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
]

[tool.poetry]
name = "my-project"
version = "1.0.0"

[tool.poetry.scripts]
my-cli = "my_project.cli:main"

[tool.poetry.dependencies]
python = "^3.9"
requests = "^2.28.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
```

### スクリプト一覧の取得

```python
import tomllib  # Python 3.11+
# または
import toml  # pip install toml

def get_scripts_from_pyproject(path: str = "pyproject.toml") -> dict:
    """pyproject.tomlからスクリプトを取得"""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    
    scripts = {}
    
    # PEP 621形式 (project.scripts)
    if "project" in data and "scripts" in data["project"]:
        scripts.update(data["project"]["scripts"])
    
    # Poetry形式 (tool.poetry.scripts)
    if "tool" in data and "poetry" in data["tool"]:
        poetry = data["tool"]["poetry"]
        if "scripts" in poetry:
            scripts.update(poetry["scripts"])
    
    return scripts
```

### 依存関係の取得

```python
def get_dependencies_from_pyproject(path: str = "pyproject.toml") -> dict:
    """pyproject.tomlから依存関係を取得"""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    
    deps = {
        "main": [],
        "dev": [],
        "optional": {}
    }
    
    # PEP 621形式
    if "project" in data:
        project = data["project"]
        if "dependencies" in project:
            deps["main"] = project["dependencies"]
        if "optional-dependencies" in project:
            deps["optional"] = project["optional-dependencies"]
            if "dev" in deps["optional"]:
                deps["dev"] = deps["optional"]["dev"]
    
    # Poetry形式
    if "tool" in data and "poetry" in data["tool"]:
        poetry = data["tool"]["poetry"]
        if "dependencies" in poetry:
            deps["main"] = [
                f"{k}{v}" if isinstance(v, str) else k
                for k, v in poetry["dependencies"].items()
                if k != "python"
            ]
        if "group" in poetry and "dev" in poetry["group"]:
            deps["dev"] = list(poetry["group"]["dev"].get("dependencies", {}).keys())
    
    return deps
```

---

## setup.py からの情報抽出

### 基本構造

```python
from setuptools import setup, find_packages

setup(
    name="my-project",
    version="1.0.0",
    description="プロジェクトの説明",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "my-cli=my_project.cli:main",
            "my-server=my_project.server:run",
        ],
    },
)
```

### AST解析による情報抽出

```python
import ast
from typing import Dict, List, Any

def parse_setup_py(path: str = "setup.py") -> Dict[str, Any]:
    """setup.pyをAST解析して情報を抽出"""
    with open(path, "r") as f:
        tree = ast.parse(f.read())
    
    result = {
        "name": None,
        "version": None,
        "scripts": [],
        "dependencies": [],
        "dev_dependencies": []
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if hasattr(node.func, "id") and node.func.id == "setup":
                for keyword in node.keywords:
                    if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                        result["name"] = keyword.value.value
                    elif keyword.arg == "version" and isinstance(keyword.value, ast.Constant):
                        result["version"] = keyword.value.value
                    elif keyword.arg == "install_requires" and isinstance(keyword.value, ast.List):
                        result["dependencies"] = [
                            elt.value for elt in keyword.value.elts 
                            if isinstance(elt, ast.Constant)
                        ]
                    elif keyword.arg == "entry_points" and isinstance(keyword.value, ast.Dict):
                        for k, v in zip(keyword.value.keys, keyword.value.values):
                            if isinstance(k, ast.Constant) and k.value == "console_scripts":
                                if isinstance(v, ast.List):
                                    result["scripts"] = [
                                        elt.value for elt in v.elts 
                                        if isinstance(elt, ast.Constant)
                                    ]
    
    return result
```

---

## requirements.txt からの情報抽出

### 基本構造

```text
# Main dependencies
requests>=2.28.0
pydantic>=2.0.0,<3.0.0

# With extras
uvicorn[standard]>=0.20.0

# Git repositories
git+https://github.com/user/repo.git@v1.0.0

# Local packages
-e ./my_local_package
```

### パース方法

```python
def parse_requirements(path: str = "requirements.txt") -> List[str]:
    """requirements.txtをパース"""
    dependencies = []
    
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            # コメントと空行をスキップ
            if not line or line.startswith("#"):
                continue
            # オプション行をスキップ
            if line.startswith("-"):
                if line.startswith("-e "):
                    dependencies.append(line[3:])  # 編集可能インストール
                continue
            dependencies.append(line)
    
    return dependencies
```

---

## 利用可能なコマンドの自動検出

### Makefileの解析

```python
import re

def parse_makefile(path: str = "Makefile") -> Dict[str, str]:
    """Makefileからターゲットを抽出"""
    targets = {}
    current_target = None
    
    with open(path, "r") as f:
        for line in f:
            # ターゲット定義を検出
            match = re.match(r"^([a-zA-Z_-]+):", line)
            if match:
                current_target = match.group(1)
                # コメントから説明を抽出（前の行）
                targets[current_target] = ""
    
    return targets
```

### tox.iniの解析

```python
import configparser

def parse_tox_ini(path: str = "tox.ini") -> Dict[str, str]:
    """tox.iniから環境を抽出"""
    config = configparser.ConfigParser()
    config.read(path)
    
    environments = {}
    for section in config.sections():
        if section.startswith("testenv"):
            env_name = section.replace("testenv:", "") or "default"
            commands = config.get(section, "commands", fallback="")
            environments[env_name] = commands
    
    return environments
```

---

## ドキュメント生成テンプレート

### 利用可能なスクリプト

```markdown
## 利用可能なスクリプト

| コマンド | 説明 |
|----------|------|
| `poetry run my-cli` | CLI ツールを実行 |
| `poetry run my-server` | サーバーを起動 |
| `python -m my_project` | モジュールとして実行 |

### 開発用コマンド

| コマンド | 説明 |
|----------|------|
| `poetry install` | 依存関係をインストール |
| `poetry install --with dev` | 開発依存関係を含めてインストール |
| `pytest` | テストを実行 |
| `pytest --cov` | カバレッジ付きでテスト |
| `black .` | コードフォーマット |
| `mypy .` | 型チェック |
| `ruff check .` | リント |
```

### 依存関係

```markdown
## 依存関係

### 本番依存関係

| パッケージ | バージョン | 用途 |
|------------|------------|------|
| requests | >=2.28.0 | HTTP クライアント |
| pydantic | >=2.0.0 | データバリデーション |

### 開発依存関係

| パッケージ | バージョン | 用途 |
|------------|------------|------|
| pytest | >=7.0.0 | テストフレームワーク |
| black | >=23.0.0 | コードフォーマッター |
| mypy | >=1.0.0 | 型チェッカー |
```

---

## 統合パース関数

```python
from pathlib import Path
from typing import Dict, Any, Optional
import tomllib
import json

def extract_python_project_metadata(project_root: str = ".") -> Dict[str, Any]:
    """Pythonプロジェクトのメタデータを統合的に抽出"""
    root = Path(project_root)
    metadata = {
        "name": None,
        "version": None,
        "scripts": {},
        "dependencies": {
            "main": [],
            "dev": [],
        },
        "python_version": None,
        "source_files": [],
    }
    
    # pyproject.toml（優先）
    pyproject_path = root / "pyproject.toml"
    if pyproject_path.exists():
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        
        # PEP 621
        if "project" in data:
            project = data["project"]
            metadata["name"] = project.get("name")
            metadata["version"] = project.get("version")
            metadata["python_version"] = project.get("requires-python")
            metadata["scripts"] = project.get("scripts", {})
            metadata["dependencies"]["main"] = project.get("dependencies", [])
            if "optional-dependencies" in project:
                metadata["dependencies"]["dev"] = project["optional-dependencies"].get("dev", [])
        
        # Poetry
        if "tool" in data and "poetry" in data["tool"]:
            poetry = data["tool"]["poetry"]
            metadata["name"] = metadata["name"] or poetry.get("name")
            metadata["version"] = metadata["version"] or poetry.get("version")
            if "scripts" in poetry:
                metadata["scripts"].update(poetry["scripts"])
    
    # requirements.txt（フォールバック）
    req_path = root / "requirements.txt"
    if req_path.exists() and not metadata["dependencies"]["main"]:
        metadata["dependencies"]["main"] = parse_requirements(str(req_path))
    
    # requirements-dev.txt
    req_dev_path = root / "requirements-dev.txt"
    if req_dev_path.exists():
        metadata["dependencies"]["dev"] = parse_requirements(str(req_dev_path))
    
    return metadata
```
