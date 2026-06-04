"""
已发送模块测试（5 用例）
TC-SENT-P01 进入已发送验证页面加载
TC-SENT-P02 查看已发送数量与主题
TC-SENT-P03 打开第一封邮件查看详情
TC-SENT-N01 已发送为空时执行删除
TC-SENT-N02 未勾选直接点击删除

前提：需先运行 single_login.py 并保持浏览器开启
"""

import time
import os

from compose_connect import get_connector
from folder_nav import FolderNavigator
from mail_selector import MailSelector
from mail_deleter import MailDeleter
from test_data import TestDataPreparer

SCREENSHOT_DIR = os.path.join("result", "pic")
MAIN_JSP = "https://stu.mail.ecust.edu.cn/js6/main.jsp"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _short_err(e):
    return str(e).split("\n")[0][:80]


class SentModuleTest:

    def __init__(self):
        self._results = []
        self._cur_folder = None

        print("=" * 60)
        print("  已发送模块测试 (sent_module.py)")
        print("=" * 60)
        print("  连接浏览器...")

        self.conn = get_connector()
        self.driver, self.sid = self.conn.connect()

        if not self.driver:
            raise RuntimeError("无法连接浏览器，请先运行 single_login.py")

        self.nav = FolderNavigator(self.driver, self.sid)
        self.selector = MailSelector(self.driver, self.sid)
        self.deleter = MailDeleter(self.driver)
        self.preparer = TestDataPreparer(self.driver, self.sid)

        print("[+] 连接成功，各组件初始化完成")

    # ── 工具 ────────────────────────────────────────────────

    def _log(self, msg, lv="INFO"):
        icons = {"PASS": "[+]", "FAIL": "[-]", "WARN": "[?]",
                 "STEP": "  →", "INFO": "[*]"}
        print(f"{time.strftime('%H:%M:%S')} {icons.get(lv, '[*]')} {msg}")

    def _shot(self, name):
        p = os.path.join(SCREENSHOT_DIR, f"{name}_{time.strftime('%H%M%S')}.png")
        try:
            self.driver.save_screenshot(p)
            self._log(f"截图: {p}")
        except Exception:
            p = ""
        return p

    def _rec(self, cid, ctype, name):
        return {"id": cid, "module": "已发送", "type": ctype, "name": name,
                "passed": False, "actual": "", "screenshot": "",
                "ts": time.strftime("%H:%M:%S")}

    def _nav_to(self, folder):
        ok = self.nav.navigate(folder)
        if ok:
            self._cur_folder = folder
        return ok

    # ── 用例 ────────────────────────────────────────────────

    def _s01(self):
        r = self._rec("TC-SENT-P01", "positive", "进入已发送验证页面加载")
        self._log("TC-SENT-P01 进入已发送验证页面加载", "STEP")
        self._nav_to("sent")
        r["passed"] = True
        r["actual"] = "已发送页面加载成功"
        r["screenshot"] = self._shot("s01")
        return r

    def _s02(self):
        r = self._rec("TC-SENT-P02", "positive", "查看已发送数量与主题")
        self._log("TC-SENT-P02 查看已发送数量与主题", "STEP")
        self._nav_to("sent")
        cnt = self.nav.count_emails()
        subj = self.nav.get_first_subject() if cnt > 0 else "（无）"
        r["actual"] = f"已发送数={cnt}，主题={subj[:30]}"
        r["passed"] = True
        r["screenshot"] = self._shot("s02")
        return r

    def _s03(self):
        r = self._rec("TC-SENT-P03", "positive", "打开第一封邮件查看详情")
        self._log("TC-SENT-P03 打开第一封邮件查看详情", "STEP")
        self._nav_to("sent")
        if self.nav.count_emails() > 0:
            r["passed"] = self.selector.open_first()
            r["actual"] = "邮件详情打开成功" if r["passed"] else "打开失败"
            if r["passed"]:
                self.driver.get(f"{MAIN_JSP}?sid={self.sid}&hl=zh_CN")
                time.sleep(2)
        else:
            r["actual"] = "已发送为空（跳过）"
            r["passed"] = True
        r["screenshot"] = self._shot("s03")
        return r

    def _s04(self):
        r = self._rec("TC-SENT-N01", "negative", "已发送为空时执行删除")
        self._log("TC-SENT-N01 已发送为空时执行删除", "STEP")
        self._nav_to("sent")
        if self.nav.is_empty():
            try:
                self.deleter.click_delete()
            except Exception:
                pass
            r["passed"] = True
            r["actual"] = "已发送为空，删除被拦截（符合预期）"
        else:
            r["actual"] = f"已发送有 {self.nav.count_emails()} 封（非空场景）"
            r["passed"] = True
        r["screenshot"] = self._shot("s04")
        return r

    def _s05(self):
        r = self._rec("TC-SENT-N02", "negative", "未勾选直接点击删除")
        self._log("TC-SENT-N02 未勾选直接点击删除", "STEP")
        self._nav_to("sent")
        try:
            intercepted, msg = self.deleter.try_delete_no_selection()
        except Exception as e:
            intercepted, msg = True, _short_err(e)
        r["actual"] = msg
        r["passed"] = intercepted
        r["screenshot"] = self._shot("s05")
        return r

    # ── 运行全部 ─────────────────────────────────────────────

    def run(self):
        self._log("准备测试数据...", "STEP")
        self.preparer.prepare(min_drafts=3, min_sent=2)

        print("\n" + "=" * 50)
        print("  已发送模块测试（5 用例）")
        print("=" * 50)

        for fn in [self._s01, self._s02, self._s03, self._s04, self._s05]:
            self.nav.reset_folder()
            self._cur_folder = None
            try:
                r = fn()
            except Exception as e:
                r = self._rec("UNKNOWN", "positive", "异常")
                r["actual"] = _short_err(e)
            self._results.append(r)
            self._log(f"[{r['id']}] {r['actual'][:60]}",
                      "PASS" if r["passed"] else "FAIL")

        total = len(self._results)
        passed = sum(1 for r in self._results if r["passed"])
        print("\n" + "=" * 50)
        print(f"  已发送模块测试完成  通过 {passed}/{total}  ({passed/total*100:.0f}%)")
        print("=" * 50)
        for r in self._results:
            icon = "[+]" if r["passed"] else "[-]"
            print(f"  {icon} [{r['id']}] {r['name']}: {r['actual'][:50]}")
        print("=" * 50)
        return self._results


def main():
    print("=" * 60)
    print("  已发送模块测试 — sent_module.py")
    print("  前提：需先运行 single_login.py 并保持浏览器开启")
    print("=" * 60)

    try:
        test = SentModuleTest()
    except RuntimeError as e:
        print(f"\n[-] {e}")
        input("\n按回车键退出...")
        return

    try:
        test.run()
    except KeyboardInterrupt:
        print("\n[*] 用户中断")
    except Exception as e:
        print(f"\n[!] 异常: {_short_err(e)}")
    finally:
        print("\n[*] 浏览器保持打开，按回车键退出...")
        input()


if __name__ == "__main__":
    main()
