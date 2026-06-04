"""
第三层：发送成功后返回写信页面
功能：在邮件发送成功页面，点击"继续写信"按钮返回写信页面
"""

import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_test import BaseTest

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ReturnWriteTest(BaseTest):
    def __init__(self):
        super().__init__("return_write")

    def run(self):
        self.init_log()
        self.log("=" * 60)
        self.log("第三层：发送成功后返回写信页面")
        self.log("=" * 60)

        if not self.connect_browser():
            self.close()
            return False

        result = self.return_to_compose()
        self.log(f"\n检测结果: {'PASS' if result else 'FAIL'}", "PASS" if result else "FAIL")

        self.close()
        return result

    def is_send_success_page(self):
        """检测当前是否是发送成功页面"""
        indicators = [
            "//*[contains(text(),'发送成功')]",
            "//*[contains(text(),'已成功发送到收件人')]",
            "//a[contains(text(),'继续写信')]",
            "//a[contains(text(),'返回收件箱')]",
            "//a[contains(text(),'查看已发邮件')]",
        ]
        found_count = 0
        for xpath in indicators:
            try:
                self.driver.find_element(By.XPATH, xpath)
                found_count += 1
            except:
                continue

        # 至少命中 2 个指标才认为是发送成功页面
        if found_count >= 2:
            self.log(f"当前为发送成功页面（命中 {found_count} 个指标）")
            return True
        else:
            self.log(f"当前不是发送成功页面（仅命中 {found_count} 个指标）")
            return False

    def safe_click(self, element, desc="元素"):
        """安全点击封装：先尝试普通点击，失败则用 JS 点击"""
        try:
            element.click()
            self.log(f"已点击{desc}（普通点击）", "PASS")
            return True
        except Exception as click_err:
            self.log(f"普通点击失败: {str(click_err)[:80]}，尝试 JS 点击...", "WARN")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                self.log(f"已点击{desc}(JS 点击)", "PASS")
                return True
            except Exception as js_err:
                self.log(f"JS 点击也失败: {js_err}", "ERROR")
                return False

    def return_to_compose(self):
        """点击'继续写信'按钮，返回写信页面"""
        self.log("\n[*] 开始返回写信页面流程")

        # Step 1: 确认当前是发送成功页面
        if not self.is_send_success_page():
            self.log("当前页面不是发送成功页面，尝试继续执行...", "WARN")

        # Step 2: 查找并点击"继续写信"按钮
        self.log("[*] 查找'继续写信'按钮...")

        continue_btn = None
        strategies = [
            # 策略1: 根据截图的 DOM 结构 —— class 包含 js-component-link + nui-ico 图标
            (By.XPATH, "//a[contains(@class,'js-component-link')]//b[contains(@class,'nui-ico')]/parent::a[contains(.,'继续写信')]"),
            (By.XPATH, "//a[contains(@class,'js-component-link') and contains(.,'继续写信')]"),

            # 策略2: 纯文字匹配
            (By.XPATH, "//a[contains(text(),'继续写信')]"),
            (By.XPATH, "//span[contains(text(),'继续写信')]/parent::a"),
            (By.XPATH, "//a[contains(.,'继续写信')]"),

            # 策略3: 图标+文字组合（兼容不同 class 名）
            (By.XPATH, "//a[.//b[contains(@class,'nui-ico')] and contains(.,'继续写信')]"),

            # 策略4: 兜底 —— 任何包含"继续写信"的可点击元素
            (By.XPATH, "//*[contains(text(),'继续写信') and (@role='button' or self::button or self::a)]"),
            (By.XPATH, "//span[contains(text(),'继续写信')]"),
        ]

        for i, (by, val) in enumerate(strategies, 1):
            try:
                self.log(f"  尝试 {i}/{len(strategies)}: {val[:60]}...")
                continue_btn = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((by, val))
                )
                if continue_btn.is_displayed():
                    tag = continue_btn.tag_name
                    class_attr = continue_btn.get_attribute("class") or ""
                    text = continue_btn.text or continue_btn.get_attribute("textContent") or ""
                    self.log(f"  找到元素: tag={tag}, class={class_attr[:50]}, text='{text.strip()}'")
                    break
                else:
                    continue_btn = None
            except Exception:
                continue

        if not continue_btn:
            self.log("未找到'继续写信'按钮", "FAIL")
            return False

        # Step 3: 点击按钮
        self.log("[*] 点击'继续写信'按钮...")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_btn)
        time.sleep(0.3)

        clicked = self.safe_click(continue_btn, "'继续写信'按钮")
        if not clicked:
            return False

        # Step 4: 等待页面跳转
        self.log("[*] 等待页面跳转...")
        time.sleep(3)

        # Step 5: 验证是否成功返回到写信页面
        return self.verify_compose_page()

    def verify_compose_page(self):
        """验证当前页面是否为写信页面"""
        self.log("[*] 验证是否成功返回写信页面...")

        compose_indicators = [
            "//*[contains(text(),'收件人')]",
            "//*[contains(text(),'主题')]",
            "//*[contains(text(),'发送')]",
            "//div[contains(@class,'compose')]",
            "//div[@contenteditable='true']",
            "//iframe",
            "//div[contains(@class,'nui-mainBtn') and contains(.,'发送')]",
        ]

        found_count = 0
        for xpath in compose_indicators:
            try:
                self.driver.find_element(By.XPATH, xpath)
                found_count += 1
            except:
                continue

        current_url = self.driver.current_url
        self.log(f"[*] 当前URL: {current_url[:80]}...")
        self.log(f"[*] 写信页面指标命中: {found_count}/{len(compose_indicators)}")

        # 命中至少 3 个指标，或 URL 包含 compose，即认为成功
        if found_count >= 3 or "compose" in current_url:
            self.log("成功返回写信页面", "PASS")
            return True
        else:
            self.log("未能确认已返回写信页面", "FAIL")
            return False


def main():
    tester = ReturnWriteTest()
    tester.run()


if __name__ == "__main__":
    main()