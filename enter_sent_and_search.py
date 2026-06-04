"""
第三层：连接到已打开的调试浏览器（已在已发送页面），搜索并点击收件人为23070066的邮件
"""

import time
import json
import os
import re
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# 会话文件（与第一个文件共享）
SESSION_FILE = "browser_session.json"

# 结果目录
RESULT_DIR = "result"
PIC_DIR = os.path.join(RESULT_DIR, "pic")
LOG_DIR = os.path.join(RESULT_DIR, "log")

# 目标收件人
TARGET_RECIPIENT = "********" #保护隐私，自行修改


def ensure_dirs():
    """确保结果目录存在"""
    os.makedirs(PIC_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def log_print(message, level="INFO"):
    """打印日志，同时写入日志文件"""
    timestamp = time.strftime(fr"%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "[*]", "PASS": "[+]", "FAIL": "[-]", "ERROR": "[!]", "WARN": "[?]"}
    p = prefix.get(level, "[*]")
    log_line = f"[{timestamp}] {p} {message}"
    print(log_line)

    ensure_dirs()
    log_file = os.path.join(LOG_DIR, f"search_mail_{time.strftime(fr'%Y%m%d')}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def connect_to_existing_browser():
    """
    连接到第一个文件打开的浏览器
    通过读取 browser_session.json 获取调试端口
    """

    # 检查会话文件是否存在
    if not os.path.exists(SESSION_FILE):
        print("="*60)
        print("[-] 错误：未找到会话文件")
        print("[-] 请先运行第一个脚本完成登录")
        print("[-] 第一个脚本会创建 browser_session.json 文件")
        print("="*60)
        return None

    # 读取会话信息
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        session = json.load(f)

    debug_port = session.get("debug_port", 9223)

    print("="*60)
    print("第三层：连接到已打开的浏览器，搜索目标邮件")
    print("="*60)
    print(f"[*] 调试端口: {debug_port}")
    print("-"*60)

    # 使用Chrome DevTools Protocol连接到现有浏览器
    options = Options()
    options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")

    try:
        # 关键：不创建新浏览器，而是连接到已有的
        driver = webdriver.Edge(options=options)

        print(f"[+] 成功连接到已打开的浏览器！")
        print(f"[+] 当前页面标题: {driver.title}")
        print(f"[+] 当前URL: {driver.current_url[:80]}...")

        return driver

    except Exception as e:
        print(f"[-] 连接失败: {e}")
        print("[-] 可能原因：")
        print("    1. 第一个脚本已关闭（浏览器被关闭）")
        print("    2. 调试端口错误")
        print("    3. 浏览器崩溃")
        print("\n[*] 解决方式：重新运行第一个脚本登录")
        return None


def safe_click(driver, elem, desc=""):
    """
    安全点击元素，尝试多种点击方式
    """
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
    """
    向上查找可点击的父元素
    网易邮箱邮件列表中，整行通常是div或tr，包含onclick事件
    """
    current = elem
    for i in range(max_levels):
        try:
            parent = current.find_element(By.XPATH, "..")
            tag = parent.tag_name.lower()
            onclick = parent.get_attribute("onclick")
            class_attr = parent.get_attribute("class") or ""

            log_print(f"第{i+1}层父元素: <{tag}> class='{class_attr[:60]}' onclick={'有' if onclick else '无'}")

            # 网易邮箱邮件行特征：div容器，可能有m-r-list-item等class，或带onclick
            if tag in ["tr", "div", "li"]:
                # 如果父元素有onclick，或class包含item/row/list，认为是可点击行
                if onclick or any(kw in class_attr.lower() for kw in ["item", "row", "list", "mail", "msg"]):
                    log_print(f"找到可点击父元素(第{i+1}层): <{tag}> class='{class_attr[:40]}'")
                    return parent
                # 即使没有特定class，div/tr也可能是行容器，尝试返回
                if i >= 1:  # 至少向上找一层
                    log_print(f"使用父元素(第{i+1}层)尝试: <{tag}>")
                    return parent

            current = parent
        except Exception as e:
            log_print(f"查找父元素失败(第{i+1}层): {e}")
            break

    return None


def search_and_click_recipient(driver, recipient=TARGET_RECIPIENT):
    """
    在已发送页面搜索并点击指定收件人的邮件
    根据网易邮箱页面结构优化
    """
    log_print(f"\n[*] 开始搜索收件人为 '{recipient}' 的邮件...")

    # 先等待邮件列表加载
    time.sleep(2)

    # 方法1：直接定位收件人文本，然后找其所在行
    # 网易邮箱中，收件人通常在一个span或div中
    text_locators = [
        f"//span[contains(text(),'{recipient}')]",
        f"//div[contains(text(),'{recipient}')]",
        f"//a[contains(text(),'{recipient}')]",
        f"//td[contains(text(),'{recipient}')]",
        f"//span[contains(@title,'{recipient}')]",
        f"//div[contains(@title,'{recipient}')]",
    ]

    target_elem = None
    found_xpath = ""

    for xpath in text_locators:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                # 过滤可见元素
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    target_elem = visible[0]
                else:
                    target_elem = elements[0]
                found_xpath = xpath
                log_print(f"找到收件人元素: {xpath} (共{len(elements)}个，可见{len(visible) if visible else '?' }个)")
                break
        except:
            continue

    if not target_elem:
        log_print(f"[-] 未找到包含 '{recipient}' 的元素", "FAIL")

        # 调试：打印页面所有文本内容帮助定位
        log_print("[*] 尝试获取页面文本进行调试...")
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if recipient in body_text:
                log_print("[+] 页面文本中包含目标收件人，但XPath定位失败")
            else:
                log_print("[-] 页面文本中也不包含目标收件人")
        except:
            pass

        # 调试截图
        ensure_dirs()
        debug_path = os.path.join(PIC_DIR, f"debug_no_element_{time.strftime(fr'%Y%m%d_%H%M%S')}.png")
        driver.save_screenshot(debug_path)
        log_print(f"调试截图已保存: {debug_path}")
        return False

    # 方法2：找到收件人元素后，向上查找可点击的邮件行
    clickable_row = get_clickable_parent(driver, target_elem, max_levels=6)

    # 如果没找到合适的父元素，尝试找兄弟元素（如主题链接）
    if not clickable_row:
        log_print("[*] 尝试查找兄弟元素（主题链接）...")
        try:
            # 尝试找到同一行中的主题元素（通常是链接或带onclick的元素）
            # 从收件人元素出发，找父级容器，再找容器内的主题链接
            parent = target_elem.find_element(By.XPATH, "..")
            # 在父元素内查找链接或带onclick的元素
            links = parent.find_elements(By.XPATH, ".//a | .//div[@onclick] | .//span[@onclick]")
            if links:
                for link in links:
                    if link.is_displayed():
                        clickable_row = link
                        log_print(f"找到兄弟链接元素: <{link.tag_name}>")
                        break
        except Exception as e:
            log_print(f"查找兄弟元素失败: {e}")

    # 如果还是没找到，尝试使用收件人元素的父级的父级（整行容器）
    if not clickable_row:
        try:
            grandparent = target_elem.find_element(By.XPATH, "../..")
            tag = grandparent.tag_name.lower()
            if tag in ["tr", "div", "li"]:
                clickable_row = grandparent
                log_print(f"使用祖父元素作为行: <{tag}>")
        except:
            pass

    # 最终尝试：直接用收件人元素本身
    if not clickable_row:
        clickable_row = target_elem
        log_print("[*] 使用收件人元素本身尝试点击")

    # 执行点击
    clicked = safe_click(driver, clickable_row, f"收件人{recipient}所在行")

    if clicked:
        time.sleep(3)

        # 验证是否成功打开
        current_url = driver.current_url
        log_print(f"点击后当前URL: {current_url[:100]}...")

        # 检查是否进入读信页面
        is_read_page = any(kw in current_url.lower() for kw in ["read", "view", "detail", "mid", "compose"])
        page_title = driver.title

        if is_read_page or "读信" in page_title or "邮件" in page_title:
            log_print("[+] 疑似成功打开邮件", "PASS")
        else:
            log_print("[*] 点击完成，等待页面加载...")
            time.sleep(2)

        # 截图保存
        ensure_dirs()
        screenshot_path = os.path.join(PIC_DIR, f"mail_opened_{time.strftime(fr'%Y%m%d_%H%M%S')}.png")
        driver.save_screenshot(screenshot_path)
        log_print(f"截图已保存: {screenshot_path}")

        return True
    else:
        log_print(f"[-] 所有点击方式均失败", "FAIL")

        # 调试截图
        ensure_dirs()
        debug_path = os.path.join(PIC_DIR, f"debug_click_fail_{time.strftime(fr'%Y%m%d_%H%M%S')}.png")
        driver.save_screenshot(debug_path)
        log_print(f"调试截图已保存: {debug_path}")

        return False


def main():
    """主程序：连接到已有浏览器，搜索并点击指定邮件"""

    # 连接到第一个文件打开的浏览器
    driver = connect_to_existing_browser()

    if not driver:
        # 连接失败，退出
        input("\n按回车键退出...")
        return

    try:
        # 搜索并点击收件人为23070066的邮件
        if search_and_click_recipient(driver, TARGET_RECIPIENT):
            log_print("\n[*] 已完成：打开目标邮件")
            log_print("[*] 浏览器保持打开，按回车键关闭...")
            input()
        else:
            log_print("\n[-] 无法找到或点击目标邮件")
            log_print("[*] 浏览器保持打开，按回车键关闭...")
            input()

    except KeyboardInterrupt:
        log_print("\n[*] 用户中断")
    except Exception as e:
        log_print(f"\n[!] 异常: {e}", "ERROR")
    finally:
        driver.quit()
        log_print("[*] 已关闭")


if __name__ == "__main__":
    main()

    
