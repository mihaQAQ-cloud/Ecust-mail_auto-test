"""
第三层：附件添加测试（支持正确格式 + 错误格式，期望错误格式上传失败）
功能：在写信页面中测试添加附件
  - 正确格式（png/txt/zip/pptx/html）：期望上传成功
  - 错误格式（bat/js）：期望上传被系统拒绝（失败）
附件路径: E:\软件质量保证与测试\自动化测试\resource\
命名规则: {格式}_test{编号}.{格式}，例如 png_test01.png
"""

import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_test import BaseTest

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class AttachmentTest(BaseTest):
    def __init__(self):
        super().__init__("attachment_test")
        # 附件基础路径
        self.attachment_dir = os.path.abspath(fr"resource")

        # ========== 正确格式：期望上传成功 ==========
        self.default_specs = [
            ("png", "01"),
            ("txt", "01"),
            ("zip", "01"),
            ("pptx", "01"),
            ("html", "01"),
        ]

        # ========== 错误格式：期望上传失败（被系统拒绝） ==========
        self.invalid_specs = [
            ("bat", "01"),   # 批处理文件
            ("js", "01"),    # JavaScript 文件
        ]

        # 用户指定的附件路径列表（可自定义）
        self.specified_files = []
        # 用户指定的错误格式附件路径列表（可自定义）
        self.specified_invalid_files = []

        # 开关：是否测试错误格式
        self.test_invalid = True

    def run(self):
        """主入口：运行正确格式测试 + 错误格式测试"""
        self.init_log()
        self.log("=" * 60)
        self.log("第三层：附件添加测试（正确格式 + 错误格式）")
        self.log("=" * 60)
        self.log(f"附件目录: {self.attachment_dir}")

        if not self.connect_browser():
            self.close()
            return False


        # ---------- 测试正确格式（期望成功） ----------
        self.log("\n" + "=" * 60)
        self.log("【阶段一】测试正确格式附件（期望: 上传成功）")
        self.log("=" * 60)

        if self.specified_files:
            self.log(f"[*] 使用指定正确附件列表，共 {len(self.specified_files)} 个")
            valid_result = self.test_specified_attachments(self.specified_files)
        else:
            self.log("[*] 使用默认正确附件规格列表 (png/txt/zip/pptx/html)")
            valid_result = self.test_default_attachments()

        # ---------- 测试错误格式（期望失败） ----------
        invalid_result = True
        if self.test_invalid:
            self.log("\n" + "=" * 60)
            self.log("【阶段二】测试错误格式附件（期望: 上传被系统拒绝）")
            self.log("=" * 60)

            if self.specified_invalid_files:
                self.log(f"[*] 使用指定错误附件列表，共 {len(self.specified_invalid_files)} 个")
                invalid_result = self.test_invalid_attachments(self.specified_invalid_files)
            else:
                self.log("[*] 使用默认错误附件规格列表 (bat/js)")
                invalid_result = self.test_default_invalid_attachments()
        else:
            self.log("\n[*] 跳过错误格式测试(test_invalid=False)")

        # ---------- 汇总 ----------
        self.log("\n" + "=" * 60)
        self.log("【测试汇总】")
        self.log("=" * 60)
        self.log(f"正确格式测试: {'PASS' if valid_result else 'FAIL'}", "PASS" if valid_result else "FAIL")
        self.log(f"错误格式测试: {'PASS' if invalid_result else 'FAIL'}", "PASS" if invalid_result else "FAIL")

        overall = valid_result and invalid_result
        self.log(f"总测试结果: {'PASS' if overall else 'FAIL'}", "PASS" if overall else "FAIL")

        self.close()
        return overall

    # ==================== 指定附件接口 ====================

    def set_specified_files(self, file_list):
        """设置用户指定的正确附件路径列表"""
        self.specified_files = file_list
        self.log(f"已设置指定正确附件: {len(file_list)} 个")

    def add_specified_file(self, filepath):
        """添加单个正确附件到列表"""
        self.specified_files.append(filepath)
        self.log(f"已添加指定正确附件: {os.path.basename(filepath)}")

    def set_specified_invalid_files(self, file_list):
        """设置用户指定的错误附件路径列表"""
        self.specified_invalid_files = file_list
        self.log(f"已设置指定错误附件: {len(file_list)} 个")

    def add_specified_invalid_file(self, filepath):
        """添加单个错误附件到列表"""
        self.specified_invalid_files.append(filepath)
        self.log(f"已添加指定错误附件: {os.path.basename(filepath)}")

    def set_test_invalid(self, flag):
        """设置是否测试错误格式(True=测试,False=跳过)"""
        self.test_invalid = flag
        self.log(f"错误格式测试开关: {flag}")

    # ==================== 正确格式测试 ====================

    def test_specified_attachments(self, file_list):
        """测试用户指定的正确附件列表（逐个上传，期望成功）"""
        self.log(f"\n[*] 开始测试指定正确附件列表")
        all_pass = True
        for filepath in file_list:
            if not os.path.exists(filepath):
                self.log(f"文件不存在，跳过: {filepath}", "FAIL")
                all_pass = False
                continue
            result = self.upload_single_file(filepath, expect_success=True)
            if not result:
                all_pass = False
            time.sleep(1)
        return all_pass

    def test_default_attachments(self):
        """测试默认的 4 种正确格式附件（期望成功）"""
        self.log(f"\n[*] 开始测试默认正确附件规格")
        all_pass = True
        for fmt, num in self.default_specs:
            filename = f"{fmt}_test{num}.{fmt}"
            filepath = os.path.join(self.attachment_dir, filename)
            result = self.upload_single_file(filepath, expect_success=True)
            if not result:
                all_pass = False
            time.sleep(1)
        return all_pass

    # ==================== 错误格式测试（期望失败） ====================

    def test_default_invalid_attachments(self):
        """测试默认错误格式附件（期望被系统拒绝）"""
        self.log(f"\n[*] 开始测试默认错误附件规格")
        all_pass = True
        for fmt, num in self.invalid_specs:
            filename = f"{fmt}_test{num}.{fmt}"
            filepath = os.path.join(self.attachment_dir, filename)
            result = self.upload_invalid_file(filepath)
            if not result:
                all_pass = False
            time.sleep(1)
        return all_pass

    def test_invalid_attachments(self, file_list):
        """测试用户指定的错误附件列表（期望被系统拒绝）"""
        self.log(f"\n[*] 开始测试指定错误附件列表")
        all_pass = True
        for filepath in file_list:
            if not os.path.exists(filepath):
                self.log(f"文件不存在，跳过: {filepath}", "FAIL")
                all_pass = False
                continue
            result = self.upload_invalid_file(filepath)
            if not result:
                all_pass = False
            time.sleep(1)
        return all_pass

    # ==================== 核心上传方法 ====================

    def upload_single_file(self, filepath, expect_success=True):
        """
        上传单个文件并验证
        :param expect_success: True=期望成功, False=期望失败
        """
        filename = os.path.basename(filepath)
        expect_str = "期望成功" if expect_success else "期望失败"
        self.log(f"\n[*] 上传附件: {filename} ({expect_str})")
        self.log(f"[*] 完整路径: {filepath}")

        if not os.path.exists(filepath):
            self.log(f"附件文件不存在: {filepath}", "FAIL")
            return False

        file_input = self.find_file_input()
        if not file_input:
            return False

        # 记录上传前的附件数量
        attach_count_before = self.count_attachments()
        self.log(f"[*] 上传前附件数量: {attach_count_before}")

        try:
            file_input.send_keys(filepath)
            self.log(f"已发送文件路径到 input", "PASS")
            time.sleep(2)

            # 检测是否有错误弹窗
            error_dialog = self.check_error_dialog()
            if error_dialog:
                self.log(f"检测到弹窗: {error_dialog}")
                # 无论期望成功还是失败，都先尝试关闭弹窗
                dismissed = self.dismiss_error_dialog()
                if not dismissed:
                    self.log("弹窗关闭失败，可能影响后续测试", "WARN")

                if expect_success:
                    self.log(f"上传成功格式却弹出错误弹窗: {error_dialog}", "FAIL")
                    return False
                else:
                    self.log(f"错误格式被系统正确拒绝: {error_dialog}", "PASS")
                    return True

            # 检查附件列表
            uploaded = self.verify_attachment_uploaded(filename)
            attach_count_after = self.count_attachments()
            self.log(f"[*] 上传后附件数量: {attach_count_after}")

            if expect_success:
                if uploaded:
                    self.log(f"正确格式上传成功: {filename}", "PASS")
                    return True
                else:
                    self.log(f"正确格式上传后未在页面找到: {filename}", "FAIL")
                    return False
            else:
                # 期望失败的情况
                if uploaded:
                    self.log(f"错误格式居然上传成功了（系统未拦截）: {filename}", "FAIL")
                    return False
                else:
                    self.log(f"错误格式被系统正确拦截: {filename}", "PASS")
                    return True

        except Exception as e:
            self.log(f"附件上传异常: {str(e)[:100]}", "ERROR")
            return False

    def upload_invalid_file(self, filepath):
        """上传错误格式文件（期望被系统拒绝）"""
        return self.upload_single_file(filepath, expect_success=False)

    def upload_multiple_files(self, file_list):
        """批量上传多个附件（利用 input 的 multiple 属性）"""
        self.log(f"\n[*] 批量上传 {len(file_list)} 个附件")
        valid_files = [f for f in file_list if os.path.exists(f)]
        if not valid_files:
            self.log("没有有效的附件文件", "FAIL")
            return False

        files_string = "\n".join(valid_files)
        file_input = self.find_file_input()
        if not file_input:
            return False

        try:
            file_input.send_keys(files_string)
            self.log(f"已批量发送 {len(valid_files)} 个文件路径", "PASS")
            time.sleep(3)

            all_pass = True
            for filepath in valid_files:
                filename = os.path.basename(filepath)
                if not self.verify_attachment_uploaded(filename):
                    all_pass = False
            return all_pass
        except Exception as e:
            self.log(f"批量上传失败: {str(e)[:100]}", "ERROR")
            return False

    # ==================== 弹窗检测与处理 ====================

    def check_error_dialog(self):
        """
        检测是否有错误/警告弹窗
        返回弹窗文本内容，没有则返回 None
        """
        dialog_indicators = [
            # === 附件上传提示弹窗（华理邮箱特定） ===
            "//*[contains(text(),'附件上传提示')]",
            "//*[contains(text(),'您选择的文件不能上传')]",
            "//*[contains(text(),'文件类型受限')]",
            "//*[contains(text(),'不能上传')]",
            # === 通用错误提示 ===
            "//*[contains(text(),'不支持')]",
            "//*[contains(text(),'无法上传')]",
            "//*[contains(text(),'文件类型')]",
            "//*[contains(text(),'格式错误')]",
            "//*[contains(text(),'附件大小')]",
            "//*[contains(text(),'上传失败')]",
            "//*[contains(text(),'不允许')]",
            "//*[contains(text(),'危险文件')]",
            "//*[contains(text(),'安全')]",
            "//div[contains(@class,'error')]",
            "//div[contains(@class,'warn')]",
            "//div[contains(@class,'dialog')]//div[contains(@class,'icon')]",
            "//div[contains(@class,'msgbox')]",
        ]

        for xpath in dialog_indicators:
            try:
                elem = self.driver.find_element(By.XPATH, xpath)
                if elem.is_displayed():
                    text = elem.text or elem.get_attribute("textContent") or ""
                    text = text.strip()[:50]
                    return text
            except:
                continue
        return None

    def dismiss_error_dialog(self):
        """关闭错误弹窗（点击确定/关闭按钮）"""
        dismiss_strategies = [
            # === 策略1: 华理邮箱附件上传提示弹窗的"确定"按钮（最高优先级） ===
            # 根据截图: nui-msgbox-ft-btns > div[role="button"].nui-mainBtn > span.nui-btn-text: "确 定"
            (By.XPATH, "//div[contains(@class,'nui-msgbox-ft-btns')]//div[contains(@class,'nui-mainBtn') and @role='button']//span[contains(text(),'确') and contains(text(),'定')]/parent::div[@role='button']"),
            (By.XPATH, "//div[contains(@class,'nui-msgbox-ft-btns')]//div[contains(@class,'nui-mainBtn') and @role='button']"),
            (By.XPATH, "//div[contains(@class,'nui-msgbox-ft-btns')]//div[@role='button' and contains(.,'确') and contains(.,'定')]"),
            (By.XPATH, "//div[contains(@class,'nui-msgbox-ft-btns')]//span[contains(text(),'确') and contains(text(),'定')]"),

            # === 策略2: 通用 msgbox 弹窗内的确定按钮 ===
            (By.XPATH, "//div[contains(@class,'msgbox')]//div[contains(@class,'nui-mainBtn') and @role='button']"),
            (By.XPATH, "//div[contains(@class,'msgbox')]//div[@role='button' and contains(.,'确') and contains(.,'定')]"),

            # === 策略3: 通用 dialog 弹窗 ===
            (By.XPATH, "//div[contains(@class,'dialog')]//div[@role='button' and contains(.,'确') and contains(.,'定')]"),
            (By.XPATH, "//div[contains(@class,'dialog')]//button[contains(text(),'确定')]"),
            (By.XPATH, "//div[contains(@class,'dialog')]//span[contains(text(),'关闭')]/parent::*"),
            (By.XPATH, "//div[contains(@class,'dialog')]//a[contains(text(),'关闭')]"),
            (By.XPATH, "//div[contains(@class,'dialog')]//div[contains(@class,'close')]"),

            # === 策略4: 终极兜底 —— 页面中所有包含"确"+"定"的可见 role=button ===
            (By.XPATH, "//div[@role='button' and contains(.,'确') and contains(.,'定') and not(contains(.,'取消'))]"),
            (By.XPATH, "//span[contains(text(),'确') and contains(text(),'定')]/ancestor::div[@role='button'][1]"),
        ]

        for i, (by, val) in enumerate(dismiss_strategies, 1):
            try:
                candidates = self.driver.find_elements(by, val)
                for btn in candidates:
                    if btn.is_displayed():
                        text = btn.text or btn.get_attribute("textContent") or ""
                        text = text.replace("\n", "").replace("\t", "").strip()
                        # 确保是"确定"按钮而不是其他（如"取消"）
                        if "确" in text and "定" in text and "取消" not in text and len(text) <= 6:
                            self.log(f"找到弹窗确定按钮（策略{i}）: text='{text}', class={btn.get_attribute('class')[:50]}")
                            self.safe_click(btn, "弹窗'确定'按钮")
                            time.sleep(1)
                            return True
            except Exception:
                continue

        # 尝试 ESC 关闭
        try:
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            self.log("已按 ESC 关闭弹窗")
            return True
        except:
            pass

        self.log("未能关闭弹窗", "ERROR")
        return False

    def safe_click(self, element, desc="元素"):
        """安全点击封装"""
        try:
            element.click()
            self.log(f"已点击{desc}（普通点击）", "PASS")
            return True
        except:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                self.log(f"已点击{desc}(JS 点击)", "PASS")
                return True
            except:
                return False

    # ==================== 元素查找与验证 ====================

    def find_file_input(self):
        """查找附件上传的 <input type='file'> 元素"""
        strategies = [
            (By.XPATH, "//div[@title='点击添加附件']//input[@type='file']"),
            (By.XPATH, "//div[contains(@class,'attachBrowser')]//input[@type='file']"),
            (By.XPATH, "//div[contains(@id,'attachBrowser')]//input[@type='file']"),
            (By.XPATH, "//input[@type='file']"),
            (By.CSS_SELECTOR, "input[type='file']"),
            (By.XPATH, "//*[contains(text(),'添加附件') or contains(text(),'附件')]//following::input[@type='file'][1]"),
        ]
        for i, (by, val) in enumerate(strategies, 1):
            try:
                file_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((by, val))
                )
                tag = file_input.tag_name
                input_type = file_input.get_attribute("type")
                class_attr = file_input.get_attribute("class") or ""
                self.log(f"  找到文件上传 input: tag={tag}, type={input_type}, class={class_attr[:50]}")
                return file_input
            except:
                continue
        self.log("未找到文件上传 input 元素", "FAIL")
        return None

    def count_attachments(self):
        """统计当前页面附件数量"""
        try:
            attach_items = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class,'attach') or contains(@class,'attachment')]//div[contains(@class,'item')] | "
                "//div[contains(@class,'attach') or contains(@class,'attachment')]//span[contains(@class,'name')]"
            )
            return len(attach_items)
        except:
            return 0

    def verify_attachment_uploaded(self, filename):
        """验证附件是否已添加到页面中"""
        time.sleep(2)
        check_strategies = [
            (By.XPATH, f"//*[contains(text(),'{filename}')]"),
            (By.XPATH, f"//span[contains(text(),'{filename}')]"),
            (By.XPATH, f"//div[contains(text(),'{filename}')]"),
            (By.XPATH, f"//a[contains(text(),'{filename}')]"),
        ]
        for by, val in check_strategies:
            try:
                elem = self.driver.find_element(by, val)
                if elem.is_displayed():
                    return True
            except:
                continue
        # 兜底：检查附件列表区域
        try:
            attach_area = self.driver.find_element(
                By.XPATH,
                "//div[contains(@class,'attach') or contains(@class,'attachment') or contains(@id,'attach')]"
            )
            if attach_area.is_displayed():
                return True
        except:
            pass
        return False


def main():
    tester = AttachmentTest()

    # ========== 用户自定义配置示例 ==========

    # 方式1: 指定正确附件列表
    # tester.set_specified_files([
    #     r"E:\软件质量保证与测试\自动化测试\resource\png_test01.png",
    #     r"E:\软件质量保证与测试\自动化测试\resource\txt_test01.txt",
    # ])

    # 方式2: 指定错误附件列表
    # tester.set_specified_invalid_files([
    #     r"E:\软件质量保证与测试\自动化测试\resource\exe_test01.exe",
    #     r"E:\软件质量保证与测试\自动化测试\resource\bat_test01.bat",
    # ])

    # 方式3: 关闭错误格式测试（只测正确格式）
    # tester.set_test_invalid(False)

    # 方式4: 使用默认配置（正确4种 + 错误4种）
    tester.run()


if __name__ == "__main__":
    main()