"""
第三层：收件人输入测试
"""

import time
import os
import sys

# 添加当前目录到路径，导入基类
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from base_test import BaseTest
except ImportError:
    # 如果不用 base_test.py，可以把 BaseTest 类直接贴到这里
    class BaseTest:
        pass  # 简化版，实际使用时需要完整实现

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains


class RecipientTest(BaseTest):
    def __init__(self):
        super().__init__("recipient_test")

    def run(self):
        self.init_log()
        self.log("=" * 60)
        self.log("第三层：收件人输入测试")
        self.log("=" * 60)

        if not self.connect_browser():
            self.close()
            return False

        result = self.test_recipient("23070066@mail.ecust.edu.cn")
        self.log(f"\n测试结果: {'PASS' if result else 'FAIL'}", "PASS" if result else "FAIL")

        self.close()
        return result

    def test_recipient(self, value="23070066@mail.ecust.edu.cn"):
        self.log(f"\n[*] 测试收件人输入: '{value}'")

        try:
            label = self.driver.find_element(By.XPATH, "//*[contains(text(),'收件人')]")
            self.log(f"  找到标签: tag={label.tag_name}")

            container = label
            for i in range(3):
                parent = container.find_element(By.XPATH, "..")
                if parent.size['width'] > 300:
                    container = parent
                    break
                container = parent

            children = container.find_elements(By.XPATH, ".//*")
            target = None
            for child in children:
                try:
                    if "收件人" in (child.text or ""):
                        continue
                    if child.is_displayed() and child.size['width'] > 50 and child.size['height'] > 10:
                        if len(child.find_elements(By.XPATH, "./*")) < 3:
                            target = child
                            break
                except:
                    continue

            if target:
                target.click()
                time.sleep(0.5)
                try:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(target).click().pause(0.3).send_keys(value).perform()
                    self.log("收件人输入成功", "PASS")
                    return True
                except Exception as e:
                    self.log(f"ActionChains 失败: {str(e)[:80]}", "WARN")

            self.log("未找到合适的输入目标", "FAIL")
            return False

        except Exception as e:
            self.log(f"测试失败: {str(e)[:100]}", "ERROR")
            return False


def main():
    tester = RecipientTest()
    tester.run()


if __name__ == "__main__":
    main()