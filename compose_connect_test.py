"""
第二层：连接到已打开的调试浏览器，进入写信页面并检测
"""

import time
import json
import os
import re
import sys
from selenium import webdriver
from selenium.webdriver.edge.options import Options

SESSION_FILE = "browser_session.json"

LOG_DIR = fr"result\log"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, time.strftime(fr"compose_connect_%Y%m%d_%H%M%S") + ".txt")
_log_fp = open(LOG_FILE, "w", encoding="utf-8")


def _write_log(msg):
    print(msg)
    _log_fp.write(msg + "\n")
    _log_fp.flush()


def connect_to_existing_browser():
    if not os.path.exists(SESSION_FILE):
        _write_log("[-] 错误：未找到会话文件，请先运行 single_login.py")
        return None, None

    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        session = json.load(f)

    debug_port = session.get("debug_port", 9223)
    sid = session.get("sid", "")

    _write_log("=" * 60)
    _write_log("第二层：连接到已打开的浏览器")
    _write_log("=" * 60)
    _write_log(f"[*] 调试端口: {debug_port}")
    _write_log(f"[*] sid: {sid[:30]}..." if len(sid) > 30 else f"[*] sid: {sid}")

    options = Options()
    options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")

    try:
        driver = webdriver.Edge(options=options)
        _write_log(f"[+] 成功连接到已打开的浏览器！")
        _write_log(f"[+] 当前页面标题: {driver.title}")
        _write_log(f"[+] 当前URL: {driver.current_url[:80]}...")
        return driver, sid
    except Exception as e:
        _write_log(f"[-] 连接失败: {e}")
        return None, None


def is_compose_page(driver):
    indicators = [
        "//*[contains(text(),'收件人')]",
        "//*[contains(text(),'主题')]",
        "//*[contains(text(),'发送')]",
        "//div[contains(@class,'compose')]",
        "//div[@contenteditable='true']",
        "//iframe"
    ]
    for xpath in indicators:
        try:
            driver.find_element("xpath", xpath)
            return True
        except:
            continue
    return False


def enter_compose_by_url(driver, sid):
    if not sid:
        _write_log("[-] 缺少 sid,无法进入写信页面")
        return False

    compose_url = f"https://stu.mail.ecust.edu.cn/js6/main.jsp?sid={sid}&show_new=1&hl=zh_CN#module=compose.ComposeModule%7C%7B%7D"
    _write_log(f"[*] 正在打开写信页面...")
    driver.get(compose_url)
    time.sleep(5)

    current_url = driver.current_url
    _write_log(f"[*] 当前URL: {current_url[:80]}...")

    if "compose" in current_url or is_compose_page(driver):
        _write_log("[+] 成功进入写信页面")
        return True
    else:
        _write_log("[-] 进入写信页面失败")
        return False


def main():
    driver, sid = connect_to_existing_browser()
    if not driver:
        input("\n按回车键退出...")
        return

    try:
        if enter_compose_by_url(driver, sid):
            _write_log("[+] 第二层完成：写信页面已就绪")
        else:
            _write_log("[-] 第二层失败：无法进入写信页面")
            input("按回车键关闭...")

    except Exception as e:
        _write_log(f"[!] 异常: {e}")
    finally:
        _write_log("[*] 第二层结束，浏览器保持打开")
        _log_fp.close()


if __name__ == "__main__":
    main()