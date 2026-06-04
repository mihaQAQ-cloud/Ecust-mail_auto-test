"""
网易邮箱集成测试：登录 -> 收件箱 -> 查找学号邮件 -> 打开 -> 设为红旗邮件
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
USERNAME = "********"    #保护隐私，自行修改
PASSWORD = "******"

# 目标发件人学号（在收件箱中搜索这个学号发来的邮件）
TARGET_SENDER = "********"    #保护隐私，自行修改

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
    log_file = os.path.join(LOG_DIR, f"red_flag_{time.strftime('%Y%m%d')}.log")
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
    return False


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

    try:
        username_input = driver.find_element(By.XPATH, "//input[@placeholder='请输入登录账号']")
    except:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        username_input = [inp for inp in inputs if inp.get_attribute("type") == "text"][0]

    username_input.clear()
    username_input.send_keys(USERNAME)
    log_print(f"已输入账号: {USERNAME}")
    time.sleep(1)

    password_input = driver.find_element(By.XPATH, "//input[@type='password']")
    password_input.clear()
    password_input.send_keys(PASSWORD)
    log_print("已输入密码")
    time.sleep(1)

    password_input.send_keys(Keys.ENTER)
    log_print("已提交登录")
    time.sleep(6)

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
        return sid
    else:
        log_print(f"登录失败: {current_url}", "FAIL")
        return None


# ==================== 第二层：进入收件箱 ====================
def layer2_enter_inbox(driver, sid):
    """进入收件箱页面"""
    log_print("\n" + "=" * 60)
    log_print("【第二层】进入收件箱")
    log_print("=" * 60)

    if not sid:
        current_url = driver.current_url
        sid_match = re.search(r'sid=([^&]+)', current_url)
        if sid_match:
            sid = sid_match.group(1)
            log_print(f"从当前URL提取sid: {sid[:20]}...")
        else:
            log_print("无法获取sid", "ERROR")
            return False

    log_print("正在尝试进入收件箱...")

    # 方法1：点击左侧"收件箱"
    inbox_selectors = [
        "//span[contains(text(),'收件箱')]",
        "//a[contains(text(),'收件箱')]",
        "//div[contains(text(),'收件箱')]",
        "//li[contains(text(),'收件箱')]",
        "//span[@class='nui-tree-item-text' and contains(text(),'收件箱')]",
        "//div[contains(@title,'收件箱')]",
        "//*[contains(@class,'folder') and contains(text(),'收件箱')]",
    ]

    clicked = False
    for xpath in inbox_selectors:
        try:
            elem = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            elem.click()
            log_print(f"点击'收件箱'成功: {xpath}", "PASS")
            clicked = True
            time.sleep(3)
            break
        except:
            continue

    # 方法2：URL跳转
    if not clicked:
        log_print("点击方式失败，尝试URL跳转...", "WARN")
        url_patterns = [
            f"https://stu.mail.ecust.edu.cn/js6/main.jsp?sid={sid}&show_new=1&hl=zh_CN#module=mbox.ListModule%7C%7B%7B%22fid%22%3A1%7D%7D",
            f"https://stu.mail.ecust.edu.cn/js6/main.jsp?sid={sid}#module=mbox.ListModule%7C%7B%7B%22fid%22%3A1%7D%7D",
            f"https://stu.mail.ecust.edu.cn/js6/main.jsp?sid={sid}&module=mbox.ListModule&fid=1",
        ]
        for url in url_patterns:
            try:
                driver.get(url)
                log_print(f"尝试URL: {url[:80]}...")
                time.sleep(4)
                if is_inbox_page(driver):
                    log_print("URL跳转成功", "PASS")
                    clicked = True
                    break
            except Exception as e:
                log_print(f"URL尝试失败: {e}")
                continue

    if is_inbox_page(driver):
        log_print("成功进入收件箱", "PASS")
        save_screenshot(driver, "inbox")
        return True
    else:
        log_print("进入收件箱失败", "FAIL")
        log_print(f"当前URL: {driver.current_url}")
        return False


def is_inbox_page(driver):
    """检查是否在收件箱页面"""
    current_url = driver.current_url
    if "fid=1" in current_url:
        return True
    indicators = [
        "//span[contains(text(),'收件箱')]",
        "//div[contains(text(),'收件箱')]",
        "//a[contains(text(),'收件箱')]",
        "//span[@class='nui-tree-item-text' and contains(text(),'收件箱')]",
    ]
    for xpath in indicators:
        try:
            WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, xpath)))
            return True
        except:
            continue
    return False


# ==================== 第三层：搜索并打开邮件 ====================
def layer3_search_and_open(driver, sender=TARGET_SENDER):
    """在收件箱搜索指定发件人的邮件并打开"""
    log_print("\n" + "=" * 60)
    log_print(f"【第三层】搜索发件人为 '{sender}' 的邮件")
    log_print("=" * 60)

    time.sleep(2)

    # 定位发件人元素
    text_locators = [
        f"//span[contains(text(),'{sender}')]",
        f"//div[contains(text(),'{sender}')]",
        f"//a[contains(text(),'{sender}')]",
        f"//td[contains(text(),'{sender}')]",
        f"//span[contains(@title,'{sender}')]",
        f"//div[contains(@title,'{sender}')]",
    ]

    target_elem = None
    for xpath in text_locators:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                visible = [e for e in elements if e.is_displayed()]
                target_elem = visible[0] if visible else elements[0]
                log_print(f"找到发件人元素: {xpath} (共{len(elements)}个，可见{len(visible) if visible else '?' }个)")
                break
        except:
            continue

    if not target_elem:
        log_print(f"未找到包含 '{sender}' 的元素", "FAIL")
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if sender in body_text:
                log_print("页面文本中包含目标发件人，但XPath定位失败", "WARN")
            else:
                log_print("页面文本中也不包含目标发件人", "FAIL")
        except:
            pass
        save_screenshot(driver, "debug_no_sender")
        return False

    # 向上查找可点击的邮件行
    clickable_row = None
    current = target_elem
    for i in range(6):
        try:
            parent = current.find_element(By.XPATH, "..")
            tag = parent.tag_name.lower()
            onclick = parent.get_attribute("onclick")
            class_attr = parent.get_attribute("class") or ""

            if tag in ["tr", "div", "li"]:
                if onclick or any(kw in class_attr.lower() for kw in ["item", "row", "list", "mail", "msg"]):
                    clickable_row = parent
                    log_print(f"找到可点击父元素(第{i+1}层): <{tag}>")
                    break
                if i >= 1:
                    clickable_row = parent
                    log_print(f"使用父元素(第{i+1}层)尝试: <{tag}>")
                    break
            current = parent
        except:
            break

    # 兜底：用发件人元素本身
    if not clickable_row:
        clickable_row = target_elem
        log_print("使用发件人元素本身尝试点击")

    clicked = safe_click(driver, clickable_row, f"发件人{sender}所在行")

    if clicked:
        time.sleep(3)
        current_url = driver.current_url
        log_print(f"点击后当前URL: {current_url[:100]}...")

        is_read_page = any(kw in current_url.lower() for kw in ["read", "view", "detail", "mid"])
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


# ==================== 第四层：设为红旗邮件 ====================
def layer4_set_red_flag(driver):
    """
    【第四层】将当前打开的邮件设为红旗邮件
    网易邮箱红旗标记方式：
    1. 邮件列表页：点击邮件前面的小旗帜图标
    2. 读信页：点击邮件标题旁/右上角的红旗标识
    """
    log_print("\n" + "=" * 60)
    log_print("【第四层】设为红旗邮件")
    log_print("=" * 60)

    time.sleep(2)

    # 策略1：在读信页面查找红旗/旗帜按钮（toolbar/header/action区域优先）
    flag_selectors = [
        # toolbar/header 区域的红旗按钮
        "//div[contains(@class,'toolbar')]//*[contains(@class,'flag')]",
        "//div[contains(@class,'toolbar')]//*[contains(@title,'红旗')]",
        "//div[contains(@class,'toolbar')]//*[contains(@title,'标记')]",
        "//div[contains(@class,'header')]//*[contains(@class,'flag')]",
        "//div[contains(@class,'header')]//*[contains(@title,'红旗')]",
        "//div[contains(@class,'header')]//*[contains(@title,'标记')]",
        # action 区域
        "//div[contains(@class,'action')]//*[contains(@class,'flag')]",
        "//div[contains(@class,'action')]//*[contains(@title,'红旗')]",
        # 通用：包含 flag 或 红旗 的元素
        "//*[contains(@class,'flag') and not(contains(@class,'flagged'))]",
        "//*[contains(@title,'红旗')]",
        "//*[contains(@title,'标记为')]",
        "//*[contains(@title,'旗帜')]",
        # 图标类按钮（可能用 i/span 做图标）
        "//i[contains(@class,'flag')]",
        "//span[contains(@class,'flag')]",
        "//div[contains(@class,'flag')]",
        # 文本匹配
        "//button[contains(text(),'红旗')]",
        "//a[contains(text(),'红旗')]",
        "//span[contains(text(),'红旗')]",
        "//button[contains(text(),'标记')]",
        "//a[contains(text(),'标记')]",
    ]

    all_candidates = []

    for xpath in flag_selectors:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for elem in elements:
                if elem.is_displayed():
                    elem_text = elem.text or ""
                    text_content = elem.get_attribute("textContent") or ""
                    elem_title = elem.get_attribute("title") or ""
                    elem_class = elem.get_attribute("class") or ""
                    elem_tag = elem.tag_name

                    # 获取尺寸
                    try:
                        size = elem.size
                        width = size['width']
                        height = size['height']
                    except:
                        width = 9999
                        height = 9999

                    # 排除大容器
                    if width > 300 or height > 300:
                        continue
                    if any(kw in elem_class.lower() for kw in ['frame', 'main', 'outer', 'container', 'wrapper']):
                        if width > 150 or height > 150:
                            continue

                    # 获取坐标
                    try:
                        y_pos = elem.location['y']
                        x_pos = elem.location['x']
                    except:
                        y_pos = 999999
                        x_pos = 999999

                    # 检查是否包含红旗/标记/旗帜相关
                    combined = (elem_text + text_content + elem_title + elem_class).replace(" ", "").replace("\n", "")
                    has_flag = any(kw in combined.lower() for kw in ['flag', '红旗', '标记', '旗帜'])

                    if has_flag:
                        all_candidates.append({
                            'elem': elem,
                            'xpath': xpath,
                            'tag': elem_tag,
                            'text': elem_text[:20],
                            'title': elem_title[:20],
                            'class': elem_class[:40],
                            'x': x_pos,
                            'y': y_pos,
                            'width': width,
                            'height': height,
                        })
        except:
            pass

    # 策略2：如果没找到，尝试查找邮件标题附近的红旗图标
    if not all_candidates:
        log_print("toolbar区域未找到，尝试查找邮件标题附近...", "WARN")
        near_title_selectors = [
            "//h1//following-sibling::*[contains(@class,'flag')]",
            "//h2//following-sibling::*[contains(@class,'flag')]",
            "//div[contains(@class,'subject')]//following-sibling::*[contains(@class,'flag')]",
            "//div[contains(@class,'title')]//following-sibling::*[contains(@class,'flag')]",
            "//span[contains(@class,'subject')]//following-sibling::*[contains(@class,'flag')]",
        ]
        for xpath in near_title_selectors:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for elem in elements:
                    if elem.is_displayed():
                        try:
                            size = elem.size
                            if size['width'] > 300 or size['height'] > 300:
                                continue
                        except:
                            pass
                        try:
                            y_pos = elem.location['y']
                            x_pos = elem.location['x']
                        except:
                            y_pos = 999999
                            x_pos = 999999
                        all_candidates.append({
                            'elem': elem,
                            'xpath': xpath,
                            'tag': elem.tag_name,
                            'text': (elem.text or "")[:20],
                            'title': (elem.get_attribute("title") or "")[:20],
                            'class': (elem.get_attribute("class") or "")[:40],
                            'x': x_pos,
                            'y': y_pos,
                            'width': size.get('width', 0),
                            'height': size.get('height', 0),
                        })
            except:
                pass

    if not all_candidates:
        log_print("[-] 未找到任何红旗/标记按钮", "FAIL")
        save_screenshot(driver, "debug_no_flag")
        return False

    # 按 y 坐标排序，选择最顶部的（toolbar区域通常在顶部）
    all_candidates.sort(key=lambda x: x['y'])

    log_print(f"找到 {len(all_candidates)} 个候选，显示前5个:")
    for i, c in enumerate(all_candidates[:5]):
        log_print(f"  候选{i+1}: <{c['tag']}> x={c['x']} y={c['y']} w={c['width']} h={c['height']} "
                  f"text='{c['text']}' title='{c['title']}' class='{c['class']}'")

    # 选择最顶部的候选点击
    target = all_candidates[0]['elem']
    best = all_candidates[0]

    clicked = safe_click(driver, target, 
        f"红旗按钮 (x={best['x']}, y={best['y']}, w={best['width']}, h={best['height']}, "
        f"text='{best['text']}', title='{best['title']}')")

    if clicked:
        time.sleep(2)

        # 验证是否标记成功：检查元素 class 是否变为红色/flagged状态
        try:
            # 重新查找该元素，看是否变为红色状态
            new_class = target.get_attribute("class") or ""
            new_title = target.get_attribute("title") or ""
            log_print(f"点击后元素 class: '{new_class[:50]}' title: '{new_title[:30]}'")

            # 检查是否有红色相关class
            is_red = any(kw in new_class.lower() for kw in ['red', 'active', 'on', 'selected', 'flagged'])
            if is_red:
                log_print("红旗标记成功！元素已变为红色状态", "PASS")
            else:
                log_print("已点击红旗按钮，请确认标记状态", "INFO")
        except Exception as e:
            log_print(f"验证标记状态时出错: {e}", "WARN")

        save_screenshot(driver, "red_flag_set")
        return True
    else:
        log_print("[-] 点击红旗按钮失败", "FAIL")
        save_screenshot(driver, "debug_flag_fail")
        return False


# ==================== 主程序 ====================
def close_browser_prompt(driver):
    """统一关闭浏览器提示，无论成功失败都执行"""
    if driver:
        try:
            log_print("\n" + "-" * 60)
            log_print("按回车键关闭浏览器并退出...")
            input()
        except KeyboardInterrupt:
            log_print("用户跳过等待", "WARN")
        finally:
            try:
                driver.quit()
                log_print("浏览器已关闭")
            except Exception as e:
                log_print(f"关闭浏览器时出错: {e}", "ERROR")


def main():
    """主程序：完整流程"""
    driver = None

    try:
        print("=" * 60)
        print("网易邮箱自动化 - 设为红旗邮件")
        print("=" * 60)
        print("流程: 登录 -> 收件箱 -> 搜索邮件 -> 打开 -> 设为红旗")
        print("=" * 60)

        # 第一层：登录
        driver = create_debug_driver()
        sid = layer1_login(driver)

        if not sid:
            log_print("登录失败，流程终止", "FAIL")
            close_browser_prompt(driver)
            return

        # 第二层：进入收件箱
        if not layer2_enter_inbox(driver, sid):
            log_print("进入收件箱失败，流程终止", "FAIL")
            close_browser_prompt(driver)
            return

        # 第三层：搜索并打开邮件
        if not layer3_search_and_open(driver, TARGET_SENDER):
            log_print("搜索邮件失败，流程终止", "FAIL")
            close_browser_prompt(driver)
            return

        # 第四层：设为红旗邮件
        if not layer4_set_red_flag(driver):
            log_print("设为红旗邮件失败", "FAIL")
            close_browser_prompt(driver)
            return

        # 完成
        log_print("\n" + "=" * 60)
        log_print("【流程完成】邮件已设为红旗", "PASS")
        log_print("=" * 60)

        save_screenshot(driver, "final_success")
        close_browser_prompt(driver)

    except KeyboardInterrupt:
        log_print("\n用户中断流程", "WARN")
        close_browser_prompt(driver)
    except Exception as e:
        log_print(f"\n流程异常: {e}", "ERROR")
        import traceback
        log_print(traceback.format_exc(), "ERROR")
        close_browser_prompt(driver)


if __name__ == "__main__":
    main()
