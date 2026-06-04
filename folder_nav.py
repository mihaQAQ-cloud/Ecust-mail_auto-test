"""
层级3：邮件文件夹导航模块
职责：
  1. 导航到草稿箱或已发送文件夹
  2. 统计邮件数量
  3. 检测文件夹是否为空
  4. 读取第一封邮件主题
  被层级4调用以进入特定文件夹
"""

import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://stu.mail.ecust.edu.cn"
MAIN_JSP = f"{BASE_URL}/js6/main.jsp"


class FolderNavigator:
    """文件夹导航器（层级3核心类）"""

    NAV = {
        "drafts": ["//span[normalize-space(text())='草稿箱']",
                   "//a[contains(normalize-space(text()),'草稿箱')]"],
        "sent":   ["//span[normalize-space(text())='已发送']",
                   "//a[normalize-space(text())='已发送']"],
    }
    NAV_ZH = {"drafts": "草稿箱", "sent": "已发送"}

    def __init__(self, driver, sid):
        self.driver = driver
        self.sid = sid
        self._current_folder = None

    def navigate(self, folder: str) -> bool:
        """
        导航到指定文件夹（drafts 或 sent）
        返回是否成功
        """
        if self._current_folder == folder:
            return True

        zh = self.NAV_ZH[folder]
        mbox = "Drafts" if folder == "drafts" else "Sent"
        print(f"[L3] 导航至【{zh}】...")

        # 若当前在写信/全屏写信页面，先返回主界面
        try:
            url = self.driver.current_url
            if any(k in url.lower() for k in ["compose", "show_new=1", "fullscreen"]):
                print("[L3] 检测到写信页面，先返回主界面...")
                self.driver.get(f"{MAIN_JSP}?sid={self.sid}&hl=zh_CN")
                time.sleep(3)
        except Exception:
            pass

        # 方式1：点击左侧导航
        self._click(self.NAV[folder], t=5)
        time.sleep(2.5)

        # 验证：列表工具栏出现
        TOOLBAR = ("//span[contains(@class,'nui-btn-text') and "
                   "(contains(.,'刷新') or contains(.,'删除草稿') or "
                   "normalize-space(.)='删除')]")
        toolbar_ok = False
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH, TOOLBAR)))
            toolbar_ok = True
        except Exception:
            pass

        # 方式2：URL直跳兜底
        if not toolbar_ok:
            print("[L3] 工具栏未就绪,URL直跳兜底...")
            self.driver.get(
                f"{MAIN_JSP}?sid={self.sid}&hl=zh_CN"
                f"#module=mbox.ListModule%7C%7B%22mbox%22%3A%22{mbox}%22%7D")
            time.sleep(3)

        self._current_folder = folder
        print(f"[L3] 【{zh}】加载成功")
        return True

    def get_current_folder(self):
        return self._current_folder

    def reset_folder(self):
        """重置当前文件夹标记（用于用例间隔离）"""
        self._current_folder = None

    def count_emails(self, wait_extra=False) -> int:
        """
        计算当前文件夹的邮件数量
        使用JS精确统计当前活动容器内的邮件行
        """
        if wait_extra:
            time.sleep(1.5)

        try:
            cnt = self.driver.execute_script("""
                var activeBtn = null;
                for (var s of document.querySelectorAll('span.nui-btn-text')) {
                    var r = s.getBoundingClientRect();
                    var txt = s.textContent.trim();
                    if (r.width > 0 && r.height > 0 && r.top >= 0 && r.top < window.innerHeight
                        && (txt === '删除草稿' || txt === '删除')) {
                        activeBtn = s; break;
                    }
                }
                if (activeBtn) {
                    var container = activeBtn.parentElement;
                    for (var i = 0; i < 25; i++) {
                        if (!container || container === document.body) break;
                        var rows = container.querySelectorAll(
                            'div[class*="il0"], div[id*="DragDiv"], div[id*="MidDiv"]');
                        if (rows.length > 0) {
                            var visible = 0;
                            for (var row of rows) {
                                var rr = row.getBoundingClientRect();
                                if (rr.width > 0 && rr.height > 10) visible++;
                            }
                            if (visible > 0) return visible;
                        }
                        container = container.parentElement;
                    }
                }
                var seen = new Set(); var total = 0;
                for (var sel of ['div[class*="il0"]','div[id*="DragDiv"]','div[id*="MidDiv"]']) {
                    for (var e of document.querySelectorAll(sel)) {
                        if (seen.has(e)) continue;
                        var r = e.getBoundingClientRect();
                        if (r.width > 0 && r.height > 10 && r.top >= 0
                            && r.top < window.innerHeight) { seen.add(e); total++; }
                    }
                }
                return total;
            """)
            if cnt > 0:
                return cnt
        except Exception:
            pass

        # 备用：is_displayed
        for xp in ["//div[contains(@class,'il0')]",
                     "//div[contains(@id,'DragDiv')]",
                     "//div[contains(@id,'MidDiv')]"]:
            try:
                elems = self.driver.find_elements(By.XPATH, xp)
                visible = [e for e in elems if e.is_displayed()]
                if visible:
                    return len(visible)
            except Exception:
                pass

        if wait_extra:
            time.sleep(1.5)
            return self.count_emails(wait_extra=False)
        return 0

    def is_empty(self) -> bool:
        """检测当前文件夹是否为空"""
        tips = self.driver.find_elements(By.XPATH,
            "//*[contains(.,'没有邮件') or contains(.,'暂无') or contains(.,'此文件夹为空')]")
        if tips and any(t.is_displayed() for t in tips):
            return True
        return self.count_emails() == 0

    def get_first_subject(self) -> str:
        """获取第一封邮件的主题"""
        for xp in ["(//tr[.//input[@type='checkbox']]//td[contains(@class,'subject')])[1]",
                   "(//td[contains(@class,'subject') or contains(@class,'title')])[1]"]:
            try:
                e = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, xp)))
                return e.text.strip()
            except Exception:
                pass
        return "(无主题)"

    def get_nav_count(self, folder_zh: str) -> int:
        """从左侧导航标签读取邮件数量"""
        try:
            for xp in [
                f"//span[starts-with(normalize-space(text()),'{folder_zh}')]",
                f"//a[starts-with(normalize-space(text()),'{folder_zh}')]",
            ]:
                elems = self.driver.find_elements(By.XPATH, xp)
                for e in elems:
                    txt = e.text.strip()
                    if txt.startswith(folder_zh):
                        m = re.search(r'\((\d+)\)', txt)
                        if m:
                            return int(m.group(1))
            return 0
        except Exception:
            return 0

    def _click(self, xpaths, t=3):
        for xp in xpaths:
            try:
                e = WebDriverWait(self.driver, t).until(
                    EC.element_to_be_clickable((By.XPATH, xp)))
                e.click(); return True
            except Exception:
                pass
        return False


if __name__ == "__main__":
    print("="*60)
    print("【层级3】文件夹导航模块")
    print("="*60)
    print("本模块需由层级2提供 driver 和 sid 后使用")
    print("示例：")
    print("  from compose_connect import get_connector")
    print("  from folder_nav import FolderNavigator")
    print("  conn = get_connector(); driver, sid = conn.connect()")
    print("  nav = FolderNavigator(driver, sid)")
    print("  nav.navigate('drafts')  # 进入草稿箱")
    print("  nav.navigate('sent')    # 进入已发送")
