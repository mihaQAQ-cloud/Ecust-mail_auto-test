# ECUST 邮箱自动化测试系统

华东理工大学（ECUST）学生邮箱自动化测试框架，采用分层架构设计，覆盖登录验证、邮件撰写、文件夹导航、邮件选择、删除操作、性能压测等全链路测试场景，支持 GUI 图形界面一键运行。

目标站点：`stu.mail.ecust.edu.cn`（Coremail 邮件系统）

---

## 环境要求

- Python 3.8+
- Microsoft Edge 浏览器
- Selenium 4.x
- webdriver-manager
- requests
- Pillow（GUI 截图预览，可选）

### 安装依赖

```bash
pip install selenium webdriver-manager requests pillow
```

---

## 快速开始

### 方式一：GUI 图形界面（推荐）

一条命令启动图形界面，所有测试均可通过按钮一键运行，无需手动操作命令行：

```bash
python single_login.py
```

> `single_login.py` 在不带参数时默认启动 GUI 界面（`gui_main.py`）。GUI 提供四个测试页面：
> - **单步测试** — 按层级顺序依次启动各模块
> - **集成测试** — 运行端到端集成流程
> - **数据组合测试** — 多组测试数据覆盖各类场景
> - **性能测试** — 110 并发线程压测

### 方式二：命令行模式

适合脚本化或调试场景：

```bash
# 第一步：启动浏览器并登录（生成 browser_session.json）
python single_login.py --run-login

# 第二步：执行全部测试（依赖第一步的浏览器会话）
python test_engine.py
```

集成测试文件是**自包含**的，可独立运行（自带浏览器启动和登录，无需预先执行其他步骤）：

```bash
python draft_integration.py   # 草稿箱集成测试
python sent_integration.py    # 已发送集成测试
python login.py               # 数据驱动登录测试（8组账号组合）
python performance.py         # 并发性能压测（纯 HTTP，无需浏览器）
```

---

## 项目架构

### 分层测试模块

| 层级 | 文件 | 核心类 | 职责 |
|------|------|--------|------|
| 层级1 | `single_login.py` | — | 启动带调试端口的 Edge 浏览器，执行登录并保存会话信息 |
| 层级2 | `compose_connect.py` | `BrowserConnector`, `ComposeManager` | 连接已登录浏览器，提供写信/邮件撰写功能 |
| 层级2 | `compose_connect_test.py` | — | 连接已启动的浏览器，进入写信页面 |
| 层级2 | `enter_sent_box.py` | — | 进入已发送页面 |
| 层级3 | `folder_nav.py` | `FolderNavigator` | 文件夹导航（草稿箱/已发送），统计邮件数量，检测空文件夹 |
| 层级3 | `enter_sent_and_search.py` | — | 搜索发送给指定用户的信件并点击进入 |
| 层级3 | `recipient_test.py` | — | 填写收件人 |
| 层级3 | `theme_test.py` | — | 填写主题 |
| 层级3 | `text_test.py` | — | 填写正文 |
| 层级3 | `attachment_test.py` | — | 添加附件测试（允许：png/txt/zip/html/pptx；禁止：js/bat） |
| 层级4 | `mail_selector.py` | `MailSelector` | 邮件选择/锁定，支持单选、全选、打开邮件详情 |
| 层级4 | `resend_mail.py` | — | 进入再次编辑页面 |
| 层级4 | `button_test.py` | — | 发送按钮测试（无收件人时返回写信页，无主题时自动确认发送） |
| 层级5 | `mail_deleter.py` | `MailDeleter` | 邮件删除操作，支持未勾选拦截检测和删除验证 |
| 层级5 | `cancel_return.py` | — | 点击「返回」按钮回到信件页面 |
| 层级5 | `return_write.py` | — | 发送成功后点击「继续写信」，返回写信页面 |

### 基础设施

| 文件 | 分类 | 职责 |
|------|------|------|
| `base_test.py` | 基类 | 提供浏览器管理（CDP 连接）、日志记录和公共助手方法 |
| `test_data.py` | 数据层 | 测试数据准备，自动创建草稿箱/已发送的测试数据 |
| `test_engine.py` | 主控层 | 测试引擎主控程序，执行全部测试并生成 HTML 报告 |
| `gui_main.py` | 界面层 | Tkinter 图形界面，统一管理所有测试的启动与输出展示 |

### 集成测试（自包含）

| 文件 | 深度 | 描述 |
|------|------|------|
| `draft_integration.py` | 4 | IT-02：自动登录 → 进入草稿箱 → 打开草稿 → 返回列表 → 验证数量一致 |
| `sent_integration.py` | 3 | IT-01：自动登录 → 进入已发送 → 打开第一封邮件查看详情 |
| `red_flag.py` | 4 | 自动登录 → 进入收件箱 → 精确查找指定邮件 → 设置为红旗文件 |
| `all_steps.py` | 5 | 自动登录 → 进入已发送 → 查找指定信件 → 进入再次编辑 → 发送 → 返回 |
| `compose_connect_all_test.py` | 5 | 进入写信页 → 填写收件人/主题/正文/附件 → 发送 → 返回写信页 |
| `login.py` | 2 | 8 组数据驱动登录测试（2组有效 + 6组无效账号/密码组合） |

### 进阶测试

| 文件 | 分类 | 描述 |
|------|------|------|
| `draft_module.py` | 模块测试 | 草稿箱模块（5 用例）：页面加载、数量统计、打开草稿、空箱删除、未勾选删除 |
| `sent_module.py` | 模块测试 | 已发送模块（5 用例）：页面加载、数量统计、打开邮件、空箱删除、未勾选删除 |
| `draft_and_sent_combination.py` | 数据组合 | 9 组组合测试：文件夹 × 选择方式 × 操作 |
| `performance.py` | 性能测试 | 110 并发线程压测，统计成功率、TPS、延迟分位数（纯 HTTP，无需浏览器） |

---

## 测试模块详解

### 1. 草稿箱模块（5 用例）

| 用例 ID | 类型 | 描述 |
|---------|------|------|
| TC-DRAFT-P01 | 正向 | 进入草稿箱验证页面加载 |
| TC-DRAFT-P02 | 正向 | 查看草稿数量与主题 |
| TC-DRAFT-P03 | 正向 | 打开第一封草稿 |
| TC-DRAFT-N01 | 负向 | 草稿箱为空时执行删除 |
| TC-DRAFT-N02 | 负向 | 未勾选直接点击删除 |

### 2. 已发送模块（5 用例）

| 用例 ID | 类型 | 描述 |
|---------|------|------|
| TC-SENT-P01 | 正向 | 进入已发送验证页面加载 |
| TC-SENT-P02 | 正向 | 查看已发送数量与主题 |
| TC-SENT-P03 | 正向 | 打开第一封邮件查看详情 |
| TC-SENT-N01 | 负向 | 已发送为空时执行删除 |
| TC-SENT-N02 | 负向 | 未勾选直接点击删除 |

### 3. 集成测试

| 用例 ID | 深度 | 路径描述 |
|---------|------|----------|
| IT-01 | 3 | 登录 → 已发送 → 查看邮件详情 |
| IT-02 | 4 | 登录 → 草稿箱 → 打开草稿 → 返回列表 → 验证数量 |

### 4. 数据组合测试（9 组）

覆盖文件夹（草稿箱/已发送）× 选择方式（不选/单选/全选）× 操作（查看/删除）的组合场景，自动跳过实际执行删除的危险组合。

### 5. 性能测试

使用 110 个并发线程对邮件服务器进行压测，统计成功率、TPS、平均响应时间及 P50/P90/P95/P99 分位延迟。

---

## 核心特性

### 分层架构
- 各层级职责单一，通过 `browser_session.json` 解耦
- 层级 1 独立运行，层级 2-5 通过 CDP（Chrome DevTools Protocol）共享浏览器实例
- 集成测试文件自包含，各自启动独立浏览器，无需预先执行其他步骤

### 智能元素定位
- 多 XPath 策略兜底，适配 Coremail 邮箱界面变化
- JavaScript 注入点击，绕过复杂事件监听
- 自动识别工具栏、邮件行、复选框等关键元素

### 鲁棒性设计
- 删除操作多重防护：未勾选拦截、空文件夹保护
- 写信页面自动检测并返回主界面
- 异常捕获与截图保存，便于问题定位

### 测试报告
- 命令行模式自动生成 `result/test_report.html`，包含：
  - 测试统计（总计/通过/失败/通过率）
  - 用例详情表格（ID、模块、类型、步骤、结果）
  - 性能测试指标（TPS、延迟分位数）
- 截图自动保存至 `result/pic/` 目录

---

## 配置说明

### 登录配置

出于隐私保护，代码中账号密码以占位符表示。以下文件中的凭据需自行修改：

`single_login.py`、`login.py`、`all_steps.py`、`draft_integration.py`、`enter_sent_and_search.py`、`red_flag.py`、`sent_integration.py`

```python
USERNAME = "2301****"          # 学号
PASSWORD = "*******"           # 密码
DEBUG_PORT = 9223              # 浏览器调试端口
SESSION_FILE = "browser_session.json"  # 会话文件
```

### 测试配置（test_engine.py）

```python
PERF_THREADS = 110             # 性能测试并发线程数
SCREENSHOT_DIR = "screenshots" # 截图保存目录
REPORT_FILE = "test_report.html" # 报告文件名
```

---

## 注意事项

1. **GUI 模式推荐优先使用**：`python single_login.py`（不带参数）直接启动图形界面，无需手动管理浏览器进程
2. **命令行模式先运行层级 1**：执行 `test_engine.py` 前必须确保 `single_login.py --run-login` 已运行且浏览器未关闭
3. **集成测试独立运行**：`draft_integration.py`、`sent_integration.py` 等自包含测试可直接运行，无需预先启动浏览器
4. **调试端口隔离**：各集成测试使用不同调试端口（9223/9224/9225），同时运行应避免端口冲突
5. **网络环境**：需在校园网或 VPN 环境下访问 `stu.mail.ecust.edu.cn`
6. **数据安全**：测试数据准备模块会发送邮件给自己（`test_data.py`），请确保邮箱容量充足

---

## 技术栈

- **自动化测试**：Selenium WebDriver (Edge) + Chrome DevTools Protocol (CDP)
- **并发压测**：Python `concurrent.futures.ThreadPoolExecutor`
- **GUI 界面**：Tkinter
- **报告生成**：原生 HTML + CSS
- **驱动管理**：webdriver-manager（自动安装匹配的 EdgeDriver）

---

## 作者

华东理工大学 · 软件质量保证与测试综合实验

---

## 更新日志

### 当前版本
- 新增 Tkinter GUI 图形界面（`gui_main.py`），统一管理所有测试模块
- 新增自包含集成测试（`draft_integration.py`、`sent_integration.py`），无需依赖共享浏览器会话
- 新增数据驱动登录测试（`login.py`），覆盖 8 组账号组合
- 修复 `open_first()` 在已发送页面的兼容性问题
- 修复删除按钮点击策略（点击父级 `div[role="button"]` 而非 `span` 子元素）
- 增加草稿预览模式兼容（`verify_send_button`）
- 优化邮件计数 JS 算法，提高准确性
