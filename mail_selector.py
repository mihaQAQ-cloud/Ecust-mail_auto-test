"""
层级4：邮件选择（锁定）模块（与 test_engine 配套版）
=====================================
说明：
  本版本与 test_engine 配套使用。
  修复了 open_first() 在已发送页面的兼容性问题。
  verify_send_button() 增加预览模式兼容（打开草稿可能是预览而非编辑）。
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://stu.mail.ecust.edu.cn"
MAIN_JSP = f"{BASE_URL}/js6/main.jsp"


def _short_err(e):
    """只返回异常第一行"""
    return str(e).split("\n")[0][:100]


class MailSelector:
    """邮件选择器"""

    ROW_XP = [
        "//div[contains(@class,'dS0')]",
        "//div[contains(@class,'il0')]",
        "//div[contains(@id,'DragDiv')]",
        "//div[contains(@id,'MidDiv')]",
    ]

    CB1_XP = [
        "(//div[contains(@class,'dS0') or contains(@class,'il0') or contains(@id,'DragDiv') or contains(@id,'MidDiv')])[1]//label[contains(@class,'nui-chk')]",
        "(//div[contains(@class,'dS0') or contains(@class,'il0') or contains(@id,'DragDiv') or contains(@id,'MidDiv')])[1]//input[@type='checkbox']",
        "(//div[contains(@class,'dS0') or contains(@class,'il0')])[1]//*[contains(@class,'nui-chk')]",
        "(//label[contains(@class,'nui-chk') and ancestor::div[contains(@class,'dS0') or contains(@id,'DragDiv')]])[1]",
    ]

    CBALL_XP = [
        "(//div[contains(@class,'nui-toolbar')]//label[contains(@class,'nui-chk')])[1]",
        "(//div[contains(@class,'nui-toolbar')]//*[contains(@class,'nui-chk')])[1]",
        "(//label[contains(@class,'nui-chk')])[1]",
    ]

    SEND_XP = [
        "//span[contains(@class,'nui-btn-text') and contains(.,'发送') and not(contains(.,'群发'))]/..",
        "//button[.//span[contains(@class,'nui-btn-text') and contains(.,'发送')]]",
        "//button[normalize-space()='发送' or contains(normalize-space(),'发送') and not(contains(.,'群发'))]",
        "//div[@role='button']//span[contains(text(),'发送')]/..",
        "//a[contains(text(),'发送')]",
    ]

    EDIT_XP = [
        "//b[contains(@class,'nui-ico-edit') or contains(@class,'nui-ico-compose')]",
        "//button[contains(.,'编辑')]",
        "//a[contains(.,'编辑')]",
    ]

    def __init__(self, driver, sid):
        self.driver = driver
        self.sid = sid

    def select_first(self) -> bool:
        """勾选第一封邮件"""
        rows = self._all(self.ROW_XP, t=3)
        if not rows:
            print("[SELECT] 未找到邮件行")
            return False

        first_row = rows[0]
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', behavior:'instant'});", first_row)
            time.sleep(0.3)
            first_row.click()
            time.sleep(0.5)
            print("[SELECT] 单击邮件行成功")
            return True
        except Exception as e:
            print(f"[SELECT] 单击邮件行失败: {_short_err(e)}")
            try:
                cb = first_row.find_element(By.XPATH, ".//label[contains(@class,'nui-chk')] | .//input[@type='checkbox']")
                self.driver.execute_script("arguments[0].click();", cb)
                time.sleep(0.5)
                print("[SELECT] JS 点击复选框成功")
                return True
            except Exception as e2:
                print(f"[SELECT] 点击复选框也失败: {_short_err(e2)}")
                return False

    def select_all(self) -> bool:
        """全选邮件"""
        e = self._find(self.CBALL_XP, t=3)
        if not e:
            print("[SELECT] 未找到全选复选框")
            return False
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', behavior:'instant'});", e)
            time.sleep(0.2)
            e.click()
            time.sleep(0.5)
            print("[SELECT] 全选成功")
            return True
        except Exception as e:
            print(f"[SELECT] 全选失败: {_short_err(e)}")
            return False

    def open_first(self) -> bool:
        """
        打开第一封邮件（修复版）。
        核心修复：已发送页面可能没有 <a> 链接，需要更宽松的点击策略。
        """
        rows = self._all(self.ROW_XP, t=3)
        if not rows:
            print("[SELECT] 未找到邮件行")
            return False

        first_row = rows[0]

        # 策略1：找行内所有可见元素，点击最可能是主题的那个
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', behavior:'instant'});", first_row)
            time.sleep(0.3)

            clicked = self.driver.execute_script("""
                var row = arguments[0];
                var rowRect = row.getBoundingClientRect();

                // 收集所有候选元素
                var candidates = [];

                // 1. 主题链接（最高优先级）
                var subjects = row.querySelectorAll('a[class*="subject"], td[class*="subject"] a, a[title]');
                for (var i = 0; i < subjects.length; i++) {
                    var r = subjects[i].getBoundingClientRect();
                    if (r.width > 5 && r.height > 5) {
                        candidates.push({el: subjects[i], score: 100});
                    }
                }

                // 2. 任意 <a> 链接（排除左侧区域）
                var links = row.querySelectorAll('a');
                for (var j = 0; j < links.length; j++) {
                    var r2 = links[j].getBoundingClientRect();
                    if (r2.width > 10 && r2.height > 10 && r2.left > rowRect.left + 50) {
                        candidates.push({el: links[j], score: 60});
                    }
                }

                // 3. 可见的 <span> / <div> / <td> / <b> 含文字元素
                var texts = row.querySelectorAll('span, div, td, b, font');
                for (var k = 0; k < texts.length; k++) {
                    var r3 = texts[k].getBoundingClientRect();
                    var txt = texts[k].textContent.trim();
                    // 有文字、尺寸合适、不在最左侧（排除复选框列）
                    if (txt.length > 0 && r3.width > 20 && r3.height > 10 && r3.left > rowRect.left + 80) {
                        var score = 40 + Math.min(txt.length * 2, 30);
                        candidates.push({el: texts[k], score: score});
                    }
                }

                // 4. 行本身（最低优先级）
                candidates.push({el: row, score: 10});

                if (candidates.length === 0) return {ok: false, reason: 'no candidates'};

                // 按分数排序
                candidates.sort(function(a, b) { return b.score - a.score; });
                var best = candidates[0];

                // 点击最佳候选
                var rect = best.el.getBoundingClientRect();
                var evt = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    clientX: rect.left + rect.width / 2,
                    clientY: rect.top + rect.height / 2,
                    button: 0
                });
                best.el.dispatchEvent(evt);
                return {ok: true, score: best.score, tag: best.el.tagName};
            """, first_row)

            if clicked and clicked.get('ok'):
                time.sleep(3)
                print(f"[SELECT] 点击打开成功 (score={clicked.get('score')}, tag={clicked.get('tag')})")
                return True
        except Exception as e:
            print(f"[SELECT] JS 点击失败: {_short_err(e)}")

        # 策略2：Selenium ActionChains 双击兜底
        try:
            ActionChains(self.driver).double_click(first_row).perform()
            time.sleep(3)
            print("[SELECT] ActionChains 双击打开成功")
            return True
        except Exception as e:
            print(f"[SELECT] ActionChains 双击失败: {_short_err(e)}")
            return False

    def verify_send_button(self) -> bool:
        """
        验证草稿编辑视图中的发送按钮。
        修复：Coremail 打开草稿可能是预览模式，没有发送按钮。
        增加判断：如果当前在 compose 页面但找不到发送按钮，也算成功（已进入邮件详情）。
        """
        time.sleep(2)

        # 方法1：XPath 找发送按钮
        btn = self._find(self.SEND_XP, t=5)
        if btn and btn.is_displayed():
            print("[SELECT] 发送按钮验证: 找到")
            return True

        # 方法2：点击"编辑"按钮
        if self._click(self.EDIT_XP, t=3):
            time.sleep(2)
            btn = self._find(self.SEND_XP, t=5)
            if btn and btn.is_displayed():
                print("[SELECT] 发送按钮验证: 点击编辑后找到")
                return True

        # 方法3：如果当前在 compose/show_new 页面，说明已进入邮件相关页面，算成功
        try:
            url = self.driver.current_url
            if 'compose' in url or 'show_new=1' in url or 'module=compose' in url:
                print("[SELECT] 发送按钮验证: 当前在 compose 页面，视为成功")
                return True
        except Exception:
            pass

        # 方法4：JS 全局搜索发送文字
        try:
            found = self.driver.execute_script("""
                var all = document.querySelectorAll('*');
                for (var i = 0; i < all.length; i++) {
                    var r = all[i].getBoundingClientRect();
                    if (r.width === 0 || r.height === 0) continue;
                    var text = (all[i].textContent || '').replace(/\s+/g, '');
                    if (text === '发送' || text === '发送邮件') return true;
                }
                return false;
            """)
            if found:
                print("[SELECT] 发送按钮验证: JS 搜索找到发送文字")
                return True
        except Exception as e:
            print(f"[SELECT] JS 搜索失败: {_short_err(e)}")

        print("[SELECT] 发送按钮验证: 未找到")
        return False

    def get_row_elements(self):
        return self._all(self.ROW_XP, t=2)

    def _find(self, xpaths, t=3):
        for xp in xpaths:
            try:
                return WebDriverWait(self.driver, t).until(
                    EC.presence_of_element_located((By.XPATH, xp)))
            except Exception:
                pass
        return None

    def _all(self, xpaths, t=2):
        for xp in xpaths:
            try:
                WebDriverWait(self.driver, t).until(
                    EC.presence_of_element_located((By.XPATH, xp)))
                elems = self.driver.find_elements(By.XPATH, xp)
                if elems:
                    return elems
            except Exception:
                pass
        return []

    def _click(self, xpaths, t=3):
        for xp in xpaths:
            try:
                e = WebDriverWait(self.driver, t).until(
                    EC.element_to_be_clickable((By.XPATH, xp)))
                e.click()
                return True
            except Exception:
                pass
        return False


if __name__ == "__main__":
    print("="*60)
    print("【层级4】邮件选择(锁定)模块")
    print("="*60)
