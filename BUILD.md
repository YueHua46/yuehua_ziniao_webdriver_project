# 构建和发布指南

本文档说明如何构建和发布紫鸟浏览器 Python SDK。

## 📋 前置要求

确保已安装以下工具：

```bash
pip install build twine
```

## 🔨 构建包

### 1. 清理旧的构建文件

```bash
# Windows
rmdir /s /q build dist src\yuehua_ziniao_webdriver.egg-info

# Linux/macOS
rm -rf build/ dist/ src/*.egg-info
```

### 2. 构建分发包

```bash
python -m build
```

这会在 `dist/` 目录下生成两个文件：
- `.tar.gz` - 源码分发包
- `.whl` - wheel 二进制分发包

### 3. 检查构建的包

```bash
twine check dist/*
```

## 🧪 本地测试安装

在发布前，先在本地测试安装：

```bash
# 卸载旧版本（如果已安装）
pip uninstall yuehua-ziniao-webdriver -y

# 从本地 wheel 安装
pip install dist/yuehua_ziniao_webdriver-0.1.0-py3-none-any.whl

# 或从源码安装
pip install -e .
```

测试导入：

```python
import yuehua_ziniao_webdriver
print(yuehua_ziniao_webdriver.__version__)
```

## 📤 发布到 PyPI

### 1. 注册 PyPI 账号

- 访问 https://pypi.org/account/register/
- 创建账号并验证邮箱

### 2. 配置 PyPI 令牌（推荐）

创建 `~/.pypirc` 文件：

```ini
[pypi]
username = __token__
password = pypi-你的令牌
```

### 3. 发布到 TestPyPI（可选，用于测试）

```bash
# 上传到 TestPyPI
twine upload --repository testpypi dist/*

# 从 TestPyPI 安装测试
pip install --index-url https://test.pypi.org/simple/ yuehua-ziniao-webdriver
```

### 4. 发布到正式 PyPI

```bash
twine upload dist/*
```

### 5. 验证发布

访问包页面：https://pypi.org/project/yuehua-ziniao-webdriver/

测试安装：

```bash
pip install yuehua-ziniao-webdriver
```

## 🏷️ 版本管理

### 更新版本号

需要同时更新以下文件中的版本号：

1. `pyproject.toml` - `[project]` 部分的 `version`
2. `src/yuehua_ziniao_webdriver/__init__.py` - `__version__` 变量

### 语义化版本规范

遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)：

- `0.1.0` - 初始开发版本
- `0.1.1` - 修复 bug
- `0.2.0` - 新增功能（向后兼容）
- `1.0.0` - 首个稳定版本
- `2.0.0` - 破坏性更改

### 创建 Git 标签

```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

## 📝 发布检查清单

在发布新版本前，确保完成以下事项：

- [ ] 更新 `CHANGELOG.md`
- [ ] 更新版本号（`pyproject.toml` 和 `__init__.py`）
- [ ] 运行所有测试（如果有）
- [ ] 更新 `README.md`（如有新功能）
- [ ] 清理并重新构建包
- [ ] 检查包的完整性 (`twine check`)
- [ ] 本地测试安装
- [ ] 提交所有更改到 Git
- [ ] 创建 Git 标签
- [ ] 发布到 PyPI
- [ ] 验证可以从 PyPI 安装

## 🔍 常见问题

### 1. 构建失败

确保 `pyproject.toml` 配置正确，特别是 `[build-system]` 部分。

### 2. 上传失败：文件已存在

PyPI 不允许重新上传同一版本。解决方案：
- 修改版本号（推荐）
- 或使用 TestPyPI 进行测试

### 3. 导入失败

确保包结构正确：
- `src/yuehua_ziniao_webdriver/` 目录存在
- `__init__.py` 正确导出了所有公共 API

### 4. 依赖问题

确保 `pyproject.toml` 中的依赖版本正确，并且与目标 Python 版本兼容。

## 🛠️ 开发工具

### 代码格式化

```bash
# 使用 black 格式化代码
black src/

# 使用 ruff 检查代码质量
ruff check src/
```

### 类型检查

```bash
mypy src/yuehua_ziniao_webdriver/
```

### 测试（如果有）

```bash
pytest tests/
```

## 📚 相关资源

- [Python 打包指南](https://packaging.python.org/)
- [setuptools 文档](https://setuptools.pypa.io/)
- [PyPI 官方文档](https://pypi.org/help/)
- [语义化版本](https://semver.org/)
