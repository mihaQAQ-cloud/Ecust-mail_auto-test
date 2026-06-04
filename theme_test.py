"""
第三层：主题输入测试
"""

import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_test import BaseTest

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ThemeTest(BaseTest):
    def __init__(self):
        super().__init__("theme_test")

    def run(self):
        self.init_log()
        self.log("=" * 60)
        self.log("第三层：主题输入测试")
        self.log("=" * 60)

        if not self.connect_browser():
            self.close()
            return False

        result = self.test_subject("自动化测试邮件")
        self.log(f"\n测试结果: {'PASS' if result else 'FAIL'}", "PASS" if result else "FAIL")

        self.close()
        return result

    def test_subject(self, value="自动化测试邮件"):
        self.log(f"\n[*] 测试主题输入: '{value}'")

        strategies = [
            (By.XPATH, "//input[contains(@placeholder,'主题')]"),
            (By.XPATH, "//input[@type='text' and (contains(@id,'subject') or contains(@name,'subject'))]"),
            (By.CSS_SELECTOR, "input[placeholder*='主题']"),
        ]

        elem = None
        for i, (by, val) in enumerate(strategies, 1):
            try:
                elem = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((by, val))
                )
                if elem.is_displayed():
                    break
                elem = None
            except:
                continue

        if not elem:
            self.log("未找到主题输入框", "FAIL")
            return False

        try:
            elem.clear()
            elem.send_keys(value)
            time.sleep(0.5)
            actual = elem.get_attribute("value")
            if actual == value:
                self.log(f"主题输入成功: {actual}", "PASS")
                return True
            else:
                self.log(f"输入不匹配", "FAIL")
                return False
        except Exception as e:
            self.log(f"主题输入失败: {e}", "ERROR")
            return False


def main():
    tester = ThemeTest()
    tester.run()


if __name__ == "__main__":
    main()