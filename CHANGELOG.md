# 更新日志

所有重要的项目更改都将记录在此文件中。

本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)规范。

## [0.1.9] - 2026-06-15

### 新增

- `ZiniaoConfig` 支持 V6 客户端路径自动探测，Windows 下可从默认安装位置查找 `ziniao.exe`。
- 打开店铺启动页后自动持续清理多余插件 Tab，支持延迟弹出的插件页场景。
- `StoreOpenOptions` 新增多余 Tab 清理开关和轮询/稳定期参数。

### 变更

- Windows V6 进程清理覆盖 `ziniao.exe`、`ziniaobrowser.exe` 和店铺内核进程，减少残留进程影响。

## [0.1.8] - 2026-05-19

### 新增

- `ZiniaoConfig` 新增 `host`、`listen_ip`、`cdp_host`、`cdp_proxy_host` 和 `extra_args`，支持远程 WebDriver HTTP 与 CDP 连接/暴露配置。
- Linux 打开店铺示例 `examples/linux_open_store.py`，支持通过环境变量配置监听地址和 CDP 地址。

### 变更

- `HttpClient` 支持自定义 WebDriver HTTP 服务主机，不再固定为 `127.0.0.1`。
- `BrowserSession` 和 `get_browser()` 支持通过 `host:port` 连接远程 CDP 调试端口，同时保持本机端口连接兼容。
- 启动紫鸟客户端时会透传 `--listen_ip` 和额外启动参数。
- `BrowserSession` 可选启动 TCP 代理，将本机 CDP 调试端口暴露到指定网卡地址。

### 修复

- HTTP 响应解析显式使用 UTF-8，减少中文错误信息乱码风险。

## [0.1.0] - 2026-02-03

### ✨ 新增

- 🎉 首次发布
- ✅ 核心客户端类 `ZiniaoClient`
- ✅ 配置管理类 `ZiniaoConfig`，支持多种配置方式
- ✅ 浏览器会话管理 `BrowserSession`
- ✅ 完整的类型提示系统
- ✅ 清晰的异常体系
- ✅ HTTP 通信封装，内置重试机制
- ✅ 进程管理功能
- ✅ 店铺管理功能

### 🚀 核心功能

- **按名称搜索店铺**
  - 支持模糊匹配和精确匹配
  - 智能搜索算法，不区分大小写
  
- **并发打开多个店铺**
  - 使用线程池实现
  - 可配置最大并发数
  - 自动容错处理
  
- **灵活的配置方式**
  - 代码配置
  - 字典配置
  - JSON 文件配置
  - 环境变量配置
  
- **完善的错误处理**
  - 10+ 种自定义异常类
  - 详细的错误信息
  - 便于调试和定位问题
  
- **日志系统集成**
  - 基于 Python logging
  - 支持自定义日志级别
  - 可输出到文件

### 📦 依赖

- Python >= 3.8
- DrissionPage >= 4.0.0
- requests >= 2.28.0
- typing-extensions >= 4.5.0 (Python < 3.10)

### 📚 文档

- 完整的 README.md
- 详细的 API 文档
- 7 个使用示例
- 构建和发布指南

### 🔧 工具

- 平台检测工具（Windows/macOS/Linux）
- 缓存管理工具
- 路径处理工具
- 字符串匹配工具

---

## [未来计划]

### 即将推出的功能

- [ ] 异步支持（async/await）
- [ ] 命令行工具（CLI）
- [ ] 单元测试套件
- [ ] 更多使用示例
- [ ] 性能优化
- [ ] 插件系统
- [ ] WebHook 支持

### 正在考虑的功能

- [ ] 配置文件 YAML 格式支持
- [ ] 店铺分组管理
- [ ] 定时任务调度
- [ ] 浏览器指纹管理
- [ ] 代理池管理
- [ ] 数据持久化

---

## 版本格式说明

- `[版本号]` - 发布日期
- **Added** (新增) - 新功能
- **Changed** (变更) - 现有功能的变更
- **Deprecated** (弃用) - 即将移除的功能
- **Removed** (移除) - 已移除的功能
- **Fixed** (修复) - bug 修复
- **Security** (安全) - 安全相关的修复
