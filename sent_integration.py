"""
已发送集成测试（IT-01）
流程：登录 → 进入已发送 → 查看第一封邮件详情
自包含，无需预先运行 single_login.py
"""

import time
import os
import re
import tempfile

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from folder_nav import FolderNavigator
from mail_selector import MailSelector

URL = "https://stu.mail.ecust.edu.cn/"
USERNAME = "********"    #保护隐私，自行修改
PASSWORD = "******"
DEBUG_PORT = 9225
SCREENSHOT_DIR = os.path.join("result", "pic")
MAIN_JSP = "https://stu.mail.ecust.edu.cn/js6/main.jsp"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _short_err(e):
    return str(e).split("\n")[0][:80]


def _log(msg, lv="INFO"):
    icons = {"PASS": "[+]", "FAIL": "[-]", "WARN": "[?]",
             "STEP": "  →", "INFO": "[*]", "ERROR": "[!]"}
    print(f"{time.strftime('%H:%M:%S')} {icons.get(lv, '[*]')} {msg}")


def _create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument(f"--remote-debugging-port={DEBUG_PORT}")
    user_data_dir = os.path.join(
        tempfile.gettempdir(), f"edge_sent_int_{int(time.time())}")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    try:
        service = Service(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
    except Exception:
        driver = webdriver.Edge(options=options)
    return driver


def _login(driver):
    _log("打开登录页...")
    driver.get(URL)
    time.sleep(4)

    try:
        u = driver.find_element(By.XPATH, "//input[@placeholder='请输入登录账号']")
    except Exception:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        u = [i for i in inputs if i.get_attribute("type") == "text"][0]

    u.clear()
    u.send_keys(USERNAME)
    time.sleep(0.8)

    p = driver.find_element(By.XPATH, "//input[@type='password']")
    p.clear()
    p.send_keys(PASSWORD)
    time.sleep(0.8)
    p.send_keys(Keys.ENTER)
    _log("已提交登录，等待跳转...")
    time.sleep(6)

    cur = driver.current_url
    if "main.jsp" in cur:
        m = re.search(r'sid=([^&]+)', cur)
        sid = m.group(1) if m else ""
        _log(f"登录成功，sid={sid[:12]}...", "PASS")
        return sid
    _log(f"登录失败，当前URL: {cur[:80]}", "FAIL")
    return None


def run_it01(driver, sid):
    """IT-01: 登录→已发送→查看邮件详情"""
    nav = FolderNavigator(driver, sid)
    selector = MailSelector(driver, sid)

    steps = []
    result = {
        "id": "IT-01",
        "name": "登录→已发送→查看邮件详情",
        "depth": 3,
        "steps": steps,
        "passed": False,
        "actual": "",
    }

    def step(n, desc, ok, detail=""):
        steps.append({"n": n, "desc": desc, "ok": ok, "detail": detail})
        _log(f"Step{n}: {desc} → {detail}", "STEP" if ok else "FAIL")
        return ok

    print("\n" + "=" * 50)
    print("  [IT-01] 已发送集成测试（深度=3）")
    print("=" * 50)

    # Step 1
    step(1, "确认已登录", True, "已登录")

    # Step 2
    nav.reset_folder()
    ok2 = nav.navigate("sent")
    cnt = nav.count_emails() if ok2 else 0
    step(2, "进入已发送", ok2, f"邮件数={cnt}")

    if not ok2:
        result["actual"] = "导航已发送失败"
        return result

    if cnt == 0:
        step(3, "打开邮件", True, "已发送为空，边界情况跳过")
        result["actual"] = "已发送为空，集成路径为空箱边界情况"
        result["passed"] = True
        return result

    # Step 3
    subj = nav.get_first_subject()
    ok3 = selector.open_first()
    step(3, "打开第一封邮件", ok3, f"主题={subj[:25]}")

    if ok3:
        driver.get(f"{MAIN_JSP}?sid={sid}&hl=zh_CN")
        time.sleep(2)

    # 截图
    try:
        p = os.path.join(SCREENSHOT_DIR, f"it01_{time.strftime('%H%M%S')}.png")
        driver.save_screenshot(p)
        _log(f"截图: {p}")
    except Exception:
        pass

    result["passed"] = ok3
    result["actual"] = f"邮件打开{'成功' if ok3 else '失败'}"
    return result


def main():
    print("=" * 60)
    print("  已发送集成测试 — sent_integration.py")
    print("  IT-01: 登录→已发送→查看邮件详情")
    print("  （自包含，自动登录，无需预先启动浏览器）")
    print("=" * 60)

    driver = None
    try:
        _log("启动 Edge 浏览器...")
        driver = _create_driver()
        sid = _login(driver)

        if not sid:
            _log("登录失败，测试终止", "FAIL")
            return

        result = run_it01(driver, sid)

        # 输出结果
        print("\n" + "=" * 50)
        status = "[+] PASS" if result["passed"] else "[-] FAIL"
        print(f"  {status}  [{result['id']}] {result['name']}")
        print(f"  实际结果: {result['actual']}")
        print("\n  步骤详情:")
        for s in result.get("steps", []):
            icon = "✓" if s["ok"] else "✗"
            print(f"    Step{s['n']}: {s['desc']} {icon}  {s.get('detail', '')}")
        print("=" * 50)

    except KeyboardInterrupt:
        _log("用户中断", "WARN")
    except Exception as e:
        _log(f"异常: {_short_err(e)}", "ERROR")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            _log("浏览器保持打开，按回车键关闭...")
            input()
            try:
                driver.quit()
            except Exception:
                pass
            _log("浏览器已关闭")


if __name__ == "__main__":
    main()
