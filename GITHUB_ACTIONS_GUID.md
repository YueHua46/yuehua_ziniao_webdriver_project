动发布指南

本指南说明如何配置 GitHub Actions 自动将包发布到 PyPI。

## 📋 前置条件

1. ✅ 项目已推送到 GitHub
2. ✅ 已有 PyPI 账号
3. ⬜ 需要配置 PyPI API Token

## 🔑 第一步：获取 PyPI API Token

### 1. 登录 PyPI

访问 https://pypi.org/ 并登录你的账号

### 2. 创建 API Token

1. 点击右上角用户名 → **Account settings**
2. 滚动到 **API tokens** 区域
3. 点击 **Add API token**
4. 填写信息：
   - **Token name**: `github-actions-yuehua-ziniao-webdriver`
   - **Scope**: 选择 **Project: yuehua-ziniao-webdriver** (首次发布选择 "Entire account"，发布后可创建项目专用 token)
5. 点击 **Create token**
6. **重要**：立即复制生成的 token（以 `pypi-` 开头），关闭后无法再查看！

## 🔐 第二步：配置 GitHub Secrets

### 1. 进入 GitHub 仓库

访问你的 GitHub 仓库页面

### 2. 添加 Secret

1. 点击 **Settings** 标签
2. 左侧菜单点击 **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. 添加 Secret：
   - **Name**: `PYPI_API_TOKEN`
   - **Secret**: 粘贴刚才复制的 PyPI token
5. 点击 **Add secret**

## 🚀 第三步：发布新版本

### 方式 1：通过 Git 标签自动发布（推荐）

```bash
# 1. 更新版本号（修改这两个文件）
# - pyproject.toml 中的 version
# - src/yuehua_ziniao_webdriver/__init__.py 中的 __version__

# 2. 提交更改
git add .
git commit -m "Bump version to 0.1.1"

# 3. 创建并推送标签
git tag v0.1.1
git push origin main
git push origin v0.1.1

# GitHub Actions 会自动触发并发布到 PyPI
```

### 方式 2：手动触发

1. 进入 GitHub 仓库
2. 点击 **Actions** 标签
3. 左侧选择 **"发布到 PyPI"** 工作流
4. 点击右侧 **Run workflow** → **Run workflow**

## 📝 版本发布流程

### 完整的版本发布检查清单

- [ ] 更新 `CHANGELOG.md`
- [ ] 更新版本号：
  - [ ] `pyproject.toml` 中的 `version = "0.1.x"`
  - [ ] `src/yuehua_ziniao_webdriver/__init__.py` 中的 `__version__ = "0.1.x"`
- [ ] 提交所有更改：`git commit -am "Release v0.1.x"`
- [ ] 推送到 GitHub：`git push origin main`
- [ ] 创建版本标签：`git tag v0.1.x`
- [ ] 推送标签：`git push origin v0.1.x`
- [ ] 等待 GitHub Actions 完成（约 2-5 分钟）
- [ ] 验证发布：访问 https://pypi.org/project/yuehua-ziniao-webdriver/
- [ ] 测试安装：`pip install yuehua-ziniao-webdriver==0.1.x`

## 📊 查看工作流状态

### 查看运行状态

1. 进入 GitHub 仓库
2. 点击 **Actions** 标签
3. 查看最近的工作流运行记录
4. 点击具体的运行查看详细日志

### 工作流徽章（可选）

在 `README.md` 顶部添加状态徽章：

```markdown
[![PyPI version](https://badge.fury.io/py/yuehua-ziniao-webdriver.svg)](https://badge.fury.io/py/yuehua-ziniao-webdriver)
[![Publish to PyPI](https://github.com/你的用户名/yuehua-ziniao-webdriver/actions/workflows/publish.yml/badge.svg)](https://github.com/你的用户名/yuehua-ziniao-webdriver/actions/workflows/publish.yml)
```

## 🔍 工作流文件说明

### `.github/workflows/publish.yml` - 发布工作流

```yaml
触发条件：
  - 推送版本标签（如 v0.1.0）
  - 手动触发

步骤：
  1. 检出代码
  2. 设置 Python 3.10
  3. 安装构建工具（build, twine）
  4. 构建分发包
  5. 检查包的完整性
  6. 发布到 PyPI
```

### `.github/workflows/test.yml` - 测试工作流

```yaml
触发条件：
  - 推送到 main/develop 分支
  - 创建 Pull Request 到 main

测试矩阵：
  - OS: Ubuntu, Windows, macOS
  - Python: 3.8, 3.9, 3.10, 3.11, 3.12

步骤：
  1. 检出代码
  2. 设置对应的 Python 版本
  3. 安装包
  4. 测试导入
  5. 代码质量检查（ruff, black）
```

## ⚠️ 常见问题

### 1. 发布失败：文件已存在

**原因**：PyPI 不允许重新上传相同版本的包

**解决方案**：
```bash
# 增加版本号
# 修改 pyproject.toml 和 __init__.py 中的版本号
# 例如从 0.1.0 改为 0.1.1

git add .
git commit -m "Bump version to 0.1.1"
git push origin main
git tag v0.1.1
git push origin v0.1.1
```

### 2. 发布失败：认证错误

**原因**：PyPI token 无效或未正确配置

**解决方案**：
1. 检查 GitHub Secrets 中的 `PYPI_API_TOKEN` 是否正确
2. 确认 token 未过期
3. 重新生成 token 并更新 Secret

### 3. 工作流未触发

**原因**：标签格式不匹配

**解决方案**：
```bash
# 确保标签格式为 v0.1.0（以 v 开头）
git tag v0.1.0  # ✅ 正确
git tag 0.1.0   # ❌ 不会触发工作流
```

### 4. 首次发布到 PyPI

**首次发布特别说明**：

1. 首次发布需要使用 **Entire account** 范围的 token
2. 发布成功后，可以创建 **项目专用** token 并更新 GitHub Secret
3. 如果包名已被占用，需要修改 `pyproject.toml` 中的 `name` 字段

## 🛡️ 安全最佳实践

1. ✅ **永远不要**在代码中硬编码 API token
2. ✅ **使用** GitHub Secrets 存储敏感信息
3. ✅ **定期更换** PyPI token
4. ✅ **使用项目专用** token 而不是账号级别的 token
5. ✅ **启用 2FA**（双因素认证）保护 PyPI 和 GitHub 账号

## 📚 参考资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [PyPI API Token 指南](https://pypi.org/help/#apitoken)
- [Python 包发布指南](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [Trusted Publishers（可选，更安全）](https://docs.pypi.org/trusted-publishers/)

## 🎯 Trusted Publishers（推荐升级方案）

PyPI 支持 **Trusted Publishers** 功能，可以不使用 token 直接从 GitHub Actions 发布，更安全：

### 配置步骤

1. 登录 PyPI
2. 进入项目设置
3. 点击 **Publishing** → **Add a new publisher**
4. 填写信息：
   - **Repository owner**: 你的 GitHub 用户名
   - **Repository name**: `yuehua-ziniao-webdriver`
   - **Workflow name**: `publish.yml`
   - **Environment name**: 留空或填写 `release`

使用 Trusted Publishers 后，`publish.yml` 可以简化为：

```yaml
- name: 发布到 PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
```

不需要配置 `PYPI_API_TOKEN` Secret！

---

**配置完成后，每次推送版本标签都会自动发布到 PyPI！** 🎉
