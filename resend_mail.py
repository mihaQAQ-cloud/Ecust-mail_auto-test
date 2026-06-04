"""
第四层：连接到已打开的调试浏览器（已在读信页面），点击"再次编辑发送"
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
from selenium.webdriver.common.action_chains import ActionChains

# 会话文件（与第一个文件共享）
SESSION_FILE = "browser_session.json"

# 结果目录
RESULT_DIR = "result"
PIC_DIR = os.path.join(RESULT_DIR, "pic")
LOG_DIR = os.path.join(RESULT_DIR, "log")


def ensure_dirs():
    """确保结果目录存在"""
    os.makedirs(PIC_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def log_print(message, level="INFO"):
    """打印日志，同时写入日志文件"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "[*]", "PASS": "[+]", "FAIL": "[-]", "ERROR": "[!]", "WARN": "[?]"}
    p = prefix.get(level, "[*]")
    log_line = f"[{timestamp}] {p} {message}"
    print(log_line)

    ensure_dirs()
    log_file = os.path.join(LOG_DIR, f"layer4_{time.strftime('%Y%m%d')}.log")
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
        print("="*60)
        return None

    # 读取会话信息
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        session = json.load(f)

    debug_port = session.get("debug_port", 9223)

    print("="*60)
    print("第四层：连接到已打开的浏览器，点击再次编辑发送")
    print("="*60)
    print(f"[*] 调试端口: {debug_port}")
    print("-"*60)

    # 使用Chrome DevTools Protocol连接到现有浏览器
    options = Options()
    options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")

    try:
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


def click_resend_edit(driver):
    """
    点击"再次编辑发送"按钮
    """
    log_print("\n[*] 开始查找'再次编辑发送'按钮...")

    # 等待页面加载
    time.sleep(2)

    # 多种定位方式
    resend_selectors = [
        # 直接文本匹配
        "//button[contains(text(),'再次编辑发送')]",
        "//a[contains(text(),'再次编辑发送')]",
        "//span[contains(text(),'再次编辑发送')]",
        "//div[contains(text(),'再次编辑发送')]",
        # 部分文本匹配
        "//button[contains(text(),'再次编辑')]",
        "//a[contains(text(),'再次编辑')]",
        "//span[contains(text(),'再次编辑')]",
        "//div[contains(text(),'再次编辑')]",
        # title属性
        "//*[contains(@title,'再次编辑发送')]",
        "//*[contains(@title,'再次编辑')]",
        # class包含相关关键词
        "//button[contains(@class,'resend')]",
        "//a[contains(@class,'resend')]",
        "//span[contains(@class,'resend')]",
        # 通用按钮区域查找
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
                # 过滤可见元素
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    target = visible[0]
                else:
                    target = elements[0]

                log_print(f"找到元素: {xpath} (共{len(elements)}个，可见{len(visible) if visible else '?' }个)")

                # 检查文本确认是"再次编辑发送"
                elem_text = target.text or target.get_attribute("textContent") or ""
                elem_title = target.get_attribute("title") or ""
                log_print(f"元素文本: '{elem_text[:30]}' title: '{elem_title[:30]}'")

                # 如果文本匹配，尝试点击
                if "再次编辑" in elem_text or "再次编辑" in elem_title or "resend" in xpath:
                    if safe_click(driver, target, f"再次编辑发送按钮 ({xpath})"):
                        clicked = True
                        time.sleep(3)
                        break
                else:
                    # 即使文本不完全匹配，也尝试点击（可能是子元素包含文本）
                    if safe_click(driver, target, f"可能的再次编辑按钮 ({xpath})"):
                        # 点击后检查是否进入编辑页面
                        time.sleep(3)
                        current_url = driver.current_url
                        if "compose" in current_url.lower() or "写信" in driver.title:
                            log_print("[+] 成功进入编辑页面", "PASS")
                            clicked = True
                            break
                        else:
                            log_print("[*] 点击后未进入编辑页面，继续查找")

        except Exception as e:
            continue

    if clicked:
        # 验证是否进入写信/编辑页面
        time.sleep(2)
        current_url = driver.current_url
        page_title = driver.title

        log_print(f"当前URL: {current_url[:100]}...")
        log_print(f"当前标题: {page_title}")

        # 检查是否进入编辑页面
        is_edit_page = any(kw in current_url.lower() for kw in ["compose", "edit", "resend"])
        is_edit_title = any(kw in page_title for kw in ["写信", "编辑", "Compose"])

        if is_edit_page or is_edit_title:
            log_print("[+] 确认进入编辑/写信页面", "PASS")
        else:
            log_print("[?] 可能未进入编辑页面，请检查", "WARN")

        # 截图保存
        ensure_dirs()
        screenshot_path = os.path.join(PIC_DIR, f"resend_edit_{time.strftime('%Y%m%d_%H%M%S')}.png")
        driver.save_screenshot(screenshot_path)
        log_print(f"截图已保存: {screenshot_path}")

        return True
    else:
        log_print("[-] 未找到或无法点击'再次编辑发送'按钮", "FAIL")

        # 调试截图
        ensure_dirs()
        debug_path = os.path.join(PIC_DIR, f"debug_layer4_{time.strftime('%Y%m%d_%H%M%S')}.png")
        driver.save_screenshot(debug_path)
        log_print(f"调试截图已保存: {debug_path}")

        return False


def main():
    """主程序：连接到已有浏览器，点击再次编辑发送"""

    # 连接到第一个文件打开的浏览器
    driver = connect_to_existing_browser()

    if not driver:
        input("\n按回车键退出...")
        return

    try:
        # 点击再次编辑发送
        if click_resend_edit(driver):
            log_print("\n[*] 已完成：进入再次编辑发送页面")
            log_print("[*] 浏览器保持打开，按回车键关闭...")
            input()
        else:
            log_print("\n[-] 无法点击再次编辑发送")
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