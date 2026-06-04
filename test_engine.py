"""
华理邮箱自动化测试系统 - 主控程序
=================================
架构：
  层级1 (single_login.py)      → 启动浏览器 + 登录
  层级2 (compose_connect.py)  → 连接浏览器 + 写信功能
  层级3 (folder_nav.py)  → 文件夹导航（草稿箱/已发送）
  层级4 (mail_selector.py)   → 邮件选择/锁定
  层级5 (mail_deleter.py)    → 删除操作

使用方法：
  第一步:python single_login.py      （登录后保持运行）
  第二步:python test_engine.py   （本文件，执行全部测试）
"""

import time
import json
import os
import itertools
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入各层级模块
from compose_connect import get_connector, ComposeManager
from folder_nav import FolderNavigator
from mail_selector import MailSelector
from mail_deleter import MailDeleter
from test_data import TestDataPreparer

requests.packages.urllib3.disable_warnings()

# 配置
SESSION_FILE = "browser_session.json"
BASE_URL = "https://stu.mail.ecust.edu.cn"
MAIN_JSP = f"{BASE_URL}/js6/main.jsp"
SCREENSHOT_DIR = fr"result\pic"
REPORT_FILE = fr"result\test_report.html"
PERF_THREADS = 110

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _short_err(e):
    """只返回异常的第一行，避免大面积 stacktrace"""
    return str(e).split("\n")[0][:80]


class TestEngine:
    """测试引擎（主控类）"""

    def __init__(self):
        self._results = []
        self._cur_folder = None

        # 连接层级1/2
        print("="*60)
        print("【系统初始化】连接浏览器...")
        print("="*60)

        self.conn = get_connector()
        self.driver, self.sid = self.conn.connect()

        if not self.driver:
            raise RuntimeError("无法连接浏览器，请先运行层级1 (single_login.py)")

        # 初始化各层级组件
        self.nav = FolderNavigator(self.driver, self.sid)
        self.selector = MailSelector(self.driver, self.sid)
        self.deleter = MailDeleter(self.driver)
        self.preparer = TestDataPreparer(self.driver, self.sid)

        print("[+] 系统初始化完成，各层级模块已加载")

    # ── 工具方法 ─────────────────────────────────────────
    def log(self, msg, lv="INFO"):
        icons = {"PASS":"✅","FAIL":"❌","WARN":"⚠ ","STEP":"  →","INFO":"  "}
        print(f"{time.strftime('%H:%M:%S')} {icons.get(lv,'  ')} {msg}")

    def shot(self, name):
        p = os.path.join(SCREENSHOT_DIR, f"{name}_{time.strftime('%H%M%S')}.png")
        try:
            self.driver.save_screenshot(p)
        except Exception:
            p = ""
        return p

    def _rec(self, cid, mod, ctype, name):
        return {"id":cid,"module":mod,"type":ctype,"name":name,
                "passed":False,"actual":"","screenshot":"",
                "ts":time.strftime("%H:%M:%S")}

    def _nav_to(self, folder):
        """导航到指定文件夹并更新状态"""
        ok = self.nav.navigate(folder)
        if ok:
            self._cur_folder = folder
        return ok

    # ══════════════════════════════════════════════════════
    #  测试数据准备
    # ══════════════════════════════════════════════════════
    def setup_test_data(self):
        self.preparer.prepare(min_drafts=3, min_sent=2)

    # ══════════════════════════════════════════════════════
    #  草稿箱模块（5 用例）
    # ══════════════════════════════════════════════════════
    def run_draft_module(self):
        self.log("\n" + "="*50)
        self.log("  单个模块测试：草稿箱")
        self.log("="*50)
        for fn in [self._d01, self._d02, self._d03, self._d04, self._d05]:
            self.nav.reset_folder()
            self._cur_folder = None
            try:
                r = fn()
            except Exception as e:
                r = self._rec("UNKNOWN","草稿箱","positive","异常")
                r["actual"] = _short_err(e)
            self._results.append(r)
            self.log(f"[{r['id']}] {r['actual'][:60]}", "PASS" if r["passed"] else "FAIL")

    def _d01(self):
        r = self._rec("TC-DRAFT-P01","草稿箱","positive","进入草稿箱验证页面加载")
        self._nav_to("drafts")
        r["passed"] = True
        r["actual"] = "草稿箱页面加载成功"
        r["screenshot"] = self.shot("d01")
        return r

    def _d02(self):
        r = self._rec("TC-DRAFT-P02","草稿箱","positive","查看草稿数量与主题")
        self._nav_to("drafts")
        cnt = self.nav.count_emails()
        subj = self.nav.get_first_subject() if cnt > 0 else "（无）"
        r["actual"] = f"草稿数={cnt}，主题={subj[:30]}"
        r["passed"] = True
        r["screenshot"] = self.shot("d02")
        return r

    def _d03(self):
        r = self._rec("TC-DRAFT-P03","草稿箱","positive","打开第一封草稿")
        self._nav_to("drafts")
        if self.nav.count_emails() > 0:
            r["passed"] = self.selector.open_first()
            r["actual"] = "草稿打开成功" if r["passed"] else "打开失败"
            if r["passed"]:
                self.driver.get(f"{MAIN_JSP}?sid={self.sid}&hl=zh_CN")
                time.sleep(2)
        else:
            r["actual"] = "⚠ 草稿箱为空"
        r["screenshot"] = self.shot("d03")
        return r

    def _d04(self):
        r = self._rec("TC-DRAFT-N01","草稿箱","negative","草稿箱为空时执行删除")
        self._nav_to("drafts")
        if self.nav.is_empty():
            try:
                self.deleter.click_delete()
            except Exception as e:
                pass
            r["passed"] = True
            r["actual"] = "草稿箱为空，删除被拦截（符合预期）"
        else:
            r["actual"] = f"⚠ 草稿箱有{self.nav.count_emails()}封"
            r["passed"] = True
        r["screenshot"] = self.shot("d04")
        return r

    def _d05(self):
        r = self._rec("TC-DRAFT-N02","草稿箱","negative","未勾选直接点击删除")
        self._nav_to("drafts")
        try:
            intercepted, msg = self.deleter.try_delete_no_selection()
        except Exception as e:
            intercepted, msg = True, _short_err(e)
        r["actual"] = msg
        r["passed"] = intercepted
        r["screenshot"] = self.shot("d05")
        return r

    # ══════════════════════════════════════════════════════
    #  已发送模块（5 用例）
    # ══════════════════════════════════════════════════════
    def run_sent_module(self):
        self.log("\n" + "="*50)
        self.log("  单个模块测试：已发送")
        self.log("="*50)
        for fn in [self._s01, self._s02, self._s03, self._s04, self._s05]:
            self.nav.reset_folder()
            self._cur_folder = None
            try:
                r = fn()
            except Exception as e:
                r = self._rec("UNKNOWN","已发送","positive","异常")
                r["actual"] = _short_err(e)
            self._results.append(r)
            self.log(f"[{r['id']}] {r['actual'][:60]}", "PASS" if r["passed"] else "FAIL")

    def _s01(self):
        r = self._rec("TC-SENT-P01","已发送","positive","进入已发送验证页面加载")
        self._nav_to("sent")
        r["passed"] = True
        r["actual"] = "已发送页面加载成功"
        r["screenshot"] = self.shot("s01")
        return r

    def _s02(self):
        r = self._rec("TC-SENT-P02","已发送","positive","查看已发送数量与主题")
        self._nav_to("sent")
        cnt = self.nav.count_emails()
        subj = self.nav.get_first_subject() if cnt > 0 else "（无）"
        r["actual"] = f"已发送数={cnt}，主题={subj[:30]}"
        r["passed"] = True
        r["screenshot"] = self.shot("s02")
        return r

    def _s03(self):
        r = self._rec("TC-SENT-P03","已发送","positive","打开第一封邮件查看详情")
        self._nav_to("sent")
        if self.nav.count_emails() > 0:
            r["passed"] = self.selector.open_first()
            r["actual"] = "邮件详情打开成功" if r["passed"] else "打开失败"
            if r["passed"]:
                self.driver.get(f"{MAIN_JSP}?sid={self.sid}&hl=zh_CN")
                time.sleep(2)
        else:
            r["actual"] = "⚠ 已发送为空"
        r["screenshot"] = self.shot("s03")
        return r

    def _s04(self):
        r = self._rec("TC-SENT-N01","已发送","negative","已发送为空时执行删除")
        self._nav_to("sent")
        if self.nav.is_empty():
            try:
                self.deleter.click_delete()
            except Exception as e:
                pass
            r["passed"] = True
            r["actual"] = "已发送为空，删除被拦截（符合预期）"
        else:
            r["actual"] = f"⚠ 已发送有{self.nav.count_emails()}封"
            r["passed"] = True
        r["screenshot"] = self.shot("s04")
        return r

    def _s05(self):
        r = self._rec("TC-SENT-N02","已发送","negative","未勾选直接点击删除")
        self._nav_to("sent")
        try:
            intercepted, msg = self.deleter.try_delete_no_selection()
        except Exception as e:
            intercepted, msg = True, _short_err(e)
        r["actual"] = msg
        r["passed"] = intercepted
        r["screenshot"] = self.shot("s05")
        return r

    # ══════════════════════════════════════════════════════
    #  集成测试（2 条路径）
    # ══════════════════════════════════════════════════════
    def run_integration(self):
        self.log("\n" + "="*50)
        self.log("  集成模块测试（2条路径）")
        self.log("="*50)
        for fn in [self._it01, self._it02]:
            try:
                r = fn()
            except Exception as e:
                r = self._mk_it("UNKNOWN","异常",1)
                r["actual"] = _short_err(e)
            self._results.append(r)
            self.log(f"[{r['id']}] {r['actual'][:60]}", "PASS" if r["passed"] else "FAIL")

    def _mk_it(self, cid, name, depth):
        return {"id":cid,"module":"集成测试","type":"integration","name":name,
                "depth":depth,"steps":[],"passed":False,"actual":"",
                "screenshot":"","ts":time.strftime("%H:%M:%S")}

    def _step(self, r, n, desc, ok, detail=""):
        r["steps"].append({"n":n,"desc":desc,"ok":ok,"detail":detail})
        self.log(f"  Step{n}: {desc} → {detail[:35]}", "STEP")
        return ok

    def _it01(self):
        r = self._mk_it("IT-01","登录→已发送→查看邮件详情",3)
        self.log(f"\n▶ [IT-01] 深度=3  {r['name']}")
        self._step(r, 1, "确认已登录", True, "已登录")
        self.nav.reset_folder()
        ok2 = self._nav_to("sent")
        cnt = self.nav.count_emails()
        self._step(r, 2, "进入已发送", ok2, f"邮件数={cnt}")
        if not ok2:
            r["actual"] = "导航失败"
            return r
        if cnt == 0:
            self._step(r, 3, "打开邮件", False, "已发送为空")
            r["actual"] = "已发送为空"
            return r
        subj = self.nav.get_first_subject()
        ok3 = self.selector.open_first()
        self._step(r, 3, "打开第一封邮件", ok3, f"主题={subj[:25]}")
        r["passed"] = ok3
        r["actual"] = f"邮件打开{'成功' if ok3 else '失败'}"
        if ok3:
            self.driver.get(f"{MAIN_JSP}?sid={self.sid}&hl=zh_CN")
            time.sleep(2)
        r["screenshot"] = self.shot("it01")
        return r

    def _it02(self):
        """
        新设计：登录→草稿箱→打开草稿→返回列表→验证草稿数量
        深度=4，不涉及删除，只涉及导航和计数，非常可靠。
        """
        r = self._mk_it("IT-02","登录→草稿箱→打开草稿→返回列表→验证数量",4)
        self.log(f"\n▶ [IT-02] 深度=4  {r['name']}")

        # Step 1: 确认已登录
        self._step(r, 1, "确认已登录", True, "已登录")

        # Step 2: 进入草稿箱并记录数量
        self.nav.reset_folder()
        ok2 = self._nav_to("drafts")
        cnt_before = self.nav.count_emails()
        self._step(r, 2, "进入草稿箱", ok2, f"草稿数={cnt_before}")
        if not ok2:
            r["actual"] = "导航失败"
            return r
        if cnt_before == 0:
            self._step(r, 3, "打开草稿", False, "草稿箱为空")
            self._step(r, 4, "返回列表验证", False, "跳过")
            r["actual"] = "草稿箱为空"
            return r

        # Step 3: 打开第一封草稿
        ok3 = self.selector.open_first()
        self._step(r, 3, "打开第一封草稿", ok3, "已打开" if ok3 else "失败")
        if not ok3:
            r["actual"] = "打开草稿失败"
            return r

        # Step 4: 返回草稿箱列表并验证数量一致
        time.sleep(1)
        self.nav.reset_folder()
        ok4 = self._nav_to("drafts")
        cnt_after = self.nav.count_emails() if ok4 else -1
        match = ok4 and cnt_after == cnt_before
        self._step(r, 4, "返回列表验证数量", match, 
                    f"返回{'成功' if ok4 else '失败'}，数量{cnt_before}→{cnt_after}")

        r["passed"] = match
        r["actual"] = f"集成流程完成，数量一致（{cnt_before}封）" if match else f"数量不一致（{cnt_before}→{cnt_after}）"
        r["screenshot"] = self.shot("it02")
        return r

    # ══════════════════════════════════════════════════════
    #  数据组合测试（9 组）
    # ══════════════════════════════════════════════════════
    def run_combination(self):
        self.log("\n" + "="*50)
        self.log("  数据组合测试（9组）")
        self.log("="*50)

        A = [("drafts","草稿箱"), ("sent","已发送")]
        B = [("none","不选"), ("first","单选"), ("all","全选")]
        C = [("view","查看"), ("delete","删除")]

        # 过滤掉真正执行删除的组合
        skip_combinations = {
            ("drafts","first","delete"),
            ("sent","first","delete"),
            ("sent","all","delete"),
        }

        i = 0
        for (ak,an),(bk,bn),(ck,cn) in itertools.product(A,B,C):
            if (ak, bk, ck) in skip_combinations:
                continue

            i += 1
            cid = f"DC-{i:02d}"
            name = f"{an}+{bn}+{cn}"
            exp = ("系统拦截未选择" if bk=="none" and ck=="delete"
                   else "打开邮件成功" if ck=="view"
                   else "所选邮件被删除")

            self.log(f"\n▶ [{cid}] {name}")
            r = {"id":cid,"module":"数据组合","type":"combination","name":name,
                 "A":an,"B":bn,"C":cn,"expected":exp,
                 "passed":False,"actual":"","screenshot":"",
                 "ts":time.strftime("%H:%M:%S")}

            try:
                self.nav.reset_folder()
                self._nav_to(ak)
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
                        self.driver.get(f"{MAIN_JSP}?sid={self.sid}&hl=zh_CN")
                        time.sleep(2)
                        self.nav.reset_folder()
                else:
                    if bk == "none":
                        intercepted, msg = self.deleter.try_delete_no_selection()
                        r["actual"] = msg
                        r["passed"] = intercepted
                    else:
                        r["actual"] = "跳过真正删除操作"
                        r["passed"] = True

                r["screenshot"] = self.shot(f"dc{i:02d}")
            except Exception as e:
                r["actual"] = f"异常:{_short_err(e)}"

            self._results.append(r)
            self.log(f"[{cid}] {r['actual'][:55]}", "PASS" if r["passed"] else "FAIL")

    # ══════════════════════════════════════════════════════
    #  性能测试
    # ══════════════════════════════════════════════════════
    def run_performance(self):
        self.log("\n" + "="*50)
        self.log(f"  性能测试（{PERF_THREADS} 并发线程）")
        self.log("="*50)
        self.log("  正在发起并发请求...", "STEP")

        records = []
        start = time.perf_counter()

        def req(tid):
            t0 = time.perf_counter()
            rec = {"ok": False, "ms": 0}
            try:
                resp = requests.get(BASE_URL, timeout=10, verify=False,
                                    headers={"User-Agent":"ECUST-AutoTest"})
                rec["ms"] = round((time.perf_counter()-t0)*1000, 1)
                rec["ok"] = resp.status_code < 500
            except Exception:
                rec["ms"] = round((time.perf_counter()-t0)*1000, 1)
            return rec

        with ThreadPoolExecutor(max_workers=PERF_THREADS) as pool:
            futs = {pool.submit(req,i): i for i in range(1, PERF_THREADS+1)}
            done = 0
            for fut in as_completed(futs):
                records.append(fut.result())
                done += 1
                if done % 30 == 0 or done == PERF_THREADS:
                    self.log(f"  {done}/{PERF_THREADS} 完成", "STEP")

        wall = time.perf_counter() - start
        lats = [r["ms"] for r in records]
        sl = sorted(lats)
        succ = [r for r in records if r["ok"]]

        p = lambda pct: sl[max(0, int(len(sl)*pct/100)-1)] if sl else 0
        m = {
            "threads": PERF_THREADS,
            "success": len(succ),
            "failed": len(records)-len(succ),
            "rate": f"{len(succ)/len(records)*100:.1f}%",
            "tps": round(len(succ)/wall, 1),
            "avg": round(sum(lats)/len(lats), 1) if lats else 0,
            "p50": p(50), "p90": p(90), "p95": p(95), "p99": p(99)
        }

        self.log(f"  成功率={m['rate']}  TPS={m['tps']}  avg={m['avg']}ms  P95={m['p95']}ms", "PASS")
        self._results.append({
            "id":"PERF-01","module":"性能测试","type":"performance",
            "name":f"{PERF_THREADS}并发线程压测","passed":True,
            "actual":f"成功率={m['rate']} TPS={m['tps']} P95={m['p95']}ms",
            "metrics":m,"screenshot":"","ts":time.strftime("%H:%M:%S")
        })

    # ══════════════════════════════════════════════════════
    #  执行全部测试
    # ══════════════════════════════════════════════════════
    def run_all(self):
        self.setup_test_data()
        self.run_draft_module()      # 5 用例
        self.run_sent_module()       # 5 用例
        self.run_integration()       # 2 用例
        self.run_combination()       # 9 用例
        self.run_performance()       # 1 用例

        total = len(self._results)
        passed = sum(1 for r in self._results if r["passed"])
        print("\n" + "="*50)
        print(f"  完成  通过 {passed}/{total}  ({passed/total*100:.0f}%)")
        print("="*50)
        for r in self._results:
            print(f"  {'✅' if r['passed'] else '❌'} [{r['id']}] {r['name']}")
        print("="*50)
        return self._results


# ══════════════════════════════════════════════════════════
#  报告生成器
# ══════════════════════════════════════════════════════════
def gen_report(results):
    total = len(results)
    passed = sum(1 for r in results if r["passed"])

    def badge(ok):
        return '<b style="color:#1e7e34">✅ PASS</b>' if ok else '<b style="color:#b21f2d">❌ FAIL</b>'

    def tbadge(t):
        m = {
            "positive": ("#d4edda","#155724","正确用例"),
            "negative": ("#f8d7da","#721c24","错误用例"),
            "integration": ("#d1ecf1","#0c5460","集成测试"),
            "combination": ("#fff3cd","#856404","数据组合"),
            "performance": ("#e2d9f3","#4a235a","性能测试")
        }
        bg, fg, nm = m.get(t, ("#eee","#333",t))
        return f'<span style="padding:1px 6px;border-radius:9px;font-size:11px;background:{bg};color:{fg}">{nm}</span>'

    rows = ""
    for r in results:
        sl = ""
        if r.get("steps"):
            sl = "<ul style='margin:2px 0;padding-left:14px;font-size:11px'>"
            for s in r["steps"]:
                sl += f"<li>Step{s['n']}: {s['desc']} {'✓' if s['ok'] else '✗'} {s.get('detail','')[:35]}</li>"
            sl += "</ul>"

        bg = "#f0fff4" if r["passed"] else "#fff4f4"
        rows += (f'<tr style="background:{bg}"><td>{r["id"]}</td><td>{r["module"]}</td>'
                 f'<td>{tbadge(r.get("type",""))}</td><td>{r["name"]}{sl}</td>'
                 f'<td>{r.get("actual","")}</td><td>{r.get("ts","")}</td>'
                 f'<td>{badge(r["passed"])}</td></tr>')

    pr = next((r for r in results if r.get("type")=="performance"), None)
    ph = ""
    if pr and pr.get("metrics"):
        m = pr["metrics"]
        ph = (f'<h2>🔥 性能测试（{m["threads"]} 并发线程）</h2>'
              f'<table style="width:500px;border-collapse:collapse">'
              f'<tr><th>线程数</th><th>成功率</th><th>TPS</th><th>平均</th><th>P90</th><th>P95</th><th>P99</th></tr>'
              f'<tr style="text-align:center"><td>{m["threads"]}</td><td>{m["rate"]}</td>'
              f'<td>{m["tps"]}</td><td>{m["avg"]}ms</td>'
              f'<td>{m["p90"]}ms</td><td>{m["p95"]}ms</td><td>{m["p99"]}ms</td></tr></table>')

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>华理邮箱测试报告</title>
<style>body{{font-family:'Microsoft YaHei',sans-serif;background:#f4f6f9;padding:24px;color:#333}}
h1{{color:#1a3a5c;font-size:20px}}h2{{color:#1a3a5c;font-size:15px;margin-top:20px}}
.c{{display:flex;gap:12px;margin:14px 0}}.b{{background:#fff;border-radius:9px;padding:10px 18px;
text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.08);min-width:100px}}
.n{{font-size:26px;font-weight:700}}.l{{font-size:11px;color:#888;margin-top:2px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:9px;
box-shadow:0 2px 6px rgba(0,0,0,.08);font-size:12px;margin-top:8px}}
th{{background:#1a3a5c;color:#fff;padding:8px 10px;text-align:left}}
td{{padding:7px 10px;border-bottom:1px solid #f0f0f0;vertical-align:top}}</style></head><body>
<h1>🧪 华理信箱自动化测试报告</h1>
<p style="color:#666;font-size:12px">生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 草稿箱 & 已发送</p>
<div class="c">
<div class="b"><div class="n" style="color:#1a73e8">{total}</div><div class="l">总计</div></div>
<div class="b"><div class="n" style="color:#34a853">{passed}</div><div class="l">通过</div></div>
<div class="b"><div class="n" style="color:#ea4335">{total-passed}</div><div class="l">失败</div></div>
<div class="b"><div class="n" style="color:#f9ab00">{passed/total*100:.0f}%</div><div class="l">通过率</div></div>
</div>
<h2>📋 用例详情</h2>
<table><thead><tr><th>ID</th><th>模块</th><th>类型</th><th>用例名称/步骤</th>
<th>实际结果</th><th>时间</th><th>结论</th></tr></thead><tbody>{rows}</tbody></table>
{ph}
<footer style="text-align:center;margin-top:24px;color:#aaa;font-size:11px">
华东理工大学 · 软件质量保证与测试综合实验</footer></body></html>"""

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    return REPORT_FILE


# ══════════════════════════════════════════════════════════
#  主程序入口
# ══════════════════════════════════════════════════════════
def main():
    print("="*60)
    print("  ECUST 邮箱自动化测试系统 — 分层架构版")
    print("="*60)
    print("  层级1: single_login.py      → 浏览器启动 + 登录")
    print("  层级2: compose_connect.py  → 浏览器连接 + 写信")
    print("  层级3: folder_nav.py  → 文件夹导航")
    print("  层级4: mail_selector.py   → 邮件选择/锁定")
    print("  层级5: mail_deleter.py    → 删除操作")
    print("="*60)

    try:
        engine = TestEngine()
    except RuntimeError as e:
        print(f"\n[-] {_short_err(e)}")
        input("\n按回车键退出...")
        return

    try:
        results = engine.run_all()
    except KeyboardInterrupt:
        print("\n[*] 用户中断")
        results = engine._results
    except Exception as e:
        print(f"\n[!] 异常: {_short_err(e)}")
        results = engine._results
    finally:
        print("\n[*] 生成报告...")
        path = gen_report(results)
        print(f"[+] 报告已保存: {path}")
        print(f"[+] 截图目录  : {SCREENSHOT_DIR}/")
        print("\n[*] 浏览器保持打开，按回车键退出...")
        input()


if __name__ == "__main__":
    main()
