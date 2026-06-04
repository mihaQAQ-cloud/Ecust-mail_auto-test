"""
测试数据准备模块
职责：在测试前自动创建草稿箱/已发送的测试数据
被主控程序调用
"""

import time
from compose_connect import get_connector, ComposeManager
from folder_nav import FolderNavigator


class TestDataPreparer:
    """测试数据准备器"""

    def __init__(self, driver, sid):
        self.driver = driver
        self.sid = sid
        self.nav = FolderNavigator(driver, sid)
        self.compose = ComposeManager(get_connector())
        self._self_email = self.compose._self_email

    def prepare(self, min_drafts=3, min_sent=2):
        """
        准备测试数据
        确保草稿箱至少有 min_drafts 封，已发送至少有 min_sent 封
        """
        print("\n" + "="*50)
        print("  前置检查：检测草稿箱和已发送是否有数据...")
        print("="*50)

        # 读导航标签计数
        draft_nav = self.nav.get_nav_count("草稿箱")
        sent_nav = self.nav.get_nav_count("已发送")
        print(f"[DATA] 导航标签计数 → 草稿箱={draft_nav}封, 已发送={sent_nav}封")

        # 草稿箱
        if draft_nav > 0:
            need_draft = False
        else:
            self.nav.navigate("drafts")
            time.sleep(1)
            cnt = self.nav.count_emails(wait_extra=True)
            need_draft = (cnt == 0)
            print(f"[DATA] 草稿箱DOM计数={cnt}封")

        # 已发送
        if sent_nav > 0:
            need_sent = False
        else:
            self.nav.navigate("sent")
            time.sleep(1)
            cnt = self.nav.count_emails(wait_extra=True)
            need_sent = (cnt == 0)
            print(f"[DATA] 已发送DOM计数={cnt}封")

        if not need_draft and not need_sent:
            print("[DATA] 两个文件夹均有邮件，无需创建测试数据 ✓")
            self.nav.reset_folder()
            return

        if need_draft:
            print(f"[DATA] 草稿箱为空，创建{min_drafts}封草稿...")
            for i in range(1, min_drafts + 1):
                self.compose.write_mail(
                    f"自动化测试草稿{i} {time.strftime('%H:%M:%S')}",
                    save_as_draft=True)
            self.nav.navigate("drafts")
            cnt = self.nav.count_emails(wait_extra=True)
            print(f"[DATA] 草稿准备完成(数量={cnt})")

        if need_sent:
            print(f"[DATA] 已发送为空，发送{min_sent}封邮件给自己...")
            for i in range(1, min_sent + 1):
                self.compose.write_mail(
                    f"自动化测试邮件{i} {time.strftime('%H:%M:%S')}",
                    save_as_draft=False)
            self.nav.navigate("sent")
            cnt = self.nav.count_emails(wait_extra=True)
            print(f"[DATA] 已发送准备完成(数量={cnt})")

        self.nav.reset_folder()
        print("[DATA] 前置准备完成")
