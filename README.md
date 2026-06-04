# ECUST 邮箱自动化测试系统

华东理工大学（ECUST）学生邮箱自动化测试框架，采用分层架构设计，支持登录、写信、文件夹导航、邮件选择、删除操作及完整的测试报告生成。

---

## 项目结构
甘甜(g) 陶若愚(t) 詹子杰(z)

| 文件 | 层级 | 职责 |
|------|------|------|
| `single_login.py` | 层级1 | 启动调试模式 Edge 浏览器，执行登录并保存会话信息 |

| `compose_connect.py` | 层级2 | 连接已启动的浏览器，提供写信/邮件撰写功能 | (t)
| `compose_connect_test.py` | 层级2 | 连接已启动的浏览器，进入写信页面 | (z)
| `enter_sent_box.py` | 层级2 | 进入已发送页面| (g)

| `folder_nav.py` | 层级3 | 文件夹导航（草稿箱/已发送），统计邮件数量，检测空文件夹 | (t)
| `enter_sent_and_search.py` | 层级3 | 搜索发送给23070066的信件点击进入 | (g)
| `recipient_test.py` | 层级3 | 填写收件人 | (z)
| `theme_test.py` | 层级3 | 填写主题 | (z)
| `text_test.py` | 层级3 | 填写正文 | (z)
| `attachment_test.py` | 层级3 | 添加附件测试(成功:png、txt、zip、html、pptx;失败:js、bat) | (z)


| `mail_selector.py` | 层级4 | 邮件选择/锁定，支持单选、全选、打开邮件详情 | (t)
| `resend_mail.py` | 层级4 | 进入再次编辑页面 | (g)
| `button_test.py` | 层级4 | 发送按钮测试，发送失败(即未填写收件人)会返回写信页面，没有主题时会自动确认“确认没有主题，依然发送”。测试层里它是第4层，但可以在和第3层同样的powershell里运行该文件 | (z)

| `mail_deleter.py` | 层级5 | 邮件删除操作，支持未勾选拦截检测和删除验证 | (t)
| `cancel_return.py` | 层级5 | 实现点击”返回“回到信件页面 | (g)
| `return_write.py` | 层级5 | 发送成功时点击“继续写信”，返回写信页面 | (z)

| `test_data.py` | 数据层 | 测试数据准备，自动创建草稿箱/已发送的测试数据 | (t)
| `test_engine.py` | 主控层 | 测试引擎主控程序，执行全部测试并生成 HTML 报告 | (t)
| `base_test.py` | 基层 | 基类模块，提供浏览器管理、日志记录和公共助手方法 | (z)

| `all_steps.py` | 集成测试 | 实现登录、进入已发送、寻找23070066信笺进入再次编辑，编辑成功，实现发送点击（实现返回键） | (g)
| `red_flag.py` | 集成测试 | 实现登录、进入收件箱、寻找23070066发给我的邮件，进入设置为红旗文件 | (g)
| `login.py` | 集成测试 | 实现八组数据测试(两组密码账号正确，一组无验证码，一组有验证码；六祖密码/账号错误) | (g)
| `compose_connect_all_test.py` | 集成测试 | 实现进入写信页面，填写收件人、主题、正文、添加附件，发送，成功发送后返回写信页面的测试 | (z)
---

## 环境要求

- Python 3.8+
- Microsoft Edge 浏览器
- Selenium 4.x
- webdriver-manager
- requests

### 安装依赖

```bash
pip install selenium webdriver-manager requests
```

---

## 快速开始

### 第一步：启动浏览器并登录

运行层级1模块，启动带调试端口的 Edge 浏览器，自动登录邮箱并保存会话：

```bash
python single_login.py
```

登录成功后，浏览器保持运行，生成 `browser_session.json` 会话文件。

### 第二步：执行全部测试

在另一个终端窗口运行主控程序：

```bash
python test_engine.py
```

主控程序会自动：
1. 读取会话信息，连接已登录的浏览器
2. 准备测试数据（草稿箱≥3封，已发送≥2封）
3. 执行草稿箱模块测试（5个用例）
4. 执行已发送模块测试（5个用例）
5. 执行集成测试（2条路径）
6. 执行数据组合测试（9组）
7. 执行性能测试（110并发线程压测）
8. 生成 HTML 测试报告

---

## 测试模块详解

### 1. 草稿箱模块（5用例）

| 用例ID | 类型 | 描述 |
|--------|------|------|
| TC-DRAFT-P01 | 正向 | 进入草稿箱验证页面加载 |
| TC-DRAFT-P02 | 正向 | 查看草稿数量与主题 |
| TC-DRAFT-P03 | 正向 | 打开第一封草稿 |
| TC-DRAFT-N01 | 负向 | 草稿箱为空时执行删除 |
| TC-DRAFT-N02 | 负向 | 未勾选直接点击删除 |

### 2. 已发送模块（5用例）

| 用例ID | 类型 | 描述 |
|--------|------|------|
| TC-SENT-P01 | 正向 | 进入已发送验证页面加载 |
| TC-SENT-P02 | 正向 | 查看已发送数量与主题 |
| TC-SENT-P03 | 正向 | 打开第一封邮件查看详情 |
| TC-SENT-N01 | 负向 | 已发送为空时执行删除 |
| TC-SENT-N02 | 负向 | 未勾选直接点击删除 |

### 3. 集成测试（2用例）

| 用例ID | 深度 | 路径描述 |
|--------|------|----------|
| IT-01 | 3 | 登录→已发送→查看邮件详情 |
| IT-02 | 4 | 登录→草稿箱→打开草稿→返回列表→验证数量 |

### 4. 数据组合测试（9组）

覆盖文件夹（草稿箱/已发送）× 选择方式（不选/单选/全选）× 操作（查看/删除）的组合场景，自动跳过实际执行删除的危险组合。

### 5. 性能测试

使用 110 个并发线程对邮箱服务进行压测，统计成功率、TPS、平均响应时间及 P90/P95/P99 分位延迟。

---

## 核心特性

### 分层架构
- 各层级职责单一，通过 `browser_session.json` 解耦
- 层级1独立运行，层级2-5共享浏览器实例
- 支持浏览器复用，避免重复登录

### 智能元素定位
- 多 XPath 策略兜底，适配 Coremail 邮箱界面变化
- JavaScript 注入点击，绕过复杂事件监听
- 自动识别工具栏、邮件行、复选框等关键元素

### 鲁棒性设计
- 删除操作多重防护：未勾选拦截、空文件夹保护
- 写信页面自动检测并返回主界面
- 异常捕获与截图保存，便于问题定位

### 测试报告
- 自动生成 `test_report.html`，包含：
  - 测试统计（总计/通过/失败/通过率）
  - 用例详情表格（ID、模块、类型、步骤、结果）
  - 性能测试指标（TPS、延迟分位数）
- 截图自动保存至 `screenshots/` 目录

---

## 配置说明

### 登录配置（single_login.py）

```python
USERNAME = "23013181"          # 学号
PASSWORD = "Cqszrr2020"        # 密码
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

1. **先运行层级1**：执行 `test_engine.py` 前必须确保 `single_login.py` 已运行且浏览器未关闭
2. **账号安全**：密码明文存储在代码中，仅供本地测试使用
3. **浏览器独占**：调试端口同一时间只能被一个程序连接
4. **网络环境**：需在校园网或 VPN 环境下访问 `stu.mail.ecust.edu.cn`
5. **数据安全**：测试数据准备模块会发送邮件给自己，请确保邮箱容量充足

---

## 文件说明

### single_login.py
启动带 `--remote-debugging-port=9223` 的 Edge 浏览器，自动填充账号密码登录，保存 `sid` 和调试端口到 `browser_session.json`。

### compose_connect.py
提供 `BrowserConnector` 单例类连接已启动的浏览器，以及 `ComposeManager` 写信管理器，支持保存草稿和发送邮件。

### folder_nav.py
`FolderNavigator` 类负责导航到草稿箱/已发送，提供邮件计数、空文件夹检测、主题读取等功能。使用 JS 精确统计可见邮件行。

### mail_selector.py
`MailSelector` 类实现邮件选择（单选/全选）和打开邮件详情。针对已发送页面无 `<a>` 链接的问题，采用多候选元素评分点击策略。

### mail_deleter.py
`MailDeleter` 类实现邮件删除，核心修复：点击 `<span class="nui-btn-text">` 的父级 `<div role="button">` 而非 span 本身。支持删除验证和未勾选拦截测试。

### test_data.py
`TestDataPreparer` 类在测试前自动检查并创建测试数据：草稿箱不足时自动保存草稿，已发送不足时自动发送邮件给自己。

### test_engine.py
主控程序，集成所有模块，执行完整测试流程并生成 HTML 报告。支持模块级测试和全量测试。

---

## 技术栈

- **自动化测试**：Selenium WebDriver (Edge)
- **并发压测**：Python concurrent.futures ThreadPoolExecutor
- **报告生成**：原生 HTML + CSS
- **浏览器调试**：Chrome DevTools Protocol (CDP)

---

## 作者

华东理工大学 · 软件质量保证与测试综合实验

---

## 更新日志

### 当前版本
- 修复 `open_first()` 在已发送页面的兼容性问题
- 修复删除按钮点击策略（点击父级 div[role="button"]）
- 增加草稿预览模式兼容（verify_send_button）
- 优化邮件计数 JS 算法，提高准确性
