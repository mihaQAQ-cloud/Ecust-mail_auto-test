"""
第三层：正文输入测试
"""

import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_test import BaseTest

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


class TextTest(BaseTest):
    def __init__(self):
        super().__init__("text_test")

    def run(self):
        self.init_log()
        self.log("=" * 60)
        self.log("第三层：正文输入测试")
        self.log("=" * 60)

        if not self.connect_browser():
            self.close()
            return False

        result = self.test_content()
        self.log(f"\n测试结果: {'PASS' if result else 'FAIL'}", "PASS" if result else "FAIL")

        self.close()
        return result

    def test_content(self, value=None):
        if value is None:
            value = "这是一封由自动化测试工具发送的测试邮件。\n测试时间: " + time.strftime(fr"%Y-%m-%d %H:%M:%S")

        self.log(f"\n[*] 测试正文输入")

        # iframe 编辑器
        self.driver.switch_to.default_content()
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        self.log(f"发现 {len(iframes)} 个 iframe")

        for idx, iframe in enumerate(iframes):
            try:
                if not iframe.is_displayed():
                    continue
                self.driver.switch_to.frame(iframe)
                try:
                    body = self.driver.find_element(By.XPATH, "//body[@contenteditable='true'] | //body")
                    body.click()
                    time.sleep(0.3)
                    body.clear()

                    lines = value.split('\n')
                    for i, line in enumerate(lines):
                        if i > 0:
                            body.send_keys(Keys.RETURN)
                        body.send_keys(line)
                        time.sleep(0.1)

                    self.driver.switch_to.default_content()
                    self.log(f"正文输入成功(iframe {idx})", "PASS")
                    return True
                except Exception as e:
                    self.log(f"iframe {idx} 失败: {str(e)[:80]}", "WARN")
                self.driver.switch_to.default_content()
            except:
                self.driver.switch_to.default_content()
                continue

        self.log("所有正文输入方式失败", "FAIL")
        return False


def main():
    tester = TextTest()
    tester.run()


if __name__ == "__main__":
    main()