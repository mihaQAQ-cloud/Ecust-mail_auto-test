"""
草稿箱集成测试（IT-02）
流程：登录 → 进入草稿箱 → 打开第一封草稿 → 返回列表 → 验证数量一致
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
USERNAME = "********" #出于保密隐私，需自行修改账号密码
PASSWORD = "******"
DEBUG_PORT = 9224
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
        tempfile.gettempdir(), f"edge_draft_int_{int(time.time())}")
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


def run_it02(driver, sid):
    """IT-02: 登录→草稿箱→打开草稿→返回列表→验证数量"""
    nav = FolderNavigator(driver, sid)
    selector = MailSelector(driver, sid)

    steps = []
    result = {
        "id": "IT-02",
        "name": "登录→草稿箱→打开草稿→返回列表→验证数量",
        "depth": 4,
        "steps": steps,
        "passed": False,
        "actual": "",
    }

    def step(n, desc, ok, detail=""):
        steps.append({"n": n, "desc": desc, "ok": ok, "detail": detail})
        _log(f"Step{n}: {desc} → {detail}", "STEP" if ok else "FAIL")
        return ok

    print("\n" + "=" * 50)
    print("  [IT-02] 草稿箱集成测试（深度=4）")
    print("=" * 50)

    # Step 1
    step(1, "确认已登录", True, "已登录")

    # Step 2
    nav.reset_folder()
    ok2 = nav.navigate("drafts")
    cnt_before = nav.count_emails() if ok2 else 0
    step(2, "进入草稿箱", ok2, f"草稿数={cnt_before}")

    if not ok2:
        result["actual"] = "导航草稿箱失败"
        return result

    if cnt_before == 0:
        step(3, "打开草稿", True, "草稿箱为空，边界情况跳过")
        step(4, "返回列表验证", True, "跳过")
        result["actual"] = "草稿箱为空，集成路径为空箱边界情况"
        result["passed"] = True
        return result

    # Step 3
    ok3 = selector.open_first()
    step(3, "打开第一封草稿", ok3, "已打开" if ok3 else "失败")

    if not ok3:
        result["actual"] = "打开草稿失败"
        return result

    # Step 4
    time.sleep(1)
    nav.reset_folder()
    ok4 = nav.navigate("drafts")
    cnt_after = nav.count_emails() if ok4 else -1
    match = ok4 and (cnt_after == cnt_before)
    step(4, "返回列表验证数量", match,
         f"返回{'成功' if ok4 else '失败'}，数量 {cnt_before}→{cnt_after}")

    # 截图
    try:
        p = os.path.join(SCREENSHOT_DIR, f"it02_{time.strftime('%H%M%S')}.png")
        driver.save_screenshot(p)
        _log(f"截图: {p}")
    except Exception:
        pass

    result["passed"] = match
    result["actual"] = (
        f"集成流程完成，数量一致（{cnt_before} 封）"
        if match else
        f"数量不一致（{cnt_before}→{cnt_after}）"
    )
    return result


def main():
    print("=" * 60)
    print("  草稿箱集成测试 — draft_integration.py")
    print("  IT-02: 登录→草稿箱→打开草稿→返回列表→验证数量")
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

        result = run_it02(driver, sid)

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
