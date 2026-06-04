"""
第三层：发送按钮检测（修复版 v4）
修复内容：
1. 适配华理邮箱的 div[role="button"] 结构
2. 增加 JS 点击备选
3. 处理"无主题"确认弹窗 —— 修复"确 定"文字中间有空格的匹配问题
"""

import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_test import BaseTest

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ButtonTest(BaseTest):
    def __init__(self):
        super().__init__("button_test")

    def run(self):
        self.init_log()
        self.log("=" * 60)
        self.log("第三层：发送按钮检测")
        self.log("=" * 60)

        if not self.connect_browser():
            self.close()
            return False


        result = self.test_send_button(actually_send=True)
        self.log(f"\n检测结果: {'PASS' if result else 'FAIL'}", "PASS" if result else "FAIL")

        self.close()
        return result

    def dismiss_popup(self):
        """关闭可能的弹窗/遮挡层"""
        try:
            hide_btn = self.driver.find_element(By.XPATH, "//*[contains(text(),'隐藏选项')]")
            if hide_btn.is_displayed():
                hide_btn.click()
                time.sleep(0.5)
                self.log("已收起隐藏选项")
        except:
            pass

        try:
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.3)
        except:
            pass

    def safe_click(self, element, desc="元素"):
        """
        安全点击封装：先尝试普通点击，失败则用 JS 点击
        """
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

    def handle_no_subject_dialog(self):
        """
        处理"确定真的不需要写主题吗？"弹窗
        返回 True 表示处理了弹窗，False 表示没有弹窗或处理失败
        """
        # 先检测弹窗是否出现（最多等待 3 秒）
        dialog_text_found = False
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//*[contains(text(),'确定真的不需要写主题吗')] | //*[contains(text(),'不需要写主题')]"
                ))
            )
            dialog_text_found = True
            self.log("检测到无主题确认弹窗", "WARN")
        except Exception:
            return False

        if not dialog_text_found:
            return False

        # === v4 核心修复："确 定"中间有空格，改用同时包含"确"和"定"的匹配方式 ===
        confirm_btn = None
        confirm_strategies = [
            # 策略1: 华理邮箱特定结构 —— 匹配 "确 定"（带空格）
            # 使用 contains(text(),'确') and contains(text(),'定') 来兼容有空格的情况
            (By.XPATH, "//div[contains(@class,'nui-mainBtn') and @role='button']//span[contains(text(),'确') and contains(text(),'定')]/parent::div[@role='button']"),
            (By.XPATH, "//div[contains(@class,'nui-mainBtn') and @role='button']//span[contains(text(),'确') and contains(text(),'定')]"),
            (By.XPATH, "//div[contains(@class,'nui-mainBtn') and contains(.,'确') and contains(.,'定')]"),

            # 策略2: 通用 role=button 的 div 包含"确"和"定"
            (By.XPATH, "//div[@role='button' and contains(.,'确') and contains(.,'定')]"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'确') and contains(text(),'定')]/ancestor::div[@role='button'][1]"),

            # 策略3: 弹窗上下文内的确定按钮
            (By.XPATH, "//div[contains(@class,'dialog') or contains(@class,'popup') or contains(@class,'modal')]//div[@role='button' and contains(.,'确') and contains(.,'定')]"),

            # 策略4: 兜底 —— 同时包含"确"和"定"的任何可点击元素
            (By.XPATH, "//button[contains(text(),'确') and contains(text(),'定')]"),
            (By.XPATH, "//a[contains(text(),'确') and contains(text(),'定')]"),
            (By.XPATH, "//*[contains(text(),'确') and contains(text(),'定') and (@role='button' or self::button or self::a)]"),
            (By.XPATH, "//span[contains(text(),'确') and contains(text(),'定')]"),

            # 策略5: 终极兜底 —— 只用"确"字匹配（因为弹窗里"确"字只出现在"确定"按钮）
            (By.XPATH, "//div[@role='button' and contains(text(),'确')]"),
            (By.XPATH, "//button[contains(text(),'确')]"),
        ]

        for i, (by, val) in enumerate(confirm_strategies, 1):
            try:
                candidates = self.driver.find_elements(by, val)
                for candidate in candidates:
                    if candidate.is_displayed():
                        # 获取完整文字，过滤掉"取消"按钮
                        text = (candidate.text or candidate.get_attribute("textContent") or "").replace("\n", "").replace("\t", "").strip()
                        # 同时包含"确"和"定"，且不包含"取消"
                        if "确" in text and "定" in text and "取消" not in text:
                            # 额外检查：确保不是弹窗标题文字（通常标题很长，按钮文字很短）
                            if len(text) <= 6:  # "确定"或"确 定"都很短
                                confirm_btn = candidate
                                self.log(f"找到确定按钮(策略{i}): tag={candidate.tag_name}, class={candidate.get_attribute('class')[:50]}, text='{text}'")
                                break
                if confirm_btn:
                    break
            except Exception:
                continue

        # 如果 XPath 全部失败，使用 JS 终极兜底
        if not confirm_btn:
            self.log("XPath 策略全部失败，尝试 JS 终极兜底...", "WARN")
            try:
                # JS 遍历所有元素，找到同时包含"确"和"定"、不包含"取消"的可见可点击元素
                script = """
                    var allElements = document.querySelectorAll('div[role="button"], button, a');
                    for (var i = 0; i < allElements.length; i++) {
                        var el = allElements[i];
                        var text = (el.textContent || el.innerText || '').replace(/\s+/g, ' ').trim();
                        if (text.includes('确') && text.includes('定') && !text.includes('取消')) {
                            var rect = el.getBoundingClientRect();
                            if (rect.width > 20 && rect.height > 10 && rect.top > 0 && rect.left > 0) {
                                // 优先返回短文本的（按钮而不是标题）
                                if (text.length <= 6) {
                                    return el;
                                }
                            }
                        }
                    }
                    return null;
                """
                confirm_btn = self.driver.execute_script(script)
                if confirm_btn:
                    btn_text = confirm_btn.get_attribute("textContent") or ""
                    self.log(f"通过 JS 兜底找到确定按钮: text='{btn_text.strip()}'", "PASS")
            except Exception as js_err:
                self.log(f"JS 兜底失败: {js_err}", "ERROR")

        if confirm_btn:
            # 滚动到视口并点击
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", confirm_btn)
            time.sleep(0.3)
            clicked = self.safe_click(confirm_btn, "'确定'按钮")
            if clicked:
                time.sleep(2)
                return True
            else:
                return False
        else:
            self.log("未找到'确定'按钮，无法处理弹窗", "ERROR")
            return False

    def test_send_button(self, actually_send=False):
        self.log(f"\n[*] 测试发送按钮 (实际发送: {actually_send})")

        self.dismiss_popup()

        # 查找发送按钮的策略
        strategies = [
            (By.XPATH, "//div[contains(@class,'nui-mainBtn') and contains(@class,'nui-btn-hasIcon')]//span[contains(text(),'发送')]"),
            (By.XPATH, "//div[contains(@class,'nui-mainBtn') and @role='button']"),
            (By.XPATH, "//div[contains(@class,'nui-mainBtn')]//span[@class='nui-btn-text' and contains(text(),'发送')]"),
            (By.XPATH, "//div[@role='button' and contains(.,'发送')]"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'发送')]/ancestor::div[@role='button']"),
            (By.XPATH, "//b[contains(@class,'nui-ico-sent-white')]/ancestor::div[@role='button']"),
            (By.XPATH, "//b[contains(@class,'nui-ico-sent')]/ancestor::div[@role='button']"),
            (By.XPATH, "//div[contains(@class,'toolbar')]//button[contains(text(),'发送')]"),
            (By.XPATH, "//div[contains(@class,'header')]//button[contains(text(),'发送')]"),
            (By.XPATH, "//button[contains(@class,'send') and not(contains(@class,'dropdown'))]"),
            (By.XPATH, "//button[contains(text(),'发送')]"),
            (By.XPATH, "//span[contains(text(),'发送')]/parent::button"),
            (By.XPATH, "//a[contains(text(),'发送')]"),
            (By.CSS_SELECTOR, ".toolbar .send-btn"),
            (By.CSS_SELECTOR, ".header .send-btn"),
            (By.XPATH, "//*[contains(text(),'发送') and (@role='button' or self::button or self::a)]"),
        ]

        btn = None
        for i, (by, val) in enumerate(strategies, 1):
            try:
                self.log(f"  尝试 {i}/{len(strategies)}: {val[:60]}...")
                btn = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((by, val))
                )

                tag = btn.tag_name
                role = btn.get_attribute("role")
                class_attr = btn.get_attribute("class") or ""
                location = btn.location
                size = btn.size

                self.log(f"  找到元素: tag={tag}, role={role}, class={class_attr[:50]}")

                if location['y'] < 150:
                    self.log(f"  确认顶部发送按钮: location={location}, size={size}")
                    break
                else:
                    self.log(f"  找到按钮但位置偏下(y={location['y']}), 继续查找...")
                    btn = None
            except Exception as e:
                continue

        if not btn:
            self.log("未找到发送按钮", "FAIL")
            return False

        tag = btn.tag_name
        role = btn.get_attribute("role")
        class_attr = btn.get_attribute("class") or ""
        self.log(f"最终目标元素: tag={tag}, role={role}, class={class_attr[:60]}")
        self.log(f"按钮状态: displayed={btn.is_displayed()}, location={btn.location}")

        is_clickable = btn.is_displayed()

        if actually_send and is_clickable:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.3)

                clicked = self.safe_click(btn, "'发送'按钮")
                if not clicked:
                    return False

                time.sleep(2)

                # 处理"无主题"确认弹窗
                dialog_handled = self.handle_no_subject_dialog()
                if dialog_handled:
                    self.log("已处理无主题弹窗，继续检测发送结果")

                time.sleep(2)

                # 检查发送成功提示
                try:
                    success_indicators = [
                        "//*[contains(text(),'发送成功')]",
                        "//*[contains(text(),'邮件已发送')]",
                        "//div[contains(@class,'success')]",
                        "//*[contains(text(),'发送完成')]",
                    ]
                    for xpath in success_indicators:
                        try:
                            self.driver.find_element(By.XPATH, xpath)
                            self.log("检测到发送成功提示", "PASS")
                            break
                        except:
                            continue
                except:
                    pass

                return True
            except Exception as e:
                self.log(f"点击发送失败: {e}", "ERROR")
                return False
        else:
            if is_clickable:
                self.log("找到发送按钮且可点击，未点击（测试模式）", "PASS")
            else:
                self.log("找到发送按钮但不可点击", "FAIL")
            return is_clickable


def main():
    tester = ButtonTest()
    tester.run()


if __name__ == "__main__":
    main()