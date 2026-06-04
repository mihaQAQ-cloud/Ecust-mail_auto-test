"""
第三层测试基类：提供公共的连接、日志、暂停功能
"""

import time
import json
import os
from selenium import webdriver
from selenium.webdriver.edge.options import Options

SESSION_FILE = "browser_session.json"
LOG_DIR = fr"result\log"
PIC_DIR = fr"result\pic"


class BaseTest:
    def __init__(self, test_name):
        self.test_name = test_name
        self.driver = None
        self.log_file = None
        self.log_fp = None
        self._closed = False  # 防止重复关闭

    def init_log(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, time.strftime(f"{self.test_name}_%Y%m%d_%H%M%S") + ".txt")
        self.log_fp = open(log_path, "w", encoding="utf-8")
        self.log_file = log_path
        self._closed = False
        self.log(f"日志文件: {log_path}")

    def log(self, msg, level="INFO"):
        timestamp = time.strftime("%H:%M:%S")
        prefix = {"INFO": "[*]", "PASS": "[+]", "FAIL": "[-]", "ERROR": "[!]", "WARN": "[?]"}
        line = f"{timestamp} {prefix.get(level, '[*]')} {msg}"
        print(line)
        if self.log_fp and not self.log_fp.closed:
            self.log_fp.write(line + "\n")
            self.log_fp.flush()


    def connect_browser(self):
        if not os.path.exists(SESSION_FILE):
            self.log("[-] 未找到会话文件，请先运行 single_login.py 和 compose_connect.py", "ERROR")
            return False

        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            session = json.load(f)

        debug_port = session.get("debug_port", 9223)

        options = Options()
        options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")

        try:
            self.driver = webdriver.Edge(options=options)
            self.log(f"[+] 成功连接到浏览器")
            self.log(f"[+] 当前页面: {self.driver.title}")
            return True
        except Exception as e:
            self.log(f"[-] 连接失败: {e}", "ERROR")
            return False

    def close(self):
        """安全关闭日志文件，防止重复关闭"""
        if self._closed:
            return
        self._closed = True
        if self.log_fp and not self.log_fp.closed:
            self.log("[*] 测试结束")
            self.log_fp.close()
            self.log_fp = None
        else:
            print("[*] 测试结束")