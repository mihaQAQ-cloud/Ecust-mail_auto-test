"""
第一步：启动调试模式浏览器，登录并保存会话信息
支持数据驱动测试，多账号组合验证
有效账号全部测试，不停止
"""

import time
import json
import os
import sys
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# 配置
URL = "https://stu.mail.ecust.edu.cn/"

# 测试数据
#保护隐私，自行修改
VALID_USERS = [
    {"username": "********", "password": "******", "desc": "账号一"},
    {"username": "********", "password": "******", "desc": "账号二"},
]

INVALID_USERS = [
    {"username": "********", "password": "******", "desc": "错误-密码全小写"},
    {"username": "********", "password": "*******", "desc": "错误-密码全大写"},
    {"username": "********", "password": "******", "desc": "错误-密码错误"},
    {"username": "********", "password": "******", "desc": "错误-账号不存在"},
    {"username": "", "password": "******", "desc": "错误-空账号"},
    {"username": "********", "password": "", "desc": "错误-空密码"},
]

# 调试端口和会话文件
DEBUG_PORT = 9223
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
    timestamp = datetime.now().strftime(fr"%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "[*]", "PASS": "[+]", "FAIL": "[-]", "ERROR": "[!]", "WARN": "[?]"}
    p = prefix.get(level, "[*]")
    log_line = f"[{timestamp}] {p} {message}"
    print(log_line)

    ensure_dirs()
    log_file = os.path.join(LOG_DIR, f"login_test_{datetime.now().strftime(fr'%Y%m%d')}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def create_debug_driver():
    """创建带调试端口的Edge浏览器"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    # 关键：添加远程调试端口
    options.add_argument(f"--remote-debugging-port={DEBUG_PORT}")

    # 使用唯一用户数据目录，避免冲突
    import tempfile
    user_data_dir = os.path.join(tempfile.gettempdir(), f"edge_profile_{int(time.time())}")
    options.add_argument(f"--user-data-dir={user_data_dir}")

    # 其他稳定化参数
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    try:
        service = Service(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
    except Exception as e:
        log_print(f"自动驱动失败: {e}")
        log_print("[*] 尝试使用系统默认Edge...")
        driver = webdriver.Edge(options=options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    return driver


def attempt_login(driver, username, password):
    """
    执行单次登录尝试
    返回: (success: bool, error_msg: str, duration: float)
    """
    start_time = time.time()

    try:
        driver.get(URL)
        time.sleep(3)

        # 输入用户名
        try:
            username_input = driver.find_element(By.XPATH, "//input[@placeholder='请输入登录账号']")
        except:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            username_input = [inp for inp in inputs if inp.get_attribute("type") == "text"][0]

        username_input.clear()
        username_input.send_keys(username)
        time.sleep(0.5)

        # 输入密码
        password_input = driver.find_element(By.XPATH, "//input[@type='password']")
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(0.5)

        # 回车登录
        password_input.send_keys(Keys.ENTER)
        time.sleep(4)

        # 检查登录结果
        current_url = driver.current_url
        duration = time.time() - start_time

        if "main.jsp" in current_url:
            return True, "登录成功", duration
        else:
            # 尝试获取错误提示
            error_msg = "未知错误"
            try:
                error_selectors = [
                    "//div[contains(@class,'error')]",
                    "//span[contains(@class,'error')]",
                    "//div[contains(@class,'tip')]",
                    "//span[contains(@class,'tip')]",
                    "//div[contains(text(),'错误')]",
                    "//div[contains(text(),'失败')]",
                    "//div[contains(text(),'密码')]",
                    "//div[contains(text(),'账号')]",
                ]
                for sel in error_selectors:
                    elems = driver.find_elements(By.XPATH, sel)
                    if elems:
                        for e in elems:
                            if e.is_displayed() and e.text.strip():
                                error_msg = e.text.strip()[:50]
                                break
                        if error_msg != "未知错误":
                            break
            except:
                pass

            return False, error_msg, duration

    except Exception as e:
        duration = time.time() - start_time
        return False, f"异常: {str(e)[:80]}", duration


def save_session(driver, username):
    """保存会话信息"""
    current_url = driver.current_url
    sid_match = re.search(r'sid=([^&]+)', current_url)
    sid = sid_match.group(1) if sid_match else ""

    session = {
        "debug_port": DEBUG_PORT,
        "sid": sid,
        "current_url": current_url,
        "username": username,
        "login_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)

    log_print(f"[+] 会话已保存: {SESSION_FILE} (账号: {username})")
    log_print(f"[+] sid: {sid}")
    return sid


def run_login_test(driver, test_data, expected_success):
    """
    运行单组登录测试
    expected_success: True表示期望成功，False表示期望失败
    返回测试结果字典
    """
    username = test_data.get("username", "")
    password = test_data.get("password", "")
    desc = test_data.get("desc", "未命名测试")

    log_print(f"\n{'='*60}")
    log_print(f"测试: {desc}")
    log_print(f"账号: {username if username else '(空)'}")
    log_print(f"密码: {'*' * len(password) if password else '(空)'}")
    log_print(f"期望: {'成功' if expected_success else '失败'}")
    log_print(f"{'='*60}")

    success, error_msg, duration = attempt_login(driver, username, password)

    # 截图
    ensure_dirs()
    screenshot_name = f"login_{desc.replace('-', '_').replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}.png"
    screenshot_path = os.path.join(PIC_DIR, screenshot_name)
    driver.save_screenshot(screenshot_path)
    log_print(f"[+] 截图已保存: {screenshot_path}")

    # 判断结果
    if expected_success:
        # 期望成功
        if success:
            log_print(f"[+] 登录成功 ({duration:.2f}s)", "PASS")
            result = {
                "desc": desc,
                "status": "PASS",
                "msg": f"登录成功",
                "time": round(duration, 2),
                "expected": "成功",
                "actual": "成功",
                "screenshot": screenshot_name
            }
            return result, True  # True表示登录成功
        else:
            log_print(f"[-] 登录失败: {error_msg} ({duration:.2f}s)", "FAIL")
            result = {
                "desc": desc,
                "status": "FAIL",
                "msg": f"期望成功但失败: {error_msg}",
                "time": round(duration, 2),
                "expected": "成功",
                "actual": f"失败: {error_msg}",
                "screenshot": screenshot_name
            }
            return result, False
    else:
        # 期望失败
        if not success:
            log_print(f"[+] 登录失败符合预期: {error_msg} ({duration:.2f}s)", "PASS")
            result = {
                "desc": desc,
                "status": "PASS",
                "msg": f"符合预期失败: {error_msg}",
                "time": round(duration, 2),
                "expected": "失败",
                "actual": "失败",
                "screenshot": screenshot_name
            }
            return result, False
        else:
            log_print(f"[-] 登录成功但期望失败 ({duration:.2f}s)", "FAIL")
            result = {
                "desc": desc,
                "status": "FAIL",
                "msg": "期望失败但成功",
                "time": round(duration, 2),
                "expected": "失败",
                "actual": "成功",
                "screenshot": screenshot_name
            }
            return result, True


def print_summary(results):
    """打印测试汇总"""
    log_print("\n" + "="*60)
    log_print("测试结果汇总")
    log_print("="*60)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)

    for i, r in enumerate(results, 1):
        status_icon = "✓" if r["status"] == "PASS" else "✗"
        log_print(f"  {status_icon} [{i}] {r['desc']}")
        log_print(f"      状态: {r['status']} | 耗时: {r['time']:.2f}s")
        log_print(f"      期望: {r['expected']} | 实际: {r['actual']}")
        log_print(f"      截图: {r.get('screenshot', 'N/A')}")

    log_print(f"\n总计: {total} | 通过: {passed} | 失败: {failed}")
    log_print(f"通过率: {passed/total*100:.1f}%" if total > 0 else "N/A")
    log_print("="*60)

    # 保存JSON结果
    ensure_dirs()
    result_file = os.path.join(LOG_DIR, f"login_results_{datetime.now().strftime(fr'%Y%m%d_%H%M%S')}.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_time": datetime.now().strftime(fr"%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "N/A"
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    log_print(f"[+] 详细结果已保存: {result_file}")


def main():
    """主程序：运行所有登录测试"""

    print("="*60)
    print("登录测试 - 数据驱动")
    print("="*60)
    print(f"有效账号: {len(VALID_USERS)} 组")
    print(f"无效账号: {len(INVALID_USERS)} 组")
    print("="*60)

    driver = create_debug_driver()
    results = []
    last_success_user = None  # 记录最后一个成功登录的账号

    try:
        # 1. 测试所有有效账号（期望成功，不停止）
        log_print("\n" + "="*60)
        log_print("第一阶段：测试有效账号（期望登录成功）")
        log_print("="*60)

        for test_data in VALID_USERS:
            result, is_success = run_login_test(driver, test_data, expected_success=True)
            results.append(result)
            if is_success:
                last_success_user = test_data
                # 保存会话（用当前成功的账号）
                save_session(driver, test_data["username"])
                log_print(f"[*] 账号 {test_data['username']} 登录成功，会话已保存")

        # 2. 测试无效账号（期望失败）
        log_print("\n" + "="*60)
        log_print("第二阶段：测试无效账号（期望登录失败）")
        log_print("="*60)

        for test_data in INVALID_USERS:
            result, _ = run_login_test(driver, test_data, expected_success=False)
            results.append(result)

        # 打印汇总
        print_summary(results)

        # 如果有成功登录的账号，提示继续后续测试
        if last_success_user:
            log_print(f"\n[*] 账号 {last_success_user['username']} 最后登录成功")
            log_print("[*] 可以继续运行后续层级测试(layer2/layer3/layer4/layer5)")
            log_print("[*] 按回车键关闭浏览器...")
            input()
        else:
            log_print("\n[-] 没有有效账号登录成功")
            log_print("[*] 按回车键关闭浏览器...")
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
