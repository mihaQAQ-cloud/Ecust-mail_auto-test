"""
第二步：连接到已打开的调试浏览器，进入已发送页面
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
    timestamp = time.strftime(fr"%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "[*]", "PASS": "[+]", "FAIL": "[-]", "ERROR": "[!]"}
    p = prefix.get(level, "[*]")
    log_line = f"[{timestamp}] {p} {message}"
    print(log_line)

    ensure_dirs()
    log_file = os.path.join(LOG_DIR, f"sent_box_{time.strftime(fr'%Y%m%d')}.log")
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
        return None, None

    # 读取会话信息
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        session = json.load(f)

    debug_port = session.get("debug_port", 9223)
    sid = session.get("sid", "")

    print("="*60)
    print("第二步：连接到已打开的浏览器")
    print("="*60)
    print(f"[*] 调试端口: {debug_port}")
    print(f"[*] sid: {sid[:30]}..." if len(sid) > 30 else f"[*] sid: {sid}")
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

        # 验证是否已登录
        if "main.jsp" in driver.current_url:
            print("[+] 确认：已登录状态")
        else:
            print("[?] 警告：可能未登录或已退出")

        return driver, sid

    except Exception as e:
        print(f"[-] 连接失败: {e}")
        print("[-] 可能原因：")
        print("    1. 第一个脚本已关闭（浏览器被关闭）")
        print("    2. 调试端口错误")
        print("    3. 浏览器崩溃")
        print("\n[*] 解决方式：重新运行第一个脚本登录")
        return None, None


def enter_sent_box(driver, sid):
    """
    进入已发送页面 - 通过点击左侧导航栏的"已发送"
    """
    if not sid:
        log_print("缺少sid,尝试从当前URL提取", "ERROR")
        current_url = driver.current_url
        sid_match = re.search(r'sid=([^&]+)', current_url)
        if sid_match:
            sid = sid_match.group(1)
            log_print(f"从当前URL提取sid: {sid[:20]}...")
        else:
            log_print("无法获取sid,进入已发送页面失败", "ERROR")
            return False

    log_print("正在尝试进入已发送页面...")

    # 方法1：尝试点击左侧导航栏的"已发送"链接
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
            log_print(f"点击'已发送'成功: {xpath}")
            clicked = True
            time.sleep(3)
            break
        except:
            continue

    # 方法2：如果点击失败，尝试通过URL直接跳转
    if not clicked:
        log_print("点击方式失败,尝试URL跳转...")

        # 网易邮箱已发送页面的多种URL格式尝试
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

    # 验证是否成功进入
    if is_sent_box_page(driver):
        log_print("成功进入已发送页面", "PASS")

        # 截图保存
        ensure_dirs()
        screenshot_path = os.path.join(PIC_DIR, f"sent_box_{time.strftime(fr'%Y%m%d_%H%M%S')}.png")
        driver.save_screenshot(screenshot_path)
        log_print(f"截图已保存: {screenshot_path}")

        return True
    else:
        log_print("进入已发送页面失败", "FAIL")
        log_print(f"当前URL: {driver.current_url}")
        log_print("建议：检查页面结构或重新登录")
        return False


def is_sent_box_page(driver):
    """检查是否在已发送页面"""
    # 检查URL特征
    current_url = driver.current_url
    if "fid=3" in current_url or "sent" in current_url.lower():
        return True

    # 检查页面元素
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


def main():
    """主程序：连接到已有浏览器并进入已发送页面"""

    # 连接到第一个文件打开的浏览器
    driver, sid = connect_to_existing_browser()

    if not driver:
        # 连接失败，退出
        input("\n按回车键退出...")
        return

    try:
        # 进入已发送页面
        if enter_sent_box(driver, sid):
            log_print("\n[*] 已进入已发送页面，浏览器保持打开")
            log_print("[*] 按回车键关闭浏览器并退出...")
            input()
        else:
            log_print("\n[-] 无法进入已发送页面")
            log_print("[*] 浏览器保持打开")
            input("按回车键关闭...")

    except KeyboardInterrupt:
        log_print("\n[*] 用户中断")
    except Exception as e:
        log_print(f"\n[!] 异常: {e}", "ERROR")
    finally:
        driver.quit()
        log_print("[*] 已关闭")


if __name__ == "__main__":
    main()
    