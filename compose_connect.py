"""
层级2：浏览器连接管理器 + 写信页面入口
职责：
  1. 连接层级1启动的浏览器（读取 browser_session.json）
  2. 提供统一的浏览器连接接口给层级3调用
  3. 提供写信/邮件撰写功能（被层级3在准备测试数据时调用）
"""

import time
import json
import os
import re
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SESSION_FILE = "browser_session.json"
BASE_URL = "https://stu.mail.ecust.edu.cn"
MAIN_JSP = f"{BASE_URL}/js6/main.jsp"


class BrowserConnector:
    """浏览器连接管理器（层级2核心类）"""

    _instance = None
    _driver = None
    _sid = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self):
        """连接到层级1启动的浏览器，返回 (driver, sid)"""
        if self._driver is not None:
            print("[L2] 复用已有浏览器连接")
            return self._driver, self._sid

        if not os.path.exists(SESSION_FILE):
            print("[-] 未找到 browser_session.json,请先运行层级1 (module1_login.py)")
            return None, ""

        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            session = json.load(f)

        debug_port = session.get("debug_port", 9223)
        self._sid = session.get("sid", "")

        options = Options()
        options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")

        try:
            self._driver = webdriver.Edge(options=options)
            print(f"[L2] 已连接浏览器 端口={debug_port}")
            return self._driver, self._sid
        except Exception as e:
            print(f"[-] 连接失败: {e}\n    请确认层级1仍在运行")
            return None, ""

    def get_driver(self):
        """获取当前浏览器驱动"""
        if self._driver is None:
            self.connect()
        return self._driver

    def get_sid(self):
        """获取当前会话ID"""
        return self._sid

    def disconnect(self):
        """断开连接（不关闭浏览器）"""
        self._driver = None
        self._sid = ""
        print("[L2] 已断开连接（浏览器保持运行）")


class ComposeManager:
    """写信页面管理器（层级2功能扩展）"""

    def __init__(self, connector: BrowserConnector):
        self.conn = connector
        self.driver = connector.get_driver()
        self.sid = connector.get_sid()
        self._self_email = self._detect_self_email()

    def _detect_self_email(self) -> str:
        """检测当前登录账号的邮箱地址"""
        try:
            for xp in ["//span[contains(text(),'@mail.ecust')]",
                       "//a[contains(text(),'@')]",
                       "//*[contains(@class,'user') and contains(text(),'@')]"]:
                elems = self.driver.find_elements(By.XPATH, xp)
                for e in elems:
                    txt = e.text.strip()
                    if "@" in txt and "ecust" in txt:
                        return txt
        except Exception:
            pass
        return "23013181@stu.ecust.edu.cn"

    def enter_compose(self):
        """进入写信页面"""
        compose_url = f"{MAIN_JSP}?sid={self.sid}&show_new=1&hl=zh_CN#module=compose.ComposeModule%7C%7B%7D"
        self.driver.get(compose_url)
        time.sleep(5)
        return "compose" in self.driver.current_url

    def _find_clickable(self, xpaths, t=5):
        for xp in xpaths:
            try:
                return WebDriverWait(self.driver, t).until(
                    EC.element_to_be_clickable((By.XPATH, xp)))
            except Exception:
                pass
        return None

    def _safe_input(self, elem, text: str):
        try:
            elem.click(); time.sleep(0.2)
            elem.clear()
            elem.send_keys(text)
        except Exception:
            try:
                self.driver.execute_script(
                    "arguments[0].value = arguments[1];"
                    "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));",
                    elem, text)
            except Exception:
                pass

    def write_mail(self, subject: str, save_as_draft: bool = False) -> bool:
        """
        写邮件并保存为草稿或发送
        被层级3调用以准备测试数据
        """
        if not self.enter_compose():
            return False

        # 收件人
        to_xp = ["//input[contains(@placeholder,'收件人')]",
                 "//div[contains(@class,'to')]//input[1]",
                 "//input[@id='toAddress']"]
        to_elem = self._find_clickable(to_xp, t=3)
        if not to_elem:
            self._click(["//span[normalize-space(text())='收件人']",
                        "//*[contains(text(),'收件人：') or contains(text(),'收件人:')]"], t=2)
            to_elem = self._find_clickable(to_xp, t=2)
        if to_elem:
            self._safe_input(to_elem, self._self_email)
            to_elem.send_keys(Keys.RETURN)
            time.sleep(0.5)

        # 主题
        subj_xp = ["//input[contains(@placeholder,'主题')]",
                   "//input[@id='subject' or @name='subject']"]
        subj_elem = self._find_clickable(subj_xp, t=5)
        if subj_elem:
            self._safe_input(subj_elem, subject)

        # 正文（iframe编辑器）
        body_ok = False
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    body.click()
                    body.send_keys("自动化测试内容")
                    self.driver.switch_to.default_content()
                    body_ok = True
                    break
                except Exception:
                    self.driver.switch_to.default_content()
        except Exception:
            pass

        time.sleep(0.5)

        if save_as_draft:
            save_xp = ["//button[normalize-space(text())='存草稿']",
                       "//span[normalize-space(text())='存草稿']/.."]
            ok = self._click(save_xp, t=5)
            if ok:
                time.sleep(4)
                # 返回草稿箱列表
                durl = f"{MAIN_JSP}?sid={self.sid}&hl=zh_CN#module=mbox.ListModule%7C%7B%22mbox%22%3A%22Drafts%22%7D"
                self.driver.get(durl)
                time.sleep(3)
            return ok
        else:
            send_xp = [
                "//span[contains(@class,'nui-btn-text') and contains(.,'发送') and not(contains(.,'群发'))]/..",
                "//button[normalize-space()='发送' or contains(normalize-space(),'发送') and not(contains(.,'群发'))]",
            ]
            ok = self._click(send_xp, t=5)
            if ok:
                time.sleep(1)
                try:
                    WebDriverWait(self.driver, 2).until(EC.alert_is_present())
                    self.driver.switch_to.alert.accept()
                except Exception:
                    pass
                time.sleep(2)
            # 返回主界面
            self.driver.get(f"{MAIN_JSP}?sid={self.sid}&hl=zh_CN")
            time.sleep(2)
            return ok

    def _click(self, xpaths, t=3):
        for xp in xpaths:
            try:
                e = WebDriverWait(self.driver, t).until(
                    EC.element_to_be_clickable((By.XPATH, xp)))
                e.click(); return True
            except Exception:
                pass
        return False


def get_connector() -> BrowserConnector:
    """获取浏览器连接器的单例"""
    return BrowserConnector()


if __name__ == "__main__":
    print("="*60)
    print("【层级2】浏览器连接测试")
    print("="*60)
    conn = get_connector()
    driver, sid = conn.connect()
    if driver:
        print(f"[+] 连接成功,当前URL: {driver.current_url[:60]}...")
        print(f"[+] SID: {sid[:20]}...")
    else:
        print("[-] 连接失败")
