# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

ECUST（华东理工大学）学生邮箱自动化测试框架，测试目标为 `stu.mail.ecust.edu.cn`（Coremail 邮件系统）。项目包含单步测试、模块测试、集成测试、数据组合测试和性能测试，通过 Selenium + Edge 浏览器驱动自动化执行。

## 环境与依赖

- Python 3.8+，Microsoft Edge 浏览器
- 安装: `pip install selenium webdriver-manager requests pillow`
- 需在校园网或 VPN 环境下运行（目标服务仅内网可达）

## 运行方式

### GUI 模式（推荐入口）

```bash
python single_login.py          # 启动 GUI 图形界面（默认行为）
```

GUI (`gui_main.py`) 提供四个页面：单步测试、集成测试、数据组合测试、性能测试。每个脚本通过按钮一键启动，输出实时显示在界面中。

### 命令行模式

```bash
python single_login.py --run-login   # 层级1：启动浏览器并登录，生成 browser_session.json
python test_engine.py                # 主控：连接已登录浏览器，执行全部测试并生成 HTML 报告
python login.py                      # 数据驱动登录测试（8组账号组合）
python performance.py                # 110并发线程压测（无需浏览器）
```

单个集成测试可直接运行（自包含，自动登录）：
```bash
python draft_integration.py    # IT-02: 草稿箱集成测试
python sent_integration.py     # IT-01: 已发送集成测试
python red_flag.py             # 红旗邮件设置集成测试
python all_steps.py            # 完整流程集成测试
```

## 分层架构

项目采用 5 层架构，各层通过 `browser_session.json` 解耦：

| 层级 | 核心文件 | 核心类 | 职责 |
|------|---------|--------|------|
| 1 | `single_login.py` | — | 启动带 `--remote-debugging-port=9223` 的 Edge，登录并保存 sid |
| 2 | `compose_connect.py` | `BrowserConnector`(单例), `ComposeManager` | 通过 CDP 连接已启动浏览器，提供写信/发送能力 |
| 3 | `folder_nav.py` | `FolderNavigator` | 导航到草稿箱/已发送，邮件计数，空文件夹检测 |
| 4 | `mail_selector.py` | `MailSelector` | 邮件选择（单选/全选），打开邮件详情 |
| 5 | `mail_deleter.py` | `MailDeleter` | 删除操作，未勾选拦截检测 |

**关键设计模式**：
- `BrowserConnector` 是单例，`get_connector()` 工厂函数获取实例
- `base_test.py` 提供基类，封装浏览器连接 (`connect_browser()` 通过 `debuggerAddress` CDP 连接) 和日志记录
- 集成测试文件（`draft_integration.py`, `sent_integration.py` 等）是**自包含**的——各自启动独立浏览器、独立登录，不依赖预先运行的 `single_login.py`

## 测试数据与文件路径

- **会话文件**: `browser_session.json` — 由 `single_login.py` 生成，包含 `debug_port`, `sid`, `current_url`
- **截图目录**: `result/pic/` — 测试过程截图自动保存于此
- **日志目录**: `result/log/` — 日志文件（含 login_test 的 JSON 结果）
- **测试报告**: `result/test_report.html` — `test_engine.py` 生成的完整 HTML 报告
- **附件资源**: `resource/` — 附件测试用的文件（png, txt, zip, html, pptx 为允许格式；js, bat 为禁止格式）

## 账号配置

出于隐私保护，代码中账号密码用 `********` / `******` 占位。以下文件包含登录凭据，修改账号时需同步更新：
`single_login.py`, `login.py`, `all_steps.py`, `draft_integration.py`, `enter_sent_and_search.py`, `red_flag.py`, `sent_integration.py`

## 关键实现细节

### 元素定位策略
- 多 XPath 兜底定位，适配 Coremail 界面变化
- 删除按钮修复：点击 `<span class="nui-btn-text">` 的父级 `<div role="button">` 而非 span 本身（`mail_deleter.py` 第5-8行注释说明）
- `MailSelector.open_first()` 针对已发送页面无 `<a>` 链接的问题，采用多候选元素评分点击策略

### 浏览器管理
- 使用唯一 `user-data-dir`（含时间戳）避免 Edge 实例冲突
- CDP 注入脚本隐藏 `navigator.webdriver` 属性
- 各集成测试使用不同调试端口（9223/9224/9225）避免端口冲突
- `webdriver-manager` 自动管理 EdgeDriver，失败时回退到系统默认 Edge

### 测试结构
- `test_engine.py` 的测试按顺序执行：数据准备 → 草稿箱模块(5用例) → 已发送模块(5用例) → 集成测试(2条路径) → 数据组合(9组) → 性能测试
- 组合测试自动跳过真正执行删除的危险组合
- 性能测试使用 `concurrent.futures.ThreadPoolExecutor`，纯 HTTP 请求，不依赖浏览器
