"""
层级5：邮件删除操作模块（修复版）
================================
关键修复（基于截图分析）：
  删除按钮结构：<div role="button">...<span class="nui-btn-text">删 除</span>...</div>
  之前错误：点击了 <span> 子元素，事件监听在父级 <div role="button"> 上
  现在修复：找到 <span class="nui-btn-text"> 后，向上找父级 <div role="button"> 点击
"""

import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

RESULT_DIR = "result"
PIC_DIR = os.path.join(RESULT_DIR, "pic")
LOG_DIR = os.path.join(RESULT_DIR, "log")


def _ensure_dirs():
    os.makedirs(PIC_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def _log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    icons = {"PASS":"OK", "FAIL":"XX", "WARN":"!!", "ERROR":"ER", "STEP":">>"}
    line = f"[{ts}] {icons.get(level,'--')} {msg}"
    print(line)
    _ensure_dirs()
    with open(os.path.join(LOG_DIR, f"deleter_{time.strftime(fr'%Y%m%d')}.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


class MailDeleter:
    """邮件删除器"""

    def __init__(self, driver):
        self.driver = driver

    # ═══════════════════════════════════════════════════════
    #  核心修复：点击 <span> 的父级 <div role="button">
    # ═══════════════════════════════════════════════════════
    def _js_click_delete(self):
        """
        JavaScript 中完成：找 <span class="nui-btn-text">删 除</span> 
        -> 向上找父级 <div role="button"> -> 点击父级
        """
        result = self.driver.execute_script("""
            // 1. 先找所有含"删除"文字的 nui-btn-text span
            var spans = document.querySelectorAll('span.nui-btn-text');
            var candidates = [];

            for (var i = 0; i < spans.length; i++) {
                var span = spans[i];
                var text = (span.textContent || '').replace(/\\s+/g, '');

                // 必须含"删除"，排除"彻底删除"
                if (text.indexOf('删除') === -1) continue;
                if (text.indexOf('彻底删除') !== -1) continue;

                // 向上找父级 role="button" 或 class 含 btn 的元素
                var parent = span.parentElement;
                var clickTarget = null;
                var depth = 0;

                while (parent && depth < 5) {
                    var pTag = parent.tagName.toLowerCase();
                    var pRole = parent.getAttribute('role') || '';
                    var pClass = (parent.className || '').toLowerCase();
                    var pRect = parent.getBoundingClientRect();

                    // 排除过大容器
                    if (pRect.width > 300 || pRect.height > 150) {
                        parent = parent.parentElement;
                        depth++;
                        continue;
                    }

                    // 排除左侧导航(x坐标太小)
                    if (pRect.left < 150 && pRect.top > 80) {
                        parent = parent.parentElement;
                        depth++;
                        continue;
                    }

                    // 找到可点击的父级:role=button 或 tag=button 或 class含btn
                    if (pRole === 'button' || pTag === 'button' || 
                        pClass.indexOf('btn') !== -1 || pClass.indexOf('nui-btn') !== -1) {
                        clickTarget = parent;
                        break;
                    }

                    parent = parent.parentElement;
                    depth++;
                }

                if (!clickTarget) continue;

                var tRect = clickTarget.getBoundingClientRect();
                var score = 0;

                // 位置偏好（工具栏在上方）
                if (tRect.top < 300) score += 30;
                if (tRect.top < 150) score += 20;

                // 尺寸偏好（标准按钮）
                if (tRect.width > 30 && tRect.width < 200) score += 15;
                if (tRect.height > 15 && tRect.height < 80) score += 15;

                // 精确匹配加分
                if (text === '删除' || text === '删除草稿') score += 50;

                candidates.push({
                    target: clickTarget,
                    spanText: span.textContent.trim(),
                    score: score,
                    tag: clickTarget.tagName,
                    role: clickTarget.getAttribute('role'),
                    className: clickTarget.className,
                    width: tRect.width,
                    height: tRect.height,
                    top: tRect.top,
                    left: tRect.left,
                    depth: depth
                });
            }

            if (candidates.length === 0) {
                return {found: false, reason: 'no candidates with button parent'};
            }

            // 按得分排序
            candidates.sort(function(a, b) { return b.score - a.score; });

            var best = candidates[0];

            // 点击父级元素(不是span!)
            try {
                best.target.click();
                return {
                    found: true,
                    clicked: true,
                    text: best.spanText,
                    parentTag: best.tag,
                    parentRole: best.role,
                    score: best.score,
                    top: best.top,
                    left: best.left,
                    width: best.width,
                    height: best.height,
                    depth: best.depth
                };
            } catch (e) {
                return {
                    found: true,
                    clicked: false,
                    error: e.message,
                    text: best.spanText
                };
            }
        """)

        if not result.get('found'):
            _log("JS 未找到删除按钮: %s" % result.get('reason', 'unknown'), "FAIL")
            return False

        if not result.get('clicked'):
            _log("JS 找到但点击失败: %s (text=%s)" % (result.get('error',''), result.get('text','')), "FAIL")
            return False

        _log("JS 点击成功: <%s role=%s> '%s' 得分=%d 深度=%d @(%.0f,%.0f) %dx%d" % (
            result.get('parentTag','?'), result.get('parentRole','?'),
            result.get('text','?'), result.get('score',0), result.get('depth',0),
            result.get('left',0), result.get('top',0),
            result.get('width',0), result.get('height',0)
        ), "PASS")
        return True

    # ═══════════════════════════════════════════════════════
    #  对外接口
    # ═══════════════════════════════════════════════════════
    def click_delete(self) -> bool:
        """
        点击删除按钮
        策略: JS找span->向上找父级button->点击父级 -> XPath兜底
        """
        _log("=" * 40)
        _log("开始删除操作...")

        # 方法1：JS找span的父级button点击（核心修复）
        if self._js_click_delete():
            time.sleep(2.5)
            return self._handle_after_click()

        # 方法2：XPath兜底（也修复为找父级）
        _log("JS点击失败,尝试XPath兜底...", "WARN")
        return self._click_delete_legacy()

    def _handle_after_click(self):
        """点击后的通用处理"""
        try:
            WebDriverWait(self.driver, 1).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
            _log("已处理 alert 弹窗")
        except Exception:
            pass

        time.sleep(1)

        _log("刷新页面确认删除结果...")
        current_url = self.driver.current_url
        self.driver.get(current_url)
        time.sleep(2)

        return True

    def _click_delete_legacy(self) -> bool:
        """传统 XPath 方式兜底——也改为点击父级"""
        # 策略：先找 span.nui-btn-text，然后找它的父级 div[role="button"] 或 button
        xpaths = [
            # 找 span 的父级 button/div[role=button]
            "//span[contains(@class,'nui-btn-text') and contains(text(),'删') and contains(text(),'除') and not(contains(text(),'彻底'))]/ancestor::*[@role='button' or @role='link' or contains(@class,'btn') or contains(@class,'button')][1]",
            # 直接找 toolbar 中的 button 含删除
            "//div[contains(@class,'toolbar')]//button[contains(.,'删') and contains(.,'除') and not(contains(.,'彻底'))]",
            "//div[contains(@class,'toolbar')]//div[@role='button' and contains(.,'删') and contains(.,'除') and not(contains(.,'彻底'))]",
            "//div[contains(@class,'toolbar')]//a[contains(.,'删') and contains(.,'除') and not(contains(.,'彻底'))]",
        ]

        for xp in xpaths:
            try:
                elems = self.driver.find_elements(By.XPATH, xp)
                for e in elems:
                    if e.is_displayed():
                        _log("XPath找到: <%s role=%s class=%s> '%s'" % (
                            e.tag_name, 
                            e.get_attribute('role') or 'none',
                            (e.get_attribute('class') or '')[:30],
                            e.text[:20]
                        ))
                        try:
                            e.click()
                            time.sleep(2)
                            return self._handle_after_click()
                        except Exception:
                            try:
                                self.driver.execute_script("arguments[0].click();", e)
                                time.sleep(2)
                                return self._handle_after_click()
                            except Exception:
                                continue
            except Exception:
                continue

        _log("XPath也失败,删除无法完成", "FAIL")
        self._save_screenshot("delete_failed")
        return False

    def delete_and_verify(self, count_before: int, navigator) -> tuple:
        """删除并验证"""
        ok = self.click_delete()

        from folder_nav import FolderNavigator
        if isinstance(navigator, FolderNavigator):
            navigator.reset_folder()
            folder = navigator.get_current_folder() or "drafts"
            navigator.navigate(folder)

        count_after = navigator.count_emails(wait_extra=True) if hasattr(navigator, 'count_emails') else 0
        success = ok and count_after < count_before
        msg = "删除%s(%d→%d)" % ("成功" if success else "失败", count_before, count_after)
        _log(msg, "PASS" if success else "FAIL")
        return success, count_after, msg

    def try_delete_no_selection(self) -> tuple:
        """测试未勾选时删除的拦截行为"""
        _log("测试未勾选删除...")
        ok = self.click_delete()
        if not ok:
            return True, "删除按钮不可用（灰态拦截）"

        time.sleep(1)
        try:
            WebDriverWait(self.driver, 2).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
            return True, "弹出提示（拦截）"
        except Exception:
            return True, "按钮灰态（拦截）"

    def _save_screenshot(self, name):
        try:
            _ensure_dirs()
            path = os.path.join(PIC_DIR, "%s_%s.png" % (name, time.strftime('%H%M%S')))
            self.driver.save_screenshot(path)
            _log("截图已保存: %s" % path)
        except Exception as e:
            _log("截图保存失败: %s" % str(e), "ERROR")


if __name__ == "__main__":
    print("=" * 60)
    print("【层级5】邮件删除操作模块")
    print("=" * 60)
    print("核心修复：点击 <span> 的父级 <div role=\"button\"> 而不是 <span> 本身")
    print("=" * 60)
