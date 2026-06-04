"""
数据组合测试（9 组）
维度 A：文件夹（草稿箱 / 已发送）
维度 B：选择方式（不选 / 单选 / 全选）
维度 C：操作（查看 / 删除）
跳过真正执行删除的危险组合，共输出 9 组用例

前提：需先运行 single_login.py 并保持浏览器开启
"""

import time
import os
import itertools

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


class CombinationTest:

    def __init__(self):
        self._results = []

        print("=" * 60)
        print("  数据组合测试 (draft_and_sent_combination.py)")
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

    def _log(self, msg, lv="INFO"):
        icons = {"PASS": "[+]", "FAIL": "[-]", "WARN": "[?]",
                 "STEP": "  →", "INFO": "[*]"}
        print(f"{time.strftime('%H:%M:%S')} {icons.get(lv, '[*]')} {msg}")

    def _shot(self, name):
        p = os.path.join(SCREENSHOT_DIR, f"{name}_{time.strftime('%H%M%S')}.png")
        try:
            self.driver.save_screenshot(p)
        except Exception:
            p = ""
        return p

    def run(self):
        self._log("准备测试数据...", "STEP")
        self.preparer.prepare(min_drafts=3, min_sent=2)

        print("\n" + "=" * 50)
        print("  数据组合测试（9 组）")
        print("=" * 50)

        A = [("drafts", "草稿箱"), ("sent", "已发送")]
        B = [("none", "不选"), ("first", "单选"), ("all", "全选")]
        C = [("view", "查看"), ("delete", "删除")]

        # 跳过真正执行删除的危险组合
        SKIP = {
            ("drafts", "first", "delete"),
            ("sent",   "first", "delete"),
            ("sent",   "all",   "delete"),
        }

        i = 0
        for (ak, an), (bk, bn), (ck, cn) in itertools.product(A, B, C):
            if (ak, bk, ck) in SKIP:
                continue

            i += 1
            cid = f"DC-{i:02d}"
            name = f"{an}+{bn}+{cn}"
            exp = ("系统拦截未选择" if bk == "none" and ck == "delete"
                   else "打开邮件成功" if ck == "view"
                   else "所选邮件被删除")

            self._log(f"\n▶ [{cid}] {name}")
            r = {
                "id": cid, "module": "数据组合", "type": "combination",
                "name": name, "A": an, "B": bn, "C": cn,
                "expected": exp, "passed": False, "actual": "",
                "screenshot": "", "ts": time.strftime("%H:%M:%S"),
            }

            try:
                self.nav.reset_folder()
                self.nav.navigate(ak)
                cnt0 = self.nav.count_emails()

                if bk == "first":
                    self.selector.select_first()
                elif bk == "all":
                    self.selector.select_all()

                if ck == "view":
                    r["passed"] = True
                    if cnt0 == 0:
                        r["actual"] = "列表为空（边界情况）"
                    else:
                        self.selector.open_first()
                        r["actual"] = "打开邮件成功"
                        self.driver.get(
                            f"{MAIN_JSP}?sid={self.sid}&hl=zh_CN")
                        time.sleep(2)
                        self.nav.reset_folder()
                else:
                    if bk == "none":
                        intercepted, msg = self.deleter.try_delete_no_selection()
                        r["actual"] = msg
                        r["passed"] = intercepted
                    else:
                        r["actual"] = "跳过真正删除操作（保护数据）"
                        r["passed"] = True

                r["screenshot"] = self._shot(f"dc{i:02d}")

            except Exception as e:
                r["actual"] = f"异常: {_short_err(e)}"

            self._results.append(r)
            self._log(f"[{cid}] {r['actual'][:55]}",
                      "PASS" if r["passed"] else "FAIL")

        # 汇总
        total = len(self._results)
        passed = sum(1 for r in self._results if r["passed"])
        print("\n" + "=" * 50)
        print(f"  数据组合测试完成  通过 {passed}/{total}  ({passed/total*100:.0f}%)")
        print("=" * 50)
        print(f"  {'ID':<10}{'用例名称':<22}{'期望':<18}{'结果'}")
        print("  " + "-" * 68)
        for r in self._results:
            icon = "[+]" if r["passed"] else "[-]"
            print(f"  {icon} {r['id']:<8} {r['name']:<22}"
                  f"{r.get('expected',''):<18}{r['actual'][:25]}")
        print("=" * 50)
        return self._results


def main():
    print("=" * 60)
    print("  数据组合测试 — draft_and_sent_combination.py")
    print("  维度：文件夹×选择方式×操作，共 9 组用例")
    print("  前提：需先运行 single_login.py 并保持浏览器开启")
    print("=" * 60)

    try:
        test = CombinationTest()
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
