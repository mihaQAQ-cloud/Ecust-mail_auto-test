"""
ECUST 邮箱自动化测试系统 - GUI 图形演示界面
"""

import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import os
import sys
import glob
import queue

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable
PIC_DIR = os.path.join(BASE_DIR, "result", "pic")

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ── 测试文件定义 ──────────────────────────────────────────────

SINGLE_STEP_FILES = [
    # (文件名, 层级标签, 职责描述, 依赖层级号)
    ("single_login.py",          "层级1", "启动调试模式 Edge 浏览器，执行登录并保存会话信息",                           0),
    ("compose_connect.py",       "层级2", "连接已启动的浏览器，提供写信/邮件撰写功能",                                 1),
    ("compose_connect_test.py",  "层级2", "连接已启动的浏览器，进入写信页面",                                          1),
    ("enter_sent_box.py",        "层级2", "进入已发送页面",                                                            1),
    ("folder_nav.py",            "层级3", "文件夹导航（草稿箱/已发送），统计邮件数量，检测空文件夹",                     2),
    ("enter_sent_and_search.py", "层级3", "搜索发送给 23070066 的信件并点击进入",                                      2),
    ("recipient_test.py",        "层级3", "填写收件人",                                                                2),
    ("theme_test.py",            "层级3", "填写主题",                                                                  2),
    ("text_test.py",             "层级3", "填写正文",                                                                  2),
    ("attachment_test.py",       "层级3", "添加附件测试（成功：png/txt/zip/html/pptx；失败：js/bat）",                 2),
    ("mail_selector.py",         "层级4", "邮件选择/锁定，支持单选、全选、打开邮件详情",                                3),
    ("resend_mail.py",           "层级4", "进入再次编辑页面",                                                          3),
    ("button_test.py",           "层级4", "发送按钮测试：发送失败返回写信页面，无主题时自动确认发送",                    3),
    ("mail_deleter.py",          "层级5", "邮件删除操作，支持未勾选拦截检测和删除验证",                                 4),
    ("cancel_return.py",         "层级5", "实现点击【返回】按钮回到信件页面",                                          4),
    ("return_write.py",          "层级5", "发送成功时点击【继续写信】，返回写信页面",                                   4),
    ("draft_module.py",          "模块层", "草稿箱模块测试（5用例）：页面加载、数量统计、打开草稿、空箱删除、未勾选删除", 1),
    ("sent_module.py",           "模块层", "已发送模块测试（5用例）：页面加载、数量统计、打开邮件、空箱删除、未勾选删除", 1),
]

INTEGRATION_FILES = [
    ("all_steps.py",
     "实现登录、进入已发送、寻找 23070066 信笺进入再次编辑，编辑成功，实现发送点击（实现返回键）"),
    ("red_flag.py",
     "实现登录、进入收件箱、寻找 23070066 发给我的邮件，进入设置为红旗文件。（实现精准定位）"),
    ("compose_connect_all_test.py",
     "实现进入写信页面，填写收件人、主题、正文、添加附件，发送，成功发送后返回写信页面的测试"),
    ("draft_integration.py",
     "草稿箱集成测试 IT-02：自动登录 → 进入草稿箱 → 打开草稿 → 返回列表 → 验证数量一致（深度=4，自包含）"),
    ("sent_integration.py",
     "已发送集成测试 IT-01：自动登录 → 进入已发送 → 打开第一封邮件查看详情（深度=3，自包含）"),
]

DATA_COMBO_FILES = [
    ("login.py",
     "实现八组数据测试：两组密码账号正确，一组无验证码，一组有验证码；六组密码/账号错误。实现实际登录查看是否成功后返回。"),
    ("draft_and_sent_combination.py",
     "数据组合测试（9组）：维度 文件夹×选择方式×操作，覆盖草稿箱与已发送全量组合场景（需先运行 single_login.py）"),
]

PERF_FILES = [
    ("performance.py",
     "110 并发线程压测邮件服务器，统计成功率、TPS、平均延迟及 P50/P90/P95/P99 分位延迟，无需浏览器"),
]

ITEMS_PER_PAGE = 9

# ── 层级徽章颜色 ──────────────────────────────────────────────
LEVEL_COLORS = {
    "层级1": "#ff7b72",
    "层级2": "#ffa657",
    "层级3": "#f8e3a1",
    "层级4": "#7ee787",
    "层级5": "#79c0ff",
    "模块层": "#d2a8ff",
}

# ── 暗色主题配色 ──────────────────────────────────────────────
C = {
    "bg_title":    "#0d1117",
    "bg_nav":      "#0d1117",
    "bg_content":  "#161b22",
    "bg_row_a":    "#161b22",
    "bg_row_b":    "#1c2128",
    "bg_header":   "#21262d",
    "bg_output":   "#0d1117",
    "fg_primary":  "#f0f6fc",
    "fg_muted":    "#8b949e",
    "fg_accent":   "#58a6ff",
    "fg_code":     "#79c0ff",
    "fg_text":     "#e6edf3",
    "sep":         "#30363d",
    "btn_green":   "#238636",
    "btn_red":     "#da3633",
    "btn_green_h": "#2ea043",
    "btn_red_h":   "#b62324",
    "nav_active":  "#21262d",
}


class TestGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ECUST 邮箱自动化测试系统")
        self.root.geometry("1280x820")
        self.root.configure(bg=C["bg_content"])
        self.root.minsize(1000, 660)

        # 状态追踪
        self.started_levels: set = set()
        self.running_procs: dict = {}
        self.btn_started: dict = {}
        self.output_queue: queue.Queue = queue.Queue()
        self.output_widgets: dict = {}
        self.page_buttons: dict = {
            "integration": {}, "data": {}, "perf": {}
        }
        self.image_refs: list = []

        # 单步测试分页
        self.current_page = 0
        self.total_pages = (
            len(SINGLE_STEP_FILES) + ITEMS_PER_PAGE - 1
        ) // ITEMS_PER_PAGE

        self._build_ui()
        self._poll_queue()

    # ────────────────────────────────────────────────────────────
    # UI 构建
    # ────────────────────────────────────────────────────────────

    def _build_ui(self):
        bar = tk.Frame(self.root, bg=C["bg_title"], height=54)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)
        tk.Label(bar, text="ECUST 邮箱自动化测试系统",
                 font=("Microsoft YaHei", 17, "bold"),
                 bg=C["bg_title"], fg=C["fg_accent"]).pack(pady=13)

        body = tk.Frame(self.root, bg=C["bg_content"])
        body.pack(fill=tk.BOTH, expand=True)

        self._build_nav(body)
        tk.Frame(body, width=1, bg=C["sep"]).pack(side=tk.LEFT, fill=tk.Y)

        self.host = tk.Frame(body, bg=C["bg_content"])
        self.host.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.pages = {
            "single":      self._build_single_page(),
            "integration": self._build_integration_page(),
            "data":        self._build_data_page(),
            "perf":        self._build_perf_page(),
        }
        self._show_page("single")

    def _build_nav(self, parent):
        nav = tk.Frame(parent, bg=C["bg_nav"], width=195)
        nav.pack(side=tk.LEFT, fill=tk.Y)
        nav.pack_propagate(False)

        tk.Label(nav, text="测试导航",
                 font=("Microsoft YaHei", 10),
                 bg=C["bg_nav"], fg=C["fg_muted"]).pack(pady=(22, 10))

        entries = [
            ("single",      "  单步测试"),
            ("integration", "  集成测试"),
            ("data",        "  数据组合测试"),
            ("perf",        "  性能测试"),
        ]
        self.nav_btns = {}
        for key, label in entries:
            b = tk.Button(nav, text=label,
                          font=("Microsoft YaHei", 11),
                          bg=C["bg_nav"], fg=C["fg_primary"],
                          activebackground=C["nav_active"],
                          activeforeground=C["fg_accent"],
                          bd=0, relief=tk.FLAT, anchor="w",
                          cursor="hand2", padx=16, pady=13,
                          command=lambda k=key: self._show_page(k))
            b.pack(fill=tk.X, padx=6, pady=2)
            self.nav_btns[key] = b

    def _show_page(self, key: str):
        for p in self.pages.values():
            p.pack_forget()
        self.pages[key].pack(fill=tk.BOTH, expand=True)
        for k, b in self.nav_btns.items():
            b.configure(
                bg=C["nav_active"] if k == key else C["bg_nav"],
                fg=C["fg_accent"] if k == key else C["fg_primary"],
            )

    # ────────────────────────────────────────────────────────────
    # 单步测试页
    # ────────────────────────────────────────────────────────────

    def _build_single_page(self) -> tk.Frame:
        frame = tk.Frame(self.host, bg=C["bg_content"])

        hdr = tk.Frame(frame, bg=C["bg_content"])
        hdr.pack(fill=tk.X, padx=20, pady=(16, 4))
        tk.Label(hdr, text="单步测试",
                 font=("Microsoft YaHei", 15, "bold"),
                 bg=C["bg_content"], fg=C["fg_primary"]).pack(anchor="w")
        tk.Label(hdr,
                 text="请按层级顺序依次启动各模块，高层级依赖低层级运行结果",
                 font=("Microsoft YaHei", 9),
                 bg=C["bg_content"], fg=C["fg_muted"]).pack(anchor="w")

        self.single_table_wrap = tk.Frame(
            frame, bg=C["bg_header"],
            highlightthickness=1, highlightbackground=C["sep"])
        self.single_table_wrap.pack(fill=tk.X, padx=18, pady=(8, 4))

        self._make_header(self.single_table_wrap,
                          [("文件名", 22), ("层级", 7), ("职责描述", 52), ("操作", 8)])
        tk.Frame(self.single_table_wrap, height=1, bg=C["sep"]).pack(fill=tk.X)

        self.single_body = tk.Frame(self.single_table_wrap, bg=C["bg_content"])
        self.single_body.pack(fill=tk.X)

        self.pg_bar = tk.Frame(frame, bg=C["bg_content"])
        self.pg_bar.pack(pady=(2, 2))

        self._build_output(frame, "single").pack(
            fill=tk.BOTH, expand=True, padx=18, pady=(0, 10))

        self._render_single_body()
        self._render_pagination()
        return frame

    def _make_header(self, parent, cols):
        hdr = tk.Frame(parent, bg=C["bg_header"])
        hdr.pack(fill=tk.X)
        for i, (text, w) in enumerate(cols):
            tk.Label(hdr, text=text,
                     font=("Microsoft YaHei", 10, "bold"),
                     bg=C["bg_header"], fg=C["fg_accent"],
                     anchor="w", padx=10, pady=9, width=w).grid(
                row=0, column=i, sticky="ew")
        hdr.grid_columnconfigure(2, weight=1)

    def _render_single_body(self):
        for w in self.single_body.winfo_children():
            w.destroy()

        start = self.current_page * ITEMS_PER_PAGE
        items = SINGLE_STEP_FILES[start: start + ITEMS_PER_PAGE]

        for i, (fname, level, desc, req_lvl) in enumerate(items):
            bg = C["bg_row_a"] if i % 2 == 0 else C["bg_row_b"]
            row = tk.Frame(self.single_body, bg=bg)
            row.pack(fill=tk.X)
            tk.Frame(row, height=1, bg=C["sep"]).pack(fill=tk.X)

            inner = tk.Frame(row, bg=bg)
            inner.pack(fill=tk.X)

            tk.Label(inner, text=fname,
                     font=("Consolas", 9), bg=bg, fg=C["fg_code"],
                     anchor="w", padx=10, pady=7, width=22).grid(
                row=0, column=0, sticky="ew")

            lc = LEVEL_COLORS.get(level, C["fg_text"])
            tk.Label(inner, text=level,
                     font=("Microsoft YaHei", 9), bg=bg, fg=lc,
                     anchor="center", padx=4, pady=7, width=7).grid(
                row=0, column=1, sticky="ew")

            tk.Label(inner, text=desc,
                     font=("Microsoft YaHei", 9), bg=bg, fg=C["fg_text"],
                     anchor="w", padx=10, pady=7,
                     wraplength=470, justify="left").grid(
                row=0, column=2, sticky="ew")

            running = self.btn_started.get(fname, False)
            tk.Button(inner,
                      text="运行中" if running else "启动",
                      font=("Microsoft YaHei", 9, "bold"),
                      bg=C["btn_red"] if running else C["btn_green"],
                      fg="white",
                      activebackground=C["btn_red_h"] if running else C["btn_green_h"],
                      bd=0, relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                      command=lambda f=fname, r=req_lvl: self._launch_single(f, r)
                      ).grid(row=0, column=3, padx=10, pady=5)

            inner.grid_columnconfigure(2, weight=1)

    def _render_pagination(self):
        for w in self.pg_bar.winfo_children():
            w.destroy()
        if self.total_pages <= 1:
            return

        tk.Label(self.pg_bar, text="页码：",
                 font=("Microsoft YaHei", 9),
                 bg=C["bg_content"], fg=C["fg_muted"]).pack(side=tk.LEFT, padx=(0, 4))

        for i in range(self.total_pages):
            active = (i == self.current_page)
            tk.Button(self.pg_bar,
                      text=str(i + 1),
                      font=("Microsoft YaHei", 9, "bold" if active else "normal"),
                      bg=C["btn_green"] if active else C["bg_header"],
                      fg="white" if active else C["fg_muted"],
                      activebackground=C["btn_green_h"],
                      bd=0, relief=tk.FLAT, padx=11, pady=4, cursor="hand2",
                      command=lambda p=i: self._goto_page(p)
                      ).pack(side=tk.LEFT, padx=2)

    def _goto_page(self, p: int):
        self.current_page = p
        self._render_single_body()
        self._render_pagination()

    def _launch_single(self, fname: str, req_lvl: int):
        if req_lvl > 0 and req_lvl not in self.started_levels:
            self._append("single",
                f"\n[错误] 无法启动 {fname}\n"
                f"  → 需要先启动 层级{req_lvl} 的至少一个模块，再运行此文件！\n\n",
                tag="fail")
            return

        proc = self.running_procs.get(fname)
        if proc and proc.poll() is None:
            self._append("single",
                f"\n[提示] {fname} 正在运行中，请勿重复启动\n\n", tag="warn")
            return

        self.btn_started[fname] = True
        for item in SINGLE_STEP_FILES:
            if item[0] == fname:
                lvl_str = item[1]
                if lvl_str.startswith("层级"):
                    try:
                        self.started_levels.add(int(lvl_str.replace("层级", "")))
                    except ValueError:
                        pass
                break
        self._render_single_body()

        self._append("single", f"\n{'─'*54}\n  启动  {fname}\n{'─'*54}\n")

        script = os.path.join(BASE_DIR, fname)
        cmd = [PYTHON_EXE, script]
        if fname == "single_login.py":
            cmd.append("--run-login")

        self._run_in_thread(fname, cmd, "single")

    # ────────────────────────────────────────────────────────────
    # 集成测试页
    # ────────────────────────────────────────────────────────────

    def _build_integration_page(self) -> tk.Frame:
        frame = tk.Frame(self.host, bg=C["bg_content"])

        hdr = tk.Frame(frame, bg=C["bg_content"])
        hdr.pack(fill=tk.X, padx=20, pady=(16, 4))
        tk.Label(hdr, text="集成测试",
                 font=("Microsoft YaHei", 15, "bold"),
                 bg=C["bg_content"], fg=C["fg_primary"]).pack(anchor="w")
        tk.Label(hdr,
                 text="各集成测试包含完整端到端流程，标注「自包含」的文件会自动登录，无需预先启动浏览器",
                 font=("Microsoft YaHei", 9),
                 bg=C["bg_content"], fg=C["fg_muted"]).pack(anchor="w")

        wrap = tk.Frame(frame, bg=C["bg_header"],
                        highlightthickness=1, highlightbackground=C["sep"])
        wrap.pack(fill=tk.X, padx=18, pady=(8, 4))

        self._make_header(wrap, [("文件名", 26), ("功能介绍", 57), ("操作", 8)])
        tk.Frame(wrap, height=1, bg=C["sep"]).pack(fill=tk.X)

        body = tk.Frame(wrap, bg=C["bg_content"])
        body.pack(fill=tk.X)

        for i, (fname, desc) in enumerate(INTEGRATION_FILES):
            bg = C["bg_row_a"] if i % 2 == 0 else C["bg_row_b"]
            row = tk.Frame(body, bg=bg)
            row.pack(fill=tk.X)
            tk.Frame(row, height=1, bg=C["sep"]).pack(fill=tk.X)
            inner = tk.Frame(row, bg=bg)
            inner.pack(fill=tk.X)

            tk.Label(inner, text=fname,
                     font=("Consolas", 9), bg=bg, fg=C["fg_code"],
                     anchor="w", padx=10, pady=7, width=26).grid(
                row=0, column=0, sticky="ew")
            tk.Label(inner, text=desc,
                     font=("Microsoft YaHei", 9), bg=bg, fg=C["fg_text"],
                     anchor="w", padx=10, pady=7,
                     wraplength=550, justify="left").grid(
                row=0, column=1, sticky="ew")

            running = self.btn_started.get(fname, False)
            btn = tk.Button(inner,
                            text="运行中" if running else "启动",
                            font=("Microsoft YaHei", 9, "bold"),
                            bg=C["btn_red"] if running else C["btn_green"],
                            fg="white",
                            activebackground=C["btn_red_h"] if running else C["btn_green_h"],
                            bd=0, relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                            command=lambda f=fname: self._launch_general(f, "integration"))
            btn.grid(row=0, column=2, padx=10, pady=5)
            self.page_buttons["integration"][fname] = btn
            inner.grid_columnconfigure(1, weight=1)

        self._build_output(frame, "integration").pack(
            fill=tk.BOTH, expand=True, padx=18, pady=(0, 10))
        return frame

    # ────────────────────────────────────────────────────────────
    # 数据组合测试页
    # ────────────────────────────────────────────────────────────

    def _build_data_page(self) -> tk.Frame:
        frame = tk.Frame(self.host, bg=C["bg_content"])

        hdr = tk.Frame(frame, bg=C["bg_content"])
        hdr.pack(fill=tk.X, padx=20, pady=(16, 4))
        tk.Label(hdr, text="数据组合测试",
                 font=("Microsoft YaHei", 15, "bold"),
                 bg=C["bg_content"], fg=C["fg_primary"]).pack(anchor="w")
        tk.Label(hdr,
                 text="多组测试数据覆盖各类场景，验证系统鲁棒性",
                 font=("Microsoft YaHei", 9),
                 bg=C["bg_content"], fg=C["fg_muted"]).pack(anchor="w")

        wrap = tk.Frame(frame, bg=C["bg_header"],
                        highlightthickness=1, highlightbackground=C["sep"])
        wrap.pack(fill=tk.X, padx=18, pady=(8, 4))

        self._make_header(wrap, [("文件名", 24), ("职责说明", 59), ("操作", 8)])
        tk.Frame(wrap, height=1, bg=C["sep"]).pack(fill=tk.X)

        body = tk.Frame(wrap, bg=C["bg_content"])
        body.pack(fill=tk.X)

        for i, (fname, desc) in enumerate(DATA_COMBO_FILES):
            bg = C["bg_row_a"] if i % 2 == 0 else C["bg_row_b"]
            row = tk.Frame(body, bg=bg)
            row.pack(fill=tk.X)
            tk.Frame(row, height=1, bg=C["sep"]).pack(fill=tk.X)
            inner = tk.Frame(row, bg=bg)
            inner.pack(fill=tk.X)

            tk.Label(inner, text=fname,
                     font=("Consolas", 9), bg=bg, fg=C["fg_code"],
                     anchor="w", padx=10, pady=7, width=24).grid(
                row=0, column=0, sticky="ew")
            tk.Label(inner, text=desc,
                     font=("Microsoft YaHei", 9), bg=bg, fg=C["fg_text"],
                     anchor="w", padx=10, pady=7,
                     wraplength=570, justify="left").grid(
                row=0, column=1, sticky="ew")

            running = self.btn_started.get(fname, False)
            btn = tk.Button(inner,
                            text="运行中" if running else "启动",
                            font=("Microsoft YaHei", 9, "bold"),
                            bg=C["btn_red"] if running else C["btn_green"],
                            fg="white",
                            activebackground=C["btn_red_h"] if running else C["btn_green_h"],
                            bd=0, relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                            command=lambda f=fname: self._launch_general(f, "data"))
            btn.grid(row=0, column=2, padx=10, pady=5)
            self.page_buttons["data"][fname] = btn
            inner.grid_columnconfigure(1, weight=1)

        self._build_output(frame, "data").pack(
            fill=tk.BOTH, expand=True, padx=18, pady=(0, 10))
        return frame

    # ────────────────────────────────────────────────────────────
    # 性能测试页
    # ────────────────────────────────────────────────────────────

    def _build_perf_page(self) -> tk.Frame:
        frame = tk.Frame(self.host, bg=C["bg_content"])

        hdr = tk.Frame(frame, bg=C["bg_content"])
        hdr.pack(fill=tk.X, padx=20, pady=(16, 4))
        tk.Label(hdr, text="性能测试",
                 font=("Microsoft YaHei", 15, "bold"),
                 bg=C["bg_content"], fg=C["fg_primary"]).pack(anchor="w")
        tk.Label(hdr,
                 text="并发线程压测邮件服务器，统计 TPS 与延迟分位数，无需预先登录",
                 font=("Microsoft YaHei", 9),
                 bg=C["bg_content"], fg=C["fg_muted"]).pack(anchor="w")

        wrap = tk.Frame(frame, bg=C["bg_header"],
                        highlightthickness=1, highlightbackground=C["sep"])
        wrap.pack(fill=tk.X, padx=18, pady=(8, 4))

        self._make_header(wrap, [("文件名", 18), ("测试说明", 65), ("操作", 8)])
        tk.Frame(wrap, height=1, bg=C["sep"]).pack(fill=tk.X)

        body = tk.Frame(wrap, bg=C["bg_content"])
        body.pack(fill=tk.X)

        for i, (fname, desc) in enumerate(PERF_FILES):
            bg = C["bg_row_a"] if i % 2 == 0 else C["bg_row_b"]
            row = tk.Frame(body, bg=bg)
            row.pack(fill=tk.X)
            tk.Frame(row, height=1, bg=C["sep"]).pack(fill=tk.X)
            inner = tk.Frame(row, bg=bg)
            inner.pack(fill=tk.X)

            tk.Label(inner, text=fname,
                     font=("Consolas", 9), bg=bg, fg=C["fg_code"],
                     anchor="w", padx=10, pady=7, width=18).grid(
                row=0, column=0, sticky="ew")
            tk.Label(inner, text=desc,
                     font=("Microsoft YaHei", 9), bg=bg, fg=C["fg_text"],
                     anchor="w", padx=10, pady=7,
                     wraplength=600, justify="left").grid(
                row=0, column=1, sticky="ew")

            running = self.btn_started.get(fname, False)
            btn = tk.Button(inner,
                            text="运行中" if running else "启动",
                            font=("Microsoft YaHei", 9, "bold"),
                            bg=C["btn_red"] if running else C["btn_green"],
                            fg="white",
                            activebackground=C["btn_red_h"] if running else C["btn_green_h"],
                            bd=0, relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                            command=lambda f=fname: self._launch_general(f, "perf"))
            btn.grid(row=0, column=2, padx=10, pady=5)
            self.page_buttons["perf"][fname] = btn
            inner.grid_columnconfigure(1, weight=1)

        self._build_output(frame, "perf").pack(
            fill=tk.BOTH, expand=True, padx=18, pady=(0, 10))
        return frame

    # ────────────────────────────────────────────────────────────
    # 输出区域工厂
    # ────────────────────────────────────────────────────────────

    def _build_output(self, parent, key: str) -> tk.Frame:
        container = tk.Frame(parent, bg=C["bg_header"],
                             highlightthickness=1, highlightbackground=C["sep"])

        bar = tk.Frame(container, bg=C["bg_header"])
        bar.pack(fill=tk.X, padx=8, pady=(5, 3))
        tk.Label(bar, text="▌ 输出结果",
                 font=("Microsoft YaHei", 9, "bold"),
                 bg=C["bg_header"], fg=C["fg_muted"]).pack(side=tk.LEFT)
        tk.Button(bar, text="清空",
                  font=("Microsoft YaHei", 8),
                  bg=C["bg_content"], fg=C["fg_muted"],
                  activebackground=C["sep"],
                  bd=0, padx=8, pady=2, cursor="hand2",
                  command=lambda k=key: self._clear(k)).pack(side=tk.RIGHT)

        tk.Frame(container, height=1, bg=C["sep"]).pack(fill=tk.X)

        inner = tk.Frame(container, bg=C["bg_output"])
        inner.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(inner,
                      bg=C["bg_output"], fg=C["fg_text"],
                      font=("Consolas", 9),
                      insertbackground="white",
                      selectbackground="#264f78",
                      bd=0, relief=tk.FLAT,
                      wrap=tk.WORD, state=tk.NORMAL)
        sb = ttk.Scrollbar(inner, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)

        txt.tag_configure("pass",  foreground="#7ee787")
        txt.tag_configure("fail",  foreground="#ff7b72")
        txt.tag_configure("error", foreground="#ffa657")
        txt.tag_configure("warn",  foreground="#f8e3a1")
        txt.tag_configure("info",  foreground="#79c0ff")
        txt.tag_configure("title", foreground="#f0f6fc",
                          font=("Consolas", 9, "bold"))

        self.output_widgets[key] = txt
        return container

    # ────────────────────────────────────────────────────────────
    # 子进程启动
    # ────────────────────────────────────────────────────────────

    def _launch_general(self, fname: str, page: str):
        proc = self.running_procs.get(fname)
        if proc and proc.poll() is None:
            self._append(page, f"\n[提示] {fname} 正在运行中\n\n", tag="warn")
            return

        self.btn_started[fname] = True
        self._refresh_page_buttons(page)
        self._append(page, f"\n{'─'*54}\n  启动  {fname}\n{'─'*54}\n")
        self._run_in_thread(fname, [PYTHON_EXE, os.path.join(BASE_DIR, fname)], page)

    def _run_in_thread(self, fname: str, cmd: list, page: str):
        def worker():
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            try:
                before = set(glob.glob(os.path.join(PIC_DIR, "*.png")))
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=BASE_DIR,
                    env=env,
                )
                self.running_procs[fname] = proc

                for line in proc.stdout:
                    self.output_queue.put((page, "text", line))

                proc.wait()

                after = set(glob.glob(os.path.join(PIC_DIR, "*.png")))
                for pic in sorted(after - before)[-4:]:
                    self.output_queue.put((page, "image", pic))

                self.output_queue.put((page, "text",
                    f"\n{'─'*54}\n  完成  {fname}（退出码 {proc.returncode}）\n{'─'*54}\n"))

            except Exception as exc:
                self.output_queue.put((page, "text", f"\n[异常] {fname}: {exc}\n"))
            finally:
                self.btn_started[fname] = False
                self.output_queue.put((page, "refresh", None))

        threading.Thread(target=worker, daemon=True).start()

    # ────────────────────────────────────────────────────────────
    # 队列轮询
    # ────────────────────────────────────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                page, kind, data = self.output_queue.get_nowait()
                if kind == "text":
                    self._append(page, data)
                elif kind == "image":
                    self._show_image(page, data)
                elif kind == "refresh":
                    self._render_single_body()
                    for pg in ("integration", "data", "perf"):
                        self._refresh_page_buttons(pg)
        except queue.Empty:
            pass
        self.root.after(80, self._poll_queue)

    def _refresh_page_buttons(self, page: str):
        for fname, btn in self.page_buttons.get(page, {}).items():
            running = self.btn_started.get(fname, False)
            try:
                btn.configure(
                    text="运行中" if running else "启动",
                    bg=C["btn_red"] if running else C["btn_green"],
                    activebackground=C["btn_red_h"] if running else C["btn_green_h"],
                )
            except tk.TclError:
                pass

    # ────────────────────────────────────────────────────────────
    # 输出工具
    # ────────────────────────────────────────────────────────────

    def _append(self, page: str, text: str, tag: str = None):
        txt = self.output_widgets.get(page)
        if not txt:
            return
        if tag is None:
            tag = self._detect_tag(text)
        txt.insert(tk.END, text, tag)
        txt.see(tk.END)

    @staticmethod
    def _detect_tag(line: str) -> str:
        s = line.lstrip()
        if s.startswith("[+]") or s.startswith("✓"):
            return "pass"
        if s.startswith("[-]"):
            return "fail"
        if s.startswith("[!]") or s.startswith("[异常]") or s.startswith("[错误]"):
            return "error"
        if s.startswith("[?]") or s.startswith("[提示]") or s.startswith("[警告]"):
            return "warn"
        if s.startswith("[*]") or s.startswith("  →"):
            return "info"
        if s.startswith("─") or s.startswith("  启动") or s.startswith("  完成"):
            return "title"
        return ""

    def _clear(self, page: str):
        txt = self.output_widgets.get(page)
        if txt:
            txt.delete(1.0, tk.END)

    def _show_image(self, page: str, path: str):
        txt = self.output_widgets.get(page)
        if not txt:
            return
        if not PIL_AVAILABLE:
            txt.insert(tk.END,
                f"\n[截图已保存] {os.path.basename(path)}\n"
                "  提示：pip install pillow 后可在此直接预览截图\n\n", "warn")
            txt.see(tk.END)
            return
        try:
            img = Image.open(path)
            max_w = 720
            w, h = img.size
            if w > max_w:
                img = img.resize((max_w, int(h * max_w / w)), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.image_refs.append(photo)
            txt.insert(tk.END, f"\n[截图] {os.path.basename(path)}\n", "info")
            txt.image_create(tk.END, image=photo)
            txt.insert(tk.END, "\n\n")
            txt.see(tk.END)
        except Exception as e:
            txt.insert(tk.END, f"\n[截图加载失败: {e}]\n", "error")
            txt.see(tk.END)


# ────────────────────────────────────────────────────────────────
# 入口
# ────────────────────────────────────────────────────────────────

def run():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    TestGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run()
