"""
网易邮箱自动化：登录 -> 进入已发送 -> 搜索詹子杰邮件 -> 再次编辑 -> 修改发送
合并版完整流程
"""

import time
import json
import os
import re
import tempfile
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# ==================== 配置区域 ====================
URL = "https://stu.mail.ecust.edu.cn/"
USERNAME = "23013181"
PASSWORD = "Cqszrr2020"

# 目标收件人（詹子杰）
TARGET_RECIPIENT = "23070066"

# 调试端口
DEBUG_PORT = 9223
SESSION_FILE = "browser_session.json"

# 结果目录
RESULT_DIR = "result"
PIC_DIR = os.path.join(RESULT_DIR, "pic")
LOG_DIR = os.path.join(RESULT_DIR, "log")

# 日志前缀
PREFIX = {"INFO": "[*]", "PASS": "[+]", "FAIL": "[-]", "ERROR": "[!]", "WARN": "[?]"}


# ==================== 工具函数 ====================
def ensure_dirs():
    """确保结果目录存在"""
    os.makedirs(PIC_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def log_print(message, level="INFO"):
    """打印日志，同时写入日志文件"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    p = PREFIX.get(level, "[*]")
    log_line = f"[{timestamp}] {p} {message}"
    print(log_line)
    ensure_dirs()
    log_file = os.path.join(LOG_DIR, f"auto_mail_{time.strftime('%Y%m%d')}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def save_screenshot(driver, name):
    """保存截图"""
    ensure_dirs()
    path = os.path.join(PIC_DIR, f"{name}_{time.strftime('%Y%m%d_%H%M%S')}.png")
    driver.save_screenshot(path)
    log_print(f"截图已保存: {path}")
    return path


def safe_click(driver, elem, desc=""):
    """安全点击元素，尝试多种点击方式"""
    log_print(f"尝试点击: {desc}")
    # 方式1：滚动到元素并点击
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
        time.sleep(0.5)
        elem.click()
        log_print("方式1(直接点击)成功")
        return True
    except Exception as e1:
        log_print(f"方式1失败: {str(e1)[:80]}")
    # 方式2：ActionChains点击
    try:
        ActionChains(driver).move_to_element(elem).click().perform()
        log_print("方式2(ActionChains)成功")
        return True
    except Exception as e2:
        log_print(f"方式2失败: {str(e2)[:80]}")
    # 方式3：JavaScript点击
    try:
        driver.execute_script("arguments[0].click();", elem)
        log_print("方式3(JavaScript点击)成功")
        return True
    except Exception as e3:
        log_print(f"方式3失败: {str(e3)[:80]}")
    # 方式4：双击
    try:
        ActionChains(driver).move_to_element(elem).double_click().perform()
        log_print("方式4(双击)成功")
        return True
    except Exception as e4:
        log_print(f"方式4失败: {str(e4)[:80]}")
    return False


def get_clickable_parent(driver, elem, max_levels=5):
    """向上查找可点击的父元素"""
    current = elem
    for i in range(max_levels):
        try:
            parent = current.find_element(By.XPATH, "..")
            tag = parent.tag_name.lower()
            onclick = parent.get_attribute("onclick")
            class_attr = parent.get_attribute("class") or ""
            log_print(f"第{i+1}层父元素: <{tag}> class='{class_attr[:60]}' onclick={'有' if onclick else '无'}")
            if tag in ["tr", "div", "li"]:
                if onclick or any(kw in class_attr.lower() for kw in ["item", "row", "list", "mail", "msg"]):
                    log_print(f"找到可点击父元素(第{i+1}层): <{tag}> class='{class_attr[:40]}'")
                    return parent
                if i >= 1:
                    log_print(f"使用父元素(第{i+1}层)尝试: <{tag}>")
                    return parent
            current = parent
        except Exception as e:
            log_print(f"查找父元素失败(第{i+1}层): {e}")
            break
    return None


# ==================== 第一层：登录 ====================
def create_debug_driver():
    """创建带调试端口的Edge浏览器"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument(f"--remote-debugging-port={DEBUG_PORT}")
    user_data_dir = os.path.join(tempfile.gettempdir(), f"edge_profile_{int(time.time())}")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    try:
        service = Service(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
    except Exception as e:
        log_print(f"自动驱动失败: {e}", "WARN")
        driver = webdriver.Edge(options=options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def layer1_login(driver):
    """执行登录"""
    log_print("=" * 60)
    log_print("【第一层】启动调试浏览器并登录")
    log_print("=" * 60)

    driver.get(URL)
    log_print("已打开登录页")
    time.sleep(4)

    # 输入用户名
    try:
        username_input = driver.find_element(By.XPATH, "//input[@placeholder='请输入登录账号']")
    except:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        username_input = [inp for inp in inputs if inp.get_attribute("type") == "text"][0]

    username_input.clear()
    username_input.send_keys(USERNAME)
    log_print(f"已输入账号: {USERNAME}")
    time.sleep(1)

    # 输入密码
    password_input = driver.find_element(By.XPATH, "//input[@type='password']")
    password_input.clear()
    password_input.send_keys(PASSWORD)
    log_print("已输入密码")
    time.sleep(1)

    # 回车登录
    password_input.send_keys(Keys.ENTER)
    log_print("已提交登录")
    time.sleep(6)

    # 检查登录结果
    current_url = driver.current_url
    if "main.jsp" in current_url:
        log_print(f"登录成功: {current_url[:80]}...", "PASS")

        sid_match = re.search(r'sid=([^&]+)', current_url)
        sid = sid_match.group(1) if sid_match else ""

        session = {
            "debug_port": DEBUG_PORT,
            "sid": sid,
            "current_url": current_url,
            "login_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

        log_print(f"会话已保存到: {SESSION_FILE}", "PASS")
        log_print(f"sid: {sid}")
        return sid
    else:
        log_print(f"登录失败: {current_url}", "FAIL")
        return None


# ==================== 第二层：进入已发送 ====================
def layer2_enter_sent_box(driver, sid):
    """进入已发送页面"""
    log_print("\n" + "=" * 60)
    log_print("【第二层】进入已发送页面")
    log_print("=" * 60)

    if not sid:
        log_print("缺少sid，尝试从当前URL提取", "WARN")
        current_url = driver.current_url
        sid_match = re.search(r'sid=([^&]+)', current_url)
        if sid_match:
            sid = sid_match.group(1)
            log_print(f"从当前URL提取sid: {sid[:20]}...")
        else:
            log_print("无法获取sid，进入已发送页面失败", "ERROR")
            return False

    log_print("正在尝试进入已发送页面...")

    # 方法1：尝试点击左侧导航栏的"已发送"
    sent_selectors = [
        "//span[contains(text(),'已发送')]",
        "//a[contains(text(),'已发送')]",
        "//div[contains(text(),'已发送')]",
        "//li[contains(text(),'已发送')]",
        "//span[@class='nui-tree-item-text' and contains(text(),'已发送')]",
        "//div[contains(@class,'sent')]",
        "//div[contains(@title,'已发送')]",
        "//*[contains(@class,'folder') and contains(text(),'已发送')]",
    ]

    clicked = False
    for xpath in sent_selectors:
        try:
            elem = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            elem.click()
            log_print(f"点击'已发送'成功: {xpath}", "PASS")
            clicked = True
            time.sleep(3)
            break
        except:
            continue

    # 方法2：URL跳转
    if not clicked:
        log_print("点击方式失败，尝试URL跳转...", "WARN")
        url_patterns = [
            f"https://stu.mail.ecust.edu.cn/js6/main.jsp?sid={sid}&show_new=1&hl=zh_CN#module=mbox.ListModule%7C%7B%7B%22fid%22%3A3%7D%7D",
            f"https://stu.mail.ecust.edu.cn/js6/main.jsp?sid={sid}#module=mbox.ListModule%7C%7B%7B%22fid%22%3A3%7D%7D",
            f"https://stu.mail.ecust.edu.cn/js6/main.jsp?sid={sid}&module=mbox.ListModule&fid=3",
        ]
        for url in url_patterns:
            try:
                driver.get(url)
                log_print(f"尝试URL: {url[:80]}...")
                time.sleep(4)
                if is_sent_box_page(driver):
                    log_print("URL跳转成功", "PASS")
                    clicked = True
                    break
            except Exception as e:
                log_print(f"URL尝试失败: {e}")
                continue

    if is_sent_box_page(driver):
        log_print("成功进入已发送页面", "PASS")
        save_screenshot(driver, "sent_box")
        return True
    else:
        log_print("进入已发送页面失败", "FAIL")
        log_print(f"当前URL: {driver.current_url}")
        return False


def is_sent_box_page(driver):
    """检查是否在已发送页面"""
    current_url = driver.current_url
    if "fid=3" in current_url or "sent" in current_url.lower():
        return True
    indicators = [
        "//span[contains(text(),'已发送')]",
        "//div[contains(text(),'已发送')]",
        "//a[contains(text(),'已发送')]",
        "//li[contains(text(),'已发送')]",
        "//span[@class='nui-tree-item-text' and contains(text(),'已发送')]",
        "//div[contains(@class,'sent')]",
        "//div[contains(@title,'已发送')]",
        "//*[contains(@class,'folder') and contains(text(),'已发送')]",
        "//div[contains(@class,'nui-tree-item') and contains(text(),'已发送')]",
    ]
    for xpath in indicators:
        try:
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return True
        except:
            continue
    return False


# ==================== 第三层：搜索并点击邮件 ====================
def layer3_search_and_click(driver, recipient=TARGET_RECIPIENT):
    """搜索并点击指定收件人的邮件"""
    log_print("\n" + "=" * 60)
    log_print(f"【第三层】搜索收件人为 '{recipient}' 的邮件")
    log_print("=" * 60)

    time.sleep(2)

    # 定位收件人文本
    text_locators = [
        f"//span[contains(text(),'{recipient}')]",
        f"//div[contains(text(),'{recipient}')]",
        f"//a[contains(text(),'{recipient}')]",
        f"//td[contains(text(),'{recipient}')]",
        f"//span[contains(@title,'{recipient}')]",
        f"//div[contains(@title,'{recipient}')]",
    ]

    target_elem = None
    for xpath in text_locators:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                visible = [e for e in elements if e.is_displayed()]
                target_elem = visible[0] if visible else elements[0]
                log_print(f"找到收件人元素: {xpath} (共{len(elements)}个，可见{len(visible) if visible else '?' }个)")
                break
        except:
            continue

    if not target_elem:
        log_print(f"未找到包含 '{recipient}' 的元素", "FAIL")
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if recipient in body_text:
                log_print("页面文本中包含目标收件人，但XPath定位失败", "WARN")
            else:
                log_print("页面文本中也不包含目标收件人", "FAIL")
        except:
            pass
        save_screenshot(driver, "debug_no_element")
        return False

    # 查找可点击行
    clickable_row = get_clickable_parent(driver, target_elem, max_levels=6)

    if not clickable_row:
        log_print("尝试查找兄弟元素（主题链接）...")
        try:
            parent = target_elem.find_element(By.XPATH, "..")
            links = parent.find_elements(By.XPATH, ".//a | .//div[@onclick] | .//span[@onclick]")
            if links:
                for link in links:
                    if link.is_displayed():
                        clickable_row = link
                        log_print(f"找到兄弟链接元素: <{link.tag_name}>")
                        break
        except Exception as e:
            log_print(f"查找兄弟元素失败: {e}")

    if not clickable_row:
        try:
            grandparent = target_elem.find_element(By.XPATH, "../..")
            tag = grandparent.tag_name.lower()
            if tag in ["tr", "div", "li"]:
                clickable_row = grandparent
                log_print(f"使用祖父元素作为行: <{tag}>")
        except:
            pass

    if not clickable_row:
        clickable_row = target_elem
        log_print("使用收件人元素本身尝试点击")

    clicked = safe_click(driver, clickable_row, f"收件人{recipient}所在行")

    if clicked:
        time.sleep(3)
        current_url = driver.current_url
        log_print(f"点击后当前URL: {current_url[:100]}...")

        is_read_page = any(kw in current_url.lower() for kw in ["read", "view", "detail", "mid", "compose"])
        page_title = driver.title
        if is_read_page or "读信" in page_title or "邮件" in page_title:
            log_print("成功打开邮件", "PASS")
        else:
            log_print("点击完成，等待页面加载...")
            time.sleep(2)

        save_screenshot(driver, "mail_opened")
        return True
    else:
        log_print("所有点击方式均失败", "FAIL")
        save_screenshot(driver, "debug_click_fail")
        return False


# ==================== 第四层：点击再次编辑发送 ====================
def layer4_click_resend(driver):
    """点击'再次编辑发送'按钮"""
    log_print("\n" + "=" * 60)
    log_print("【第四层】点击'再次编辑发送'")
    log_print("=" * 60)

    time.sleep(2)

    resend_selectors = [
        "//button[contains(text(),'再次编辑发送')]",
        "//a[contains(text(),'再次编辑发送')]",
        "//span[contains(text(),'再次编辑发送')]",
        "//div[contains(text(),'再次编辑发送')]",
        "//button[contains(text(),'再次编辑')]",
        "//a[contains(text(),'再次编辑')]",
        "//span[contains(text(),'再次编辑')]",
        "//div[contains(text(),'再次编辑')]",
        "//*[contains(@title,'再次编辑发送')]",
        "//*[contains(@title,'再次编辑')]",
        "//button[contains(@class,'resend')]",
        "//a[contains(@class,'resend')]",
        "//span[contains(@class,'resend')]",
        "//div[contains(@class,'btn')]//button",
        "//div[contains(@class,'action')]//a",
        "//div[contains(@class,'toolbar')]//button",
        "//div[contains(@class,'toolbar')]//a",
    ]

    clicked = False
    for xpath in resend_selectors:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                visible = [e for e in elements if e.is_displayed()]
                target = visible[0] if visible else elements[0]

                elem_text = target.text or target.get_attribute("textContent") or ""
                elem_title = target.get_attribute("title") or ""
                log_print(f"找到元素: {xpath} | 文本: '{elem_text[:30]}' title: '{elem_title[:30]}'")

                if "再次编辑" in elem_text or "再次编辑" in elem_title or "resend" in xpath:
                    if safe_click(driver, target, f"再次编辑发送按钮 ({xpath})"):
                        clicked = True
                        time.sleep(3)
                        break
                else:
                    if safe_click(driver, target, f"可能的再次编辑按钮 ({xpath})"):
                        time.sleep(3)
                        current_url = driver.current_url
                        if "compose" in current_url.lower() or "写信" in driver.title:
                            log_print("成功进入编辑页面", "PASS")
                            clicked = True
                            break
        except Exception as e:
            continue

    if clicked:
        time.sleep(2)
        current_url = driver.current_url
        page_title = driver.title
        log_print(f"当前URL: {current_url[:100]}...")
        log_print(f"当前标题: {page_title}")

        is_edit_page = any(kw in current_url.lower() for kw in ["compose", "edit", "resend"])
        is_edit_title = any(kw in page_title for kw in ["写信", "编辑", "Compose"])

        if is_edit_page or is_edit_title:
            log_print("确认进入编辑/写信页面", "PASS")
        else:
            log_print("可能未进入编辑页面，请检查", "WARN")

        save_screenshot(driver, "resend_edit")
        return True
    else:
        log_print("未找到或无法点击'再次编辑发送'按钮", "FAIL")
        save_screenshot(driver, "debug_layer4")
        return False


# ==================== 第五层：编辑并发送 ====================
def layer5_edit_and_send(driver):
    """
    【第五层】编辑邮件内容并发送
    修复：使用 JavaScript 直接操作 iframe 内 body，确保内容写入
    """
    log_print("\n" + "=" * 60)
    log_print("【第五层】编辑邮件内容并发送")
    log_print("=" * 60)

    time.sleep(3)

    # ========== 修改主题 ==========
    try:
        subject_selectors = [
            "//input[contains(@id,'subject')]",
            "//input[contains(@class,'subject')]",
            "//input[@placeholder='请输入邮件主题']",
            "//div[contains(@class,'subject')]//input",
            "//input[contains(@data-type,'subject')]",
            "//div[contains(text(),'主题')]/following-sibling::input",
            "//div[contains(@class,'nui-ipt')]//input",
        ]

        subject_elem = None
        for xpath in subject_selectors:
            try:
                elems = driver.find_elements(By.XPATH, xpath)
                for elem in elems:
                    if elem.is_displayed() and elem.size["width"] > 100:
                        subject_elem = elem
                        log_print(f"找到主题输入框: {xpath}")
                        break
                if subject_elem:
                    break
            except:
                continue

        if subject_elem:
            original_subject = subject_elem.get_attribute("value") or ""
            log_print(f"原主题: '{original_subject}'")
            new_subject = f"【再次发送】{original_subject}" if original_subject else "【再次发送】"

            # 使用 JavaScript 设置值更可靠
            driver.execute_script("arguments[0].value = arguments[1];", subject_elem, new_subject)
            # 触发 input 事件确保页面感知到变化
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", subject_elem)
            log_print(f"已修改主题为: '{new_subject}'", "PASS")
        else:
            log_print("未找到主题输入框", "WARN")
    except Exception as e:
        log_print(f"修改主题时出错: {e}", "ERROR")

    # ========== 修改正文内容（使用 JavaScript 直接操作）==========
    iframe_switched = False

    try:
        # Step 1: 查找 iframe
        iframe_selectors = [
            "//iframe[contains(@id,'editor')]",
            "//iframe[contains(@class,'editor')]",
            "//iframe[contains(@class,'mail')]",
            "//div[contains(@class,'editor')]//iframe",
            "//div[contains(@id,'editor')]//iframe",
        ]

        iframe_elem = None
        for xpath in iframe_selectors:
            try:
                iframes = driver.find_elements(By.XPATH, xpath)
                for iframe in iframes:
                    if iframe.is_displayed() and iframe.size["height"] > 100:
                        iframe_elem = iframe
                        log_print(f"找到编辑器 iframe: {xpath} (高度:{iframe.size['height']})")
                        break
                if iframe_elem:
                    break
            except:
                continue

        if iframe_elem:
            # Step 2: 切换到 iframe
            driver.switch_to.frame(iframe_elem)
            iframe_switched = True
            log_print("已切换到 iframe 内部", "PASS")

            # Step 3: 查找 body
            try:
                body_elem = driver.find_element(By.XPATH, "//body")
                log_print(f"找到 iframe 内 body 元素")

                # 获取原内容
                original_html = body_elem.get_attribute("innerHTML") or ""
                original_text = body_elem.text or ""
                log_print(f"原正文 HTML: '{original_html[:100]}'")
                log_print(f"原正文文本: '{original_text[:100]}' (长度:{len(original_text)})")

                # Step 4: 使用 JavaScript 直接修改 innerHTML（最可靠）
                additional_html = "<br><br><b>【此邮件为自动重新发送，内容已更新】</b><br>发送时间：{}".format(
                    time.strftime("%Y-%m-%d %H:%M:%S")
                )
                new_html = original_html + additional_html

                driver.execute_script("arguments[0].innerHTML = arguments[1];", body_elem, new_html)
                log_print(f"已使用 JavaScript 修改正文 innerHTML", "PASS")

                # 触发 input 事件
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", body_elem)

                # 验证
                time.sleep(1)
                verify_html = body_elem.get_attribute("innerHTML") or ""
                verify_text = body_elem.text or ""
                log_print(f"修改后正文 HTML: '{verify_html[:150]}'")
                log_print(f"修改后正文文本: '{verify_text[:150]}' (长度:{len(verify_text)})")

                if "自动重新发送" in verify_text:
                    log_print("正文追加验证通过", "PASS")
                else:
                    log_print("正文追加验证失败", "WARN")

            except Exception as e:
                log_print(f"iframe 内操作失败: {e}", "ERROR")
        else:
            log_print("未找到 iframe，尝试直接查找 contenteditable div...", "WARN")
            # 兜底：非 iframe 编辑器
            div_selectors = [
                "//div[@contenteditable='true']",
                "//div[contains(@class,'nui-editable')]",
                "//div[contains(@class,'editor')]",
            ]
            for xpath in div_selectors:
                try:
                    elems = driver.find_elements(By.XPATH, xpath)
                    for elem in elems:
                        if elem.is_displayed() and elem.size["height"] > 50:
                            body_elem = elem
                            log_print(f"找到 div 编辑器: {xpath}")

                            original_html = body_elem.get_attribute("innerHTML") or ""
                            additional_html = "<br><br><b>【此邮件为自动重新发送，内容已更新】</b><br>发送时间：{}".format(
                                time.strftime("%Y-%m-%d %H:%M:%S")
                            )
                            new_html = original_html + additional_html
                            driver.execute_script("arguments[0].innerHTML = arguments[1];", body_elem, new_html)
                            log_print("已使用 JavaScript 修改 div 编辑器内容", "PASS")
                            break
                    if body_elem:
                        break
                except:
                    continue

    except Exception as e:
        log_print(f"修改正文时出错: {e}", "ERROR")
        import traceback
        log_print(traceback.format_exc(), "ERROR")
    finally:
        # 必须切回主文档
        if iframe_switched:
            try:
                driver.switch_to.default_content()
                log_print("已切回主文档")
            except Exception as e:
                log_print(f"切回主文档失败: {e}", "ERROR")

    # ========== 处理可能的弹窗（保存密码提示等）==========
    log_print("\n检查并关闭可能的弹窗...")
    try:
        # 尝试关闭浏览器密码保存弹窗
        dismiss_selectors = [
            "//button[contains(text(),'以后再说')]",
            "//button[contains(text(),'取消')]",
            "//span[contains(text(),'以后再说')]",
            "//span[contains(text(),'×')]",
            "//div[contains(@class,'password')]//button[contains(text(),'不')]",
            "//div[contains(@class,'dialog')]//button[contains(text(),'取消')]",
            "//div[contains(@class,'modal')]//button[contains(text(),'关闭')]",
        ]
        for xpath in dismiss_selectors:
            try:
                elems = driver.find_elements(By.XPATH, xpath)
                for elem in elems:
                    if elem.is_displayed():
                        elem.click()
                        log_print(f"关闭弹窗: {xpath}")
                        time.sleep(1)
                        break
            except:
                continue
    except Exception as e:
        log_print(f"处理弹窗时出错(可忽略): {e}")

    # ========== 处理可能的弹窗（保存密码提示等）==========
    log_print("\n检查并关闭可能的弹窗...")
    try:
        dismiss_selectors = [
            "//button[contains(text(),'以后再说')]",
            "//button[contains(text(),'取消')]",
            "//span[contains(text(),'以后再说')]",
            "//span[contains(text(),'×')]",
            "//div[contains(@class,'password')]//button[contains(text(),'不')]",
            "//div[contains(@class,'dialog')]//button[contains(text(),'取消')]",
            "//div[contains(@class,'modal')]//button[contains(text(),'关闭')]",
        ]
        for xpath in dismiss_selectors:
            try:
                elems = driver.find_elements(By.XPATH, xpath)
                for elem in elems:
                    if elem.is_displayed():
                        elem.click()
                        log_print(f"关闭弹窗: {xpath}")
                        time.sleep(1)
                        break
            except:
                continue
    except Exception as e:
        log_print(f"处理弹窗时出错(可忽略): {e}")

    # ========== 点击发送按钮（参考 cancel_return.py 策略）==========
    log_print("\n[*] 开始查找并点击'发送'按钮...")
    time.sleep(2)

    # 先截图看当前状态
    save_screenshot(driver, "before_send")

    # 策略1：优先在 toolbar/header/btn-group 区域查找，排除大容器
    send_selectors = [
        # toolbar 区域
        "//div[contains(@class,'toolbar')]//button[contains(text(),'发送')]",
        "//div[contains(@class,'toolbar')]//a[contains(text(),'发送')]",
        "//div[contains(@class,'toolbar')]//span[contains(text(),'发送')]",
        "//div[contains(@class,'toolbar')]//div[contains(text(),'发送')]",
        # header 区域
        "//div[contains(@class,'header')]//button[contains(text(),'发送')]",
        "//div[contains(@class,'header')]//a[contains(text(),'发送')]",
        "//div[contains(@class,'header')]//span[contains(text(),'发送')]",
        "//div[contains(@class,'header')]//div[contains(text(),'发送')]",
        # btn-group 区域
        "//div[contains(@class,'btn-group')]//button[contains(text(),'发送')]",
        "//div[contains(@class,'btn-group')]//a[contains(text(),'发送')]",
        "//div[contains(@class,'btn-group')]//span[contains(text(),'发送')]",
        "//div[contains(@class,'btn-group')]//div[contains(text(),'发送')]",
        # action 区域
        "//div[contains(@class,'action')]//button[contains(text(),'发送')]",
        "//div[contains(@class,'action')]//a[contains(text(),'发送')]",
        "//div[contains(@class,'action')]//span[contains(text(),'发送')]",
        "//div[contains(@class,'action')]//div[contains(text(),'发送')]",
        # 带 send class 的按钮
        "//button[contains(@class,'send')]",
        "//a[contains(@class,'send')]",
        "//span[contains(@class,'send')]",
        "//div[contains(@class,'send')]",
    ]

    all_candidates = []

    for xpath in send_selectors:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for elem in elements:
                if elem.is_displayed():
                    elem_text = elem.text or ""
                    text_content = elem.get_attribute("textContent") or ""
                    elem_class = elem.get_attribute("class") or ""
                    elem_tag = elem.tag_name

                    # 获取元素尺寸
                    try:
                        size = elem.size
                        width = size['width']
                        height = size['height']
                    except:
                        width = 9999
                        height = 9999

                    # 排除大容器（参考 cancel_return.py）
                    if width > 500 or height > 500:
                        continue
                    if any(kw in elem_class.lower() for kw in ['frame', 'main', 'outer', 'container', 'wrapper']):
                        if width > 200 or height > 200:
                            continue

                    # 获取坐标
                    try:
                        y_pos = elem.location['y']
                        x_pos = elem.location['x']
                    except:
                        y_pos = 999999
                        x_pos = 999999

                    # 检查是否包含"发送"
                    combined_text = (elem_text + text_content).replace(" ", "").replace("\n", "")
                    if "发送" not in combined_text and "send" not in elem_class.lower():
                        continue

                    all_candidates.append({
                        'elem': elem,
                        'xpath': xpath,
                        'tag': elem_tag,
                        'text': elem_text[:30],
                        'class': elem_class[:40],
                        'x': x_pos,
                        'y': y_pos,
                        'width': width,
                        'height': height,
                        'combined': combined_text[:40]
                    })
        except:
            pass

    # 策略2：toolbar 区域没找到，全局查找但严格过滤
    if not all_candidates:
        log_print("[*] toolbar区域未找到，尝试全局查找...", "WARN")

        global_selectors = [
            "//button[contains(text(),'发送')]",
            "//a[contains(text(),'发送')]",
            "//span[contains(text(),'发送')]",
            "//div[contains(text(),'发送')]",
            "//*[contains(@title,'发送')]",
            "//button[contains(@data-action,'send')]",
            "//a[contains(@data-action,'send')]",
        ]

        for xpath in global_selectors:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for elem in elements:
                    if elem.is_displayed():
                        elem_text = elem.text or ""
                        text_content = elem.get_attribute("textContent") or ""
                        elem_class = elem.get_attribute("class") or ""
                        elem_tag = elem.tag_name

                        try:
                            size = elem.size
                            width = size['width']
                            height = size['height']
                        except:
                            width = 9999
                            height = 9999

                        # 严格排除大容器
                        if width > 300 or height > 100:
                            continue
                        if any(kw in elem_class.lower() for kw in ['frame', 'main', 'outer', 'container', 'wrapper', 'body', 'html']):
                            continue

                        try:
                            y_pos = elem.location['y']
                            x_pos = elem.location['x']
                        except:
                            y_pos = 999999
                            x_pos = 999999

                        combined_text = (elem_text + text_content).replace(" ", "").replace("\n", "")
                        if "发送" in combined_text:
                            all_candidates.append({
                                'elem': elem,
                                'xpath': xpath,
                                'tag': elem_tag,
                                'text': elem_text[:30],
                                'class': elem_class[:40],
                                'x': x_pos,
                                'y': y_pos,
                                'width': width,
                                'height': height,
                                'combined': combined_text[:40]
                            })
            except:
                pass

    if not all_candidates:
        log_print("[-] 未找到任何'发送'按钮", "FAIL")
        save_screenshot(driver, "debug_no_send")
        return False

    # 按 y 坐标排序，选择最顶部的（参考 cancel_return.py）
    all_candidates.sort(key=lambda x: x['y'])

    log_print(f"找到 {len(all_candidates)} 个候选，显示前3个:")
    for i, c in enumerate(all_candidates[:3]):
        log_print(f"  候选{i+1}: <{c['tag']}> x={c['x']} y={c['y']} w={c['width']} h={c['height']} 文本='{c['text']}' class='{c['class']}'")

    target = all_candidates[0]['elem']
    best = all_candidates[0]

    # 点击最顶部的候选
    clicked = safe_click(driver, target, f"发送按钮 (x={best['x']}, y={best['y']}, w={best['width']}, h={best['height']}, 文本='{best['text']}')")

    if clicked:
        time.sleep(3)

        # 检查是否出现确认弹窗（如"确定发送？"）
        try:
            confirm_selectors = [
                "//button[contains(text(),'确定')]",
                "//button[contains(text(),'确认')]",
                "//a[contains(text(),'确定')]",
                "//div[contains(@class,'dialog')]//button[contains(text(),'确定')]",
            ]
            for xpath in confirm_selectors:
                try:
                    elems = driver.find_elements(By.XPATH, xpath)
                    for elem in elems:
                        if elem.is_displayed():
                            log_print("发现确认弹窗，点击确定...")
                            elem.click()
                            time.sleep(2)
                            break
                except:
                    continue
        except:
            pass

        # 记录点击后的页面状态
        current_url = driver.current_url
        page_title = driver.title
        log_print(f"点击后URL: {current_url[:100]}...")
        log_print(f"点击后标题: {page_title}")

        save_screenshot(driver, "mail_sent")
        return True
    else:
        log_print("[-] 所有点击方式均失败", "FAIL")
        save_screenshot(driver, "debug_send_fail")
        return False
    if send_clicked:
        time.sleep(3)
        current_url = driver.current_url
        page_title = driver.title
        log_print(f"发送后URL: {current_url[:100]}...")
        log_print(f"发送后标题: {page_title}")

        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "发送成功" in body_text or "已发送" in body_text:
                log_print("邮件发送成功！", "PASS")
            else:
                log_print("已点击发送，请确认是否成功", "INFO")
        except:
            log_print("已执行发送操作", "INFO")

        save_screenshot(driver, "mail_sent")
        return True
    else:
        log_print("未找到或无法点击发送按钮", "FAIL")
        save_screenshot(driver, "debug_send_fail")
        return False

# ==================== 主程序 ====================
def main():
    """主程序：完整五层流程"""
    driver = None

    try:
        print("=" * 60)
        print("网易邮箱自动化 - 完整五层流程")
        print("=" * 60)
        print("流程: 登录 -> 已发送 -> 搜索邮件 -> 再次编辑 -> 修改发送")
        print("=" * 60)

        # ========== 第一层：登录 ==========
        driver = create_debug_driver()
        sid = layer1_login(driver)

        if not sid:
            log_print("登录失败，流程终止", "FAIL")
            return

        # ========== 第二层：进入已发送 ==========
        if not layer2_enter_sent_box(driver, sid):
            log_print("进入已发送页面失败，流程终止", "FAIL")
            return

        # ========== 第三层：搜索并点击邮件 ==========
        if not layer3_search_and_click(driver, TARGET_RECIPIENT):
            log_print("搜索邮件失败，流程终止", "FAIL")
            return

        # ========== 第四层：点击再次编辑发送 ==========
        if not layer4_click_resend(driver):
            log_print("点击再次编辑发送失败，流程终止", "FAIL")
            return

        # ========== 第五层：编辑并发送 ==========
        if not layer5_edit_and_send(driver):
            log_print("编辑发送失败", "FAIL")
            return

        # ========== 完成 ==========
        log_print("\n" + "=" * 60)
        log_print("【流程完成】所有步骤执行完毕", "PASS")
        log_print("=" * 60)

        save_screenshot(driver, "final_success")

        log_print("\n浏览器保持打开，按回车键关闭...")
        input()

    except KeyboardInterrupt:
        log_print("\n用户中断流程", "WARN")
    except Exception as e:
        log_print(f"\n流程异常: {e}", "ERROR")
        import traceback
        log_print(traceback.format_exc(), "ERROR")
    finally:
        if driver:
            driver.quit()
            log_print("浏览器已关闭")

        log_print("\n流程结束")
        input("按回车键退出...")


if __name__ == "__main__":
    main()


    