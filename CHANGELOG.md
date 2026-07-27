# 更新日志

所有重要的项目更改都将记录在此文件中。

本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)规范。

## [0.1.17] - 2026-07-27

### 新增

- 新增 `AmazonSellerCentral` 公共门面，提供登录、MFA、站点切换、语言切换、主页导航和已知弹窗处理。
- 新增 `prepare()` 组合入口，以及登录、站点和语言的专用异常类型。
- 站点参数同时支持 `US`、`UK` 等代码与简体中文、繁体中文和英文名称。

### 调整

- 登录、站点和语言操作使用各自的页面完成条件，不再依赖全局 loading 动画判断。
- 登录专属遮挡在登录流程内处理，主页弹窗由公共门面按需处理。
- 保留 `handle_login()`、`switch_site()` 和 `switch_language_to_cn()` 函数式兼容入口。

## [0.1.16] - 2026-07-15

### 新增

- 新增紫鸟 HTTP JSON API 就绪检测：启动后用幂等的认证 `getBrowserList` 轮询，只有收到合法 JSON 和成功状态码才允许业务请求继续。
- `ZiniaoConfig` 新增 `startup_timeout`、`startup_poll_interval`、`startup_attempts` 和 `startup_restart_delay`，支持配置启动等待及内部恢复策略。

### 修复

- 修复 V6 启动耗时不稳定时，固定等待 5 秒就发送首次业务请求，导致连接拒绝、空响应或 JSON 解析失败的问题。
- HTTP API 首次未就绪时会在 SDK 内部清理、冷却并重新启动一次，避免把可恢复的启动时序异常交给业务层重跑。
- Windows 进程不存在或清理时恰好退出产生的 `taskkill` 128/255 返回码降为调试日志，不再误报启动警告。

## [0.1.15] - 2026-07-15

### 修复

- 修复会话初始化阶段尚未打开 IP 检测页和平台主页时，就要求必须存在 HTTP(S) 网页标签，导致店铺启动流程无法继续的死锁问题。
- 初始化时只验证浏览器级 CDP 连接；平台启动页打开后才重建连接并验证普通网页标签。
- `BrowserSession.reconnect()` 新增 `require_web_page` 参数，支持区分启动前后的连接验证阶段。

## [0.1.14] - 2026-07-15

### 修复

- 修复 `BrowserSession.reconnect()` 使用 `latest_tab` 时可能选中紫鸟插件的 offscreen/background 标签，从而把插件页面断开误判为整个浏览器 CDP 不可用的问题。
- 重连健康检查改为通过 `get_tabs()` 查找可访问的 HTTP(S) 普通网页，并逐个忽略无法读取 URL 的插件标签。

## [0.1.13] - 2026-07-15

### 新增

- `BrowserSession.reconnect()` 支持丢弃失效的 DrissionPage 对象，并重试到 CDP 页面 WebSocket 通道稳定。

### 修复

- 修复新版紫鸟返回调试端口后页面 CDP 通道短暂不稳定，导致 IP 检测阶段留下断开连接、后续继续使用失效 `Chromium` 对象的问题。
- `open_store()` 返回会话前会自动重建并验证浏览器连接；可通过 `cdpReconnectTimeout` 和 `cdpReconnectInterval` 调整重试参数。

## [0.1.12] - 2026-06-15

### 新增

- `StoreOpenOptions` 支持 `notPromptForDownload`、`forceDownloadPath`、`windowRatio` 和 `preSetting`，可控制 V6 下载弹窗、下载目录和浏览器预设。

## [0.1.11] - 2026-06-15

### 新增

- Windows V5 支持从常见默认安装位置自动探测 `starter.exe`，默认安装时可不传 `client_path`。

### 变更

- `ZiniaoConfig.from_env()` 不再强制要求 `ZINIAO_CLIENT_PATH`，允许 V5/V6 走默认路径自动探测。
- README 和类型说明同步标记 `client_path` 为可选。

## [0.1.10] - 2026-06-15

### 修复

- 修复部分 Windows/Python 环境下 `ProgramFiles` 指向 `C:\Program Files (x86)`，导致 V6 自动探测漏搜 `C:\Program Files\ziniao\ziniao.exe` 的问题。

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
