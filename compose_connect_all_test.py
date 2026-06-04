"""
华理邮箱自动化测试完整整合版
功能：连接调试浏览器 → 进入写信页面 → 收件人/主题/正文/附件/发送/返回 全流程测试
"""

import time
import json
import os
import re
import sys
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException

SESSION_FILE = "browser_session.json"

LOG_DIR = fr"result/log"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, time.strftime(fr"compose_test_%Y%m%d_%H%M%S") + ".txt")
_log_fp = open(LOG_FILE, "w", encoding="utf-8")

def _write_log(msg):
    """同时打印到终端并写入日志文件"""
    print(msg)
    _log_fp.write(msg + "\n")
    _log_fp.flush()

def connect_to_existing_browser():
    """连接到第一个文件打开的浏览器"""
    if not os.path.exists(SESSION_FILE):
        _write_log("="*60)
        _write_log("[-] 错误：未找到会话文件，请先运行 single_login.py")
        _write_log("="*60)
        return None, None

    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        session = json.load(f)

    debug_port = session.get("debug_port", 9223)
    sid = session.get("sid", "")

    _write_log("="*60)
    _write_log("第二步：连接到已打开的浏览器")
    _write_log("="*60)
    _write_log(f"[*] 调试端口: {debug_port}")
    _write_log(f"[*] sid: {sid[:30]}..." if len(sid) > 30 else f"[*] sid: {sid}")
    _write_log("-"*60)

    options = Options()
    options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")

    try:
        driver = webdriver.Edge(options=options)
        _write_log(f"[+] 成功连接到已打开的浏览器！")
        _write_log(f"[+] 当前页面标题: {driver.title}")
        _write_log(f"[+] 当前URL: {driver.current_url[:80]}...")

        if "main.jsp" in driver.current_url:
            _write_log("[+] 确认：已登录状态")
        else:
            _write_log("[?] 警告：可能未登录或已退出")

        return driver, sid

    except Exception as e:
        _write_log(f"[-] 连接失败: {e}")
        _write_log("[-] 可能原因：浏览器已关闭、调试端口错误或浏览器崩溃")
        _write_log("\n[*] 解决方式：重新运行第一个脚本登录")
        return None, None


class ComposeTester:
    """写信页面完整测试器（整合版）"""

    def __init__(self, driver):
        self.driver = driver
        self.debug_dir = "debug_info"
        os.makedirs(self.debug_dir, exist_ok=True)
        self.log_file = _log_fp

        # ========== 附件测试配置（来自 attachment_test.py）==========
        self.attachment_dir = os.path.abspath(fr"resource")
        # 正确格式：期望上传成功
        self.default_specs = [
            ("png", "01"), ("txt", "01"), ("zip", "01"),
            ("pptx", "01"), ("html", "01"),
        ]
        # 错误格式：期望上传被系统拒绝
        self.invalid_specs = [("bat", "01"), ("js", "01")]
        self.specified_files = []          # 用户指定的正确附件
        self.specified_invalid_files = []  # 用户指定的错误附件
        self.test_invalid = True           # 是否测试错误格式

    def log(self, msg, level="INFO"):
        timestamp = time.strftime("%H:%M:%S")
        prefix = {"INFO": "[*]", "PASS": "[+]", "FAIL": "[-]", "ERROR": "[!]", "WARN": "[?]"}
        line = f"{timestamp} {prefix.get(level, '[*]')} {msg}"
        print(line)
        self.log_file.write(line + "\n")
        self.log_file.flush()

    def save_debug_info(self, prefix="debug"):
        """保存调试信息（截图+页面源码）"""
        try:
            timestamp = time.strftime(fr"%Y%m%d_%H%M%S")
            screenshot = os.path.join(self.debug_dir, f"{prefix}_{timestamp}.png")
            source = os.path.join(self.debug_dir, f"{prefix}_{timestamp}.html")

            self.driver.save_screenshot(screenshot)
            with open(source, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)

            self.log(f"调试信息已保存: {screenshot}, {source}", "INFO")
            return screenshot, source
        except Exception as e:
            self.log(f"保存调试信息失败: {e}", "ERROR")
            return None, None

    def close_log(self):
        """关闭日志文件"""
        global _log_fp
        if _log_fp and not _log_fp.closed:
            _log_fp.close()
            _log_fp = None

    # ==================== 页面导航 ====================

    def enter_compose_by_url(self, sid):
        """通过 sid 进入写信页面"""
        if not sid:
            self.log("缺少 sid,尝试从当前URL提取", "WARN")
            current_url = self.driver.current_url
            sid_match = re.search(r'sid=([^&]+)', current_url)
            if sid_match:
                sid = sid_match.group(1)
                self.log(f"从当前URL提取sid: {sid[:20]}...")
            else:
                self.log("无法获取sid", "ERROR")
                return False

        compose_url = f"https://stu.mail.ecust.edu.cn/js6/main.jsp?sid={sid}&show_new=1&hl=zh_CN#module=compose.ComposeModule%7C%7B%7D"

        self.log(f"正在打开写信页面...")
        self.driver.get(compose_url)
        time.sleep(5)

        current_url = self.driver.current_url
        self.log(f"当前URL: {current_url[:80]}...")

        if "compose" in current_url or self.is_compose_page():
            self.log("成功进入写信页面", "PASS")
            return True
        else:
            self.log("进入写信页面失败,sid可能已过期", "FAIL")
            self.save_debug_info("enter_compose_fail")
            return False

    def is_compose_page(self):
        """检查是否在写信页面"""
        indicators = [
            "//*[contains(text(),'收件人')]",
            "//*[contains(text(),'主题')]",
            "//*[contains(text(),'发送')]",
            "//div[contains(@class,'compose')]",
            "//div[@contenteditable='true']",
            "//iframe"
        ]
        for xpath in indicators:
            try:
                self.driver.find_element(By.XPATH, xpath)
                return True
            except:
                continue
        return False

    def verify_compose_page(self):
        """验证当前页面是否为写信页面（用于返回后检测）"""
        self.log("[*] 验证是否成功返回写信页面...")
        compose_indicators = [
            "//*[contains(text(),'收件人')]",
            "//*[contains(text(),'主题')]",
            "//*[contains(text(),'发送')]",
            "//div[contains(@class,'compose')]",
            "//div[@contenteditable='true']",
            "//iframe",
            "//div[contains(@class,'nui-mainBtn') and contains(.,'发送')]",
        ]
        found_count = 0
        for xpath in compose_indicators:
            try:
                self.driver.find_element(By.XPATH, xpath)
                found_count += 1
            except:
                continue

        current_url = self.driver.current_url
        self.log(f"[*] 当前URL: {current_url[:80]}...")
        self.log(f"[*] 写信页面指标命中: {found_count}/{len(compose_indicators)}")

        if found_count >= 3 or "compose" in current_url:
            self.log("成功返回写信页面", "PASS")
            return True
        else:
            self.log("未能确认已返回写信页面", "FAIL")
            return False

    # ==================== 通用工具方法 ====================

    def safe_click(self, element, desc="元素"):
        """安全点击封装：先尝试普通点击，失败则用 JS 点击"""
        try:
            element.click()
            self.log(f"已点击{desc}（普通点击）", "PASS")
            return True
        except Exception as click_err:
            self.log(f"普通点击失败: {str(click_err)[:80]}，尝试 JS 点击...", "WARN")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                self.log(f"已点击{desc}（JS 点击）", "PASS")
                return True
            except Exception as js_err:
                self.log(f"JS 点击也失败: {js_err}", "ERROR")
                return False

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
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.3)
        except:
            pass

    # ==================== 收件人测试 ====================

    def test_recipient(self, value="23070066@mail.ecust.edu.cn"):
        """测试收件人输入（基于实际 DOM 结构最终修正）"""
        self.log(f"\n[*] 测试收件人输入: '{value}'")

        # 方法1: 容器内空白区点击输入
        try:
            self.log("方法1: 容器内空白区点击输入...", "INFO")
            label = self.driver.find_element(By.XPATH, "//*[contains(text(),'收件人')]")
            self.log(f"  找到标签: tag={label.tag_name}, text='{label.text[:20]}'")

            container = label
            for i in range(3):
                parent = container.find_element(By.XPATH, "..")
                size = parent.size
                self.log(f"    ancestor[{i+1}]: tag={parent.tag_name}, size={size}")
                if size['width'] > 300:
                    container = parent
                    break
                container = parent

            self.log(f"  选中容器: tag={container.tag_name}, size={container.size}")
            children = container.find_elements(By.XPATH, ".//*")
            target = None

            for child in children:
                try:
                    child_text = (child.text or "").strip()
                    tag = child.tag_name
                    disp = child.is_displayed()
                    size = child.size
                    if "收件人" in child_text:
                        continue
                    if disp and size['width'] > 50 and size['height'] > 10:
                        inner_count = len(child.find_elements(By.XPATH, "./*"))
                        if inner_count < 3:
                            target = child
                            self.log(f"  找到目标: tag={tag}, size={size}, text='{child_text[:20]}', inner={inner_count}")
                            break
                except:
                    continue

            if target:
                target.click()
                time.sleep(0.5)
                try:
                    target.clear()
                    target.send_keys(value)
                    self.log("收件人输入成功(目标 send_keys)", "PASS")
                    return True
                except:
                    pass
                try:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(target).click().pause(0.3).send_keys(value).perform()
                    self.log("收件人输入成功（目标 ActionChains）", "PASS")
                    return True
                except Exception as e:
                    self.log(f"  目标 ActionChains 失败: {str(e)[:80]}", "WARN")
            else:
                self.log("  容器内未找到合适的空白子元素", "WARN")
        except Exception as e:
            self.log(f"方法1失败: {str(e)[:100]}", "WARN")

        # 方法2: 坐标偏移点击输入
        try:
            self.log("方法2: 坐标偏移点击输入...", "INFO")
            label = self.driver.find_element(By.XPATH, "//*[contains(text(),'收件人')]")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
            time.sleep(0.5)

            loc = label.location
            sz = label.size
            self.log(f"  标签位置: {loc}, 尺寸: {sz}")

            offset_x = sz['width'] / 2 + 80
            offset_y = 0
            self.log(f"  偏移: ({offset_x}, {offset_y})")

            actions = ActionChains(self.driver)
            actions.move_to_element(label).move_by_offset(offset_x, offset_y).click().pause(0.5)
            actions.send_keys(value).perform()
            time.sleep(0.5)

            self.log("收件人输入成功（坐标偏移）", "PASS")
            return True
        except Exception as e:
            self.log(f"方法2失败: {str(e)[:100]}", "WARN")

        # 方法3: JS 评分找目标并强制设置
        try:
            self.log("方法3: JS 评分找目标...", "INFO")
            result = self.driver.execute_script("""
                var val = arguments[0];
                var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                var textNode = null;
                while (walker.nextNode()) {
                    if (walker.currentNode.textContent.indexOf('收件人') >= 0) {
                        textNode = walker.currentNode;
                        break;
                    }
                }
                if (!textNode) return 'no_text_node';

                var parent = textNode.parentElement;
                var bestTarget = null;
                var bestScore = -999;

                while (parent && parent !== document.body) {
                    var children = parent.querySelectorAll('*');
                    for (var i = 0; i < children.length; i++) {
                        var child = children[i];
                        var rect = child.getBoundingClientRect();
                        var style = window.getComputedStyle(child);
                        var score = 0;

                        if (rect.width > 200) score += 30;
                        else if (rect.width > 100) score += 20;
                        else if (rect.width > 50) score += 10;

                        if (rect.height > 20) score += 20;
                        else if (rect.height > 10) score += 10;

                        if (style.display !== 'none') score += 25;
                        if (style.visibility !== 'hidden') score += 25;

                        var txt = child.textContent.trim();
                        if (txt.length === 0) score += 30;
                        else if (txt.length < 5) score += 15;

                        if (child.getAttribute('contenteditable') === 'true') score += 100;
                        if (child.tagName === 'INPUT' || child.tagName === 'TEXTAREA') score += 40;
                        if (txt.indexOf('收件人') >= 0) score -= 200;
                        if (child.children.length > 5) score -= 20;

                        if (score > bestScore) {
                            bestScore = score;
                            bestTarget = child;
                        }
                    }
                    if (bestTarget && bestScore > 80) break;
                    parent = parent.parentElement;
                }

                if (!bestTarget || bestScore < 50) return 'no_target: bestScore=' + bestScore;

                bestTarget.focus();
                bestTarget.click();

                if (bestTarget.tagName === 'INPUT' || bestTarget.tagName === 'TEXTAREA') {
                    bestTarget.value = val;
                } else if (bestTarget.getAttribute('contenteditable') === 'true') {
                    bestTarget.innerHTML = val;
                } else {
                    bestTarget.textContent = val;
                    if (bestTarget.textContent !== val) {
                        bestTarget.innerHTML = val;
                    }
                }

                var events = ['focus','click','keydown','keypress','input','keyup','change','blur'];
                events.forEach(function(evtName) {
                    var evt = new Event(evtName, { bubbles: true, cancelable: true });
                    bestTarget.dispatchEvent(evt);
                });

                return 'ok:' + bestTarget.tagName + '|score:' + bestScore + '|class:' + (bestTarget.className || 'none');
            """, value)

            self.log(f"  JS 结果: {result}", "INFO")
            time.sleep(1)
            if result and result.startswith('ok:'):
                self.log("收件人输入成功(JS 评分强制)", "PASS")
                self.driver.save_screenshot(os.path.join(self.debug_dir, "recipient_js_ok.png"))
                return True
        except Exception as e:
            self.log(f"方法3失败: {str(e)[:100]}", "ERROR")

        self.log("所有收件人输入方法均失败", "FAIL")
        self.save_debug_info("recipient_all_fail")
        return False

    # ==================== 主题测试（整合 theme_test.py）====================

    def test_subject(self, value="自动化测试邮件"):
        """测试主题输入（增强版，整合 theme_test.py 策略）"""
        self.log(f"\n[*] 测试主题输入: '{value}'")

        strategies = [
            (By.XPATH, "//input[contains(@placeholder,'主题')]"),
            (By.XPATH, "//input[@type='text' and (contains(@id,'subject') or contains(@name,'subject'))]"),
            (By.XPATH, "//div[contains(text(),'主题')]/following::input[1]"),
            (By.CSS_SELECTOR, "input[placeholder*='主题']"),
        ]

        elem = None
        for i, (by, val) in enumerate(strategies, 1):
            try:
                self.log(f"  尝试 {i}/{len(strategies)}: {val[:50]}...")
                elem = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((by, val))
                )
                if elem.is_displayed() and elem.is_enabled():
                    self.log(f"  找到主题输入框", "PASS")
                    break
                else:
                    elem = None
            except:
                continue

        if not elem:
            self.log("未找到主题输入框", "ERROR")
            return False

        try:
            elem.clear()
            elem.send_keys(value)
            time.sleep(0.5)
            actual = elem.get_attribute("value")
            if actual == value:
                self.log(f"主题输入成功: {actual}", "PASS")
                return True
            else:
                self.log(f"输入不匹配: 期望'{value}', 实际'{actual}'", "FAIL")
                return False
        except Exception as e:
            self.log(f"主题输入失败: {e}", "ERROR")
            return False

    # ==================== 正文测试 ====================

    def test_content(self, value=None):
        """测试正文输入"""
        if value is None:
            value = "这是一封由自动化测试工具发送的测试邮件。\n测试时间:" + time.strftime(fr"%Y-%m-%d %H:%M:%S")

        self.log(f"\n[*] 测试正文输入")

        # 策略1: 直接 textarea
        try:
            elem = self.driver.find_element(By.XPATH, "//textarea[contains(@placeholder,'正文')]")
            if elem.is_displayed():
                elem.clear()
                elem.send_keys(value)
                self.log("正文输入成功(textarea)", "PASS")
                return True
        except:
            pass

        # 策略2: iframe 富文本编辑器
        self.log("尝试查找富文本编辑器 iframe...")
        self.driver.switch_to.default_content()
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        self.log(f"发现 {len(iframes)} 个 iframe")

        for idx, iframe in enumerate(iframes):
            try:
                if not iframe.is_displayed():
                    continue
                self.driver.switch_to.frame(iframe)
                self.log(f"  检查 iframe {idx}...")

                try:
                    body = self.driver.find_element(By.XPATH, "//body[@contenteditable='true'] | //body")
                    body.click()
                    time.sleep(0.3)
                    body.clear()

                    lines = value.split('\n')
                    for i, line in enumerate(lines):
                        if i > 0:
                            body.send_keys(Keys.RETURN)
                        body.send_keys(line)
                        time.sleep(0.1)

                    time.sleep(0.5)
                    self.driver.switch_to.default_content()
                    self.log(f"正文输入成功（iframe {idx} 编辑器）", "PASS")
                    return True
                except Exception as e:
                    self.log(f"  iframe {idx} body 输入失败: {str(e)[:80]}", "WARN")

                self.driver.switch_to.default_content()
            except Exception as e:
                self.log(f"  iframe {idx} 异常: {str(e)[:80]}", "WARN")
                self.driver.switch_to.default_content()
                continue

        # 策略3: contenteditable div
        self.driver.switch_to.default_content()
        try:
            elem = self.driver.find_element(By.XPATH, "//div[@contenteditable='true']")
            if elem.is_displayed():
                elem.click()
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].innerHTML = arguments[1];", elem, value.replace("\n", "<br>"))
                self.log("正文输入成功（contenteditable）", "PASS")
                return True
        except:
            pass

        self.log("所有正文输入方式失败", "FAIL")
        self.save_debug_info("content_fail")
        return False

    # ==================== 发送按钮测试（整合 button_test.py）====================

    def handle_no_subject_dialog(self):
        """处理'确定真的不需要写主题吗？'弹窗"""
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

        confirm_btn = None
        confirm_strategies = [
            (By.XPATH, "//div[contains(@class,'nui-mainBtn') and @role='button']//span[contains(text(),'确') and contains(text(),'定')]/parent::div[@role='button']"),
            (By.XPATH, "//div[contains(@class,'nui-mainBtn') and @role='button']//span[contains(text(),'确') and contains(text(),'定')]"),
            (By.XPATH, "//div[contains(@class,'nui-mainBtn') and contains(.,'确') and contains(.,'定')]"),
            (By.XPATH, "//div[@role='button' and contains(.,'确') and contains(.,'定')]"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'确') and contains(text(),'定')]/ancestor::div[@role='button'][1]"),
            (By.XPATH, "//div[contains(@class,'dialog') or contains(@class,'popup') or contains(@class,'modal')]//div[@role='button' and contains(.,'确') and contains(.,'定')]"),
            (By.XPATH, "//button[contains(text(),'确') and contains(text(),'定')]"),
            (By.XPATH, "//a[contains(text(),'确') and contains(text(),'定')]"),
            (By.XPATH, "//*[contains(text(),'确') and contains(text(),'定') and (@role='button' or self::button or self::a)]"),
            (By.XPATH, "//span[contains(text(),'确') and contains(text(),'定')]"),
            (By.XPATH, "//div[@role='button' and contains(text(),'确')]"),
            (By.XPATH, "//button[contains(text(),'确')]"),
        ]

        for i, (by, val) in enumerate(confirm_strategies, 1):
            try:
                candidates = self.driver.find_elements(by, val)
                for candidate in candidates:
                    if candidate.is_displayed():
                        text = (candidate.text or candidate.get_attribute("textContent") or "").replace("\n", "").replace("\t", "").strip()
                        if "确" in text and "定" in text and "取消" not in text and len(text) <= 6:
                            confirm_btn = candidate
                            self.log(f"找到确定按钮（策略{i}）: tag={candidate.tag_name}, class={candidate.get_attribute('class')[:50]}, text='{text}'")
                            break
                if confirm_btn:
                    break
            except Exception:
                continue

        # JS 终极兜底
        if not confirm_btn:
            self.log("XPath 策略全部失败，尝试 JS 终极兜底...", "WARN")
            try:
                script = """
                    var allElements = document.querySelectorAll('div[role="button"], button, a');
                    for (var i = 0; i < allElements.length; i++) {
                        var el = allElements[i];
                        var text = (el.textContent || el.innerText || '').replace(/\\s+/g, ' ').trim();
                        if (text.includes('确') && text.includes('定') && !text.includes('取消')) {
                            var rect = el.getBoundingClientRect();
                            if (rect.width > 20 && rect.height > 10 && rect.top > 0 && rect.left > 0) {
                                if (text.length <= 6) return el;
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
        """测试发送按钮（整合 button_test.py 完整逻辑）"""
        self.log(f"\n[*] 测试发送按钮 (实际发送: {actually_send})")

        self.dismiss_popup()

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
            self.save_debug_info("send_btn_fail")
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

    # ==================== 附件测试（整合 attachment_test.py）====================

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
        """设置是否测试错误格式（True=测试，False=跳过）"""
        self.test_invalid = flag
        self.log(f"错误格式测试开关: {flag}")

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

    def check_error_dialog(self):
        """检测是否有错误/警告弹窗，返回弹窗文本内容，没有则返回 None"""
        dialog_indicators = [
            "//*[contains(text(),'附件上传提示')]",
            "//*[contains(text(),'您选择的文件不能上传')]",
            "//*[contains(text(),'文件类型受限')]",
            "//*[contains(text(),'不能上传')]",
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
                    return text.strip()[:50]
            except:
                continue
        return None

    def dismiss_error_dialog(self):
        """关闭错误弹窗（点击确定/关闭按钮）"""
        dismiss_strategies = [
            (By.XPATH, "//div[contains(@class,'nui-msgbox-ft-btns')]//div[contains(@class,'nui-mainBtn') and @role='button']//span[contains(text(),'确') and contains(text(),'定')]/parent::div[@role='button']"),
            (By.XPATH, "//div[contains(@class,'nui-msgbox-ft-btns')]//div[contains(@class,'nui-mainBtn') and @role='button']"),
            (By.XPATH, "//div[contains(@class,'nui-msgbox-ft-btns')]//div[@role='button' and contains(.,'确') and contains(.,'定')]"),
            (By.XPATH, "//div[contains(@class,'nui-msgbox-ft-btns')]//span[contains(text(),'确') and contains(text(),'定')]"),
            (By.XPATH, "//div[contains(@class,'msgbox')]//div[contains(@class,'nui-mainBtn') and @role='button']"),
            (By.XPATH, "//div[contains(@class,'msgbox')]//div[@role='button' and contains(.,'确') and contains(.,'定')]"),
            (By.XPATH, "//div[contains(@class,'dialog')]//div[@role='button' and contains(.,'确') and contains(.,'定')]"),
            (By.XPATH, "//div[contains(@class,'dialog')]//button[contains(text(),'确定')]"),
            (By.XPATH, "//div[contains(@class,'dialog')]//span[contains(text(),'关闭')]/parent::*"),
            (By.XPATH, "//div[contains(@class,'dialog')]//a[contains(text(),'关闭')]"),
            (By.XPATH, "//div[contains(@class,'dialog')]//div[contains(@class,'close')]"),
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
                        if "确" in text and "定" in text and "取消" not in text and len(text) <= 6:
                            self.log(f"找到弹窗确定按钮（策略{i}）: text='{text}', class={btn.get_attribute('class')[:50]}")
                            self.safe_click(btn, "弹窗'确定'按钮")
                            time.sleep(1)
                            return True
            except Exception:
                continue

        # 尝试 ESC 关闭
        try:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            self.log("已按 ESC 关闭弹窗")
            return True
        except:
            pass

        self.log("未能关闭弹窗", "ERROR")
        return False

    def upload_single_file(self, filepath, expect_success=True):
        """上传单个文件并验证"""
        filepath = os.path.abspath(filepath)
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

    def test_default_attachments(self):
        """测试默认的 5 种正确格式附件（期望成功）"""
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

    def test_attachments(self):
        """运行附件测试主入口（正确格式 + 错误格式）"""
        self.log("\n" + "=" * 60)
        self.log("【附件添加测试】（正确格式 + 错误格式）")
        self.log("=" * 60)
        self.log(f"附件目录: {self.attachment_dir}")

        # 阶段一：正确格式
        self.log("\n" + "=" * 60)
        self.log("【阶段一】测试正确格式附件（期望: 上传成功）")
        self.log("=" * 60)

        if self.specified_files:
            self.log(f"[*] 使用指定正确附件列表，共 {len(self.specified_files)} 个")
            valid_result = self.test_specified_attachments(self.specified_files)
        else:
            self.log("[*] 使用默认正确附件规格列表 (png/txt/zip/pptx/html)")
            valid_result = self.test_default_attachments()

        # 阶段二：错误格式
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

        # 汇总
        self.log("\n" + "=" * 60)
        self.log("【附件测试汇总】")
        self.log("=" * 60)
        self.log(f"正确格式测试: {'PASS' if valid_result else 'FAIL'}", "PASS" if valid_result else "FAIL")
        self.log(f"错误格式测试: {'PASS' if invalid_result else 'FAIL'}", "PASS" if invalid_result else "FAIL")

        overall = valid_result and invalid_result
        self.log(f"附件总测试结果: {'PASS' if overall else 'FAIL'}", "PASS" if overall else "FAIL")
        return overall

    # ==================== 返回写信页测试（整合 return_write.py）====================

    def is_send_success_page(self):
        """检测当前是否是发送成功页面"""
        indicators = [
            "//*[contains(text(),'发送成功')]",
            "//*[contains(text(),'已成功发送到收件人')]",
            "//a[contains(text(),'继续写信')]",
            "//a[contains(text(),'返回收件箱')]",
            "//a[contains(text(),'查看已发邮件')]",
        ]
        found_count = 0
        for xpath in indicators:
            try:
                self.driver.find_element(By.XPATH, xpath)
                found_count += 1
            except:
                continue

        if found_count >= 2:
            self.log(f"当前为发送成功页面（命中 {found_count} 个指标）")
            return True
        else:
            self.log(f"当前不是发送成功页面（仅命中 {found_count} 个指标）")
            return False

    def return_to_compose(self):
        """点击'继续写信'按钮，返回写信页面（发送成功后）"""
        self.log("\n[*] 开始返回写信页面流程")

        if not self.is_send_success_page():
            self.log("当前页面不是发送成功页面，尝试继续执行...", "WARN")

        self.log("[*] 查找'继续写信'按钮...")

        continue_btn = None
        strategies = [
            (By.XPATH, "//a[contains(@class,'js-component-link')]//b[contains(@class,'nui-ico')]/parent::a[contains(.,'继续写信')]"),
            (By.XPATH, "//a[contains(@class,'js-component-link') and contains(.,'继续写信')]"),
            (By.XPATH, "//a[contains(text(),'继续写信')]"),
            (By.XPATH, "//span[contains(text(),'继续写信')]/parent::a"),
            (By.XPATH, "//a[contains(.,'继续写信')]"),
            (By.XPATH, "//a[.//b[contains(@class,'nui-ico')] and contains(.,'继续写信')]"),
            (By.XPATH, "//*[contains(text(),'继续写信') and (@role='button' or self::button or self::a)]"),
            (By.XPATH, "//span[contains(text(),'继续写信')]"),
        ]

        for i, (by, val) in enumerate(strategies, 1):
            try:
                self.log(f"  尝试 {i}/{len(strategies)}: {val[:60]}...")
                continue_btn = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((by, val))
                )
                if continue_btn.is_displayed():
                    tag = continue_btn.tag_name
                    class_attr = continue_btn.get_attribute("class") or ""
                    text = continue_btn.text or continue_btn.get_attribute("textContent") or ""
                    self.log(f"  找到元素: tag={tag}, class={class_attr[:50]}, text='{text.strip()}'")
                    break
                else:
                    continue_btn = None
            except Exception:
                continue

        if not continue_btn:
            self.log("未找到'继续写信'按钮", "FAIL")
            return False

        self.log("[*] 点击'继续写信'按钮...")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_btn)
        time.sleep(0.3)

        clicked = self.safe_click(continue_btn, "'继续写信'按钮")
        if not clicked:
            return False

        self.log("[*] 等待页面跳转...")
        time.sleep(3)

        return self.verify_compose_page()

    # ==================== 主控流程 ====================

    def run_all_tests(self, actually_send=False, test_attachment=False, auto_return=False):
        """
        运行所有写信页面测试
        
        参数:
            actually_send: 是否实际点击发送（True=真发送，False=仅检测按钮）
            test_attachment: 是否测试附件上传
            auto_return: 发送成功后是否自动点击"继续写信"返回
        """
        self.log("="*60)
        self.log("开始写信页面完整测试（整合版）")
        self.log("="*60)

        results = []

        # 1. 收件人
        results.append(("收件人输入", self.test_recipient()))
        time.sleep(1)

        # 2. 主题
        results.append(("主题输入", self.test_subject()))
        time.sleep(1)

        # 3. 正文
        results.append(("正文输入", self.test_content()))
        time.sleep(1)

        # 4. 附件（可选）
        if test_attachment:
            results.append(("附件上传", self.test_attachments()))
            time.sleep(1)

        # 5. 发送按钮
        results.append(("发送按钮", self.test_send_button(actually_send)))

        # 6. 发送成功后返回（可选）
        if actually_send and auto_return:
            results.append(("返回写信页", self.return_to_compose()))

        # 保存结果截图
        try:
            pic_dir = fr"result\pic"
            os.makedirs(pic_dir, exist_ok=True)
            screenshot = os.path.join(pic_dir, time.strftime(fr"compose_test_result_%Y%m%d_%H%M%S") + ".png")
            self.driver.save_screenshot(screenshot)
            self.log(f"\n[+] 结果截图已保存: {screenshot}")
        except Exception as e:
            self.log(f"截图保存失败: {e}", "WARN")

        # 汇总报告
        self.log("\n" + "="*60)
        self.log("测试结果汇总")
        self.log("="*60)

        passed = sum(1 for _, r in results if r)
        total = len(results)

        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            self.log(f"  {status}: {name}")

        self.log(f"\n总计: {total} | 通过: {passed} | 失败: {total-passed}")
        if total > 0:
            self.log(f"通过率: {passed/total*100:.1f}%")

        return results


def main():
    """主程序"""
    driver, sid = connect_to_existing_browser()

    if not driver:
        input("\n按回车键退出...")
        return

    tester = ComposeTester(driver)

    try:
        if tester.enter_compose_by_url(sid):

            # ========== 运行配置 ==========
            # actually_send=True  : 实际发送邮件（会触发无主题弹窗、进入发送成功页）
            # test_attachment=True: 测试附件上传（正确格式+错误格式）
            # auto_return=True    : 发送成功后自动点击"继续写信"返回写信页
            tester.run_all_tests(
                actually_send=True,   # 改为 True 实际发送
                test_attachment=True, # 改为 True 测试附件
                auto_return=True      # 改为 True 发送后返回（需 actually_send=True）
            )

            print("\n" + "="*60)
            print("[*] 测试完成！浏览器保持打开")
            print("[*] 如需查看调试信息，请检查 debug_info/ 目录")
            print("[*] 按回车键关闭日志并退出...")
            print("="*60)
            input()
        else:
            print("\n[-] 无法进入写信页面")
            input("按回车键关闭...")

    except KeyboardInterrupt:
        print("\n[*] 用户中断")
    except Exception as e:
        print(f"\n[!] 异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.close_log()
        print("[*] 已断开连接（浏览器仍在运行）")
        print("[*] 如需关闭，请手动关闭浏览器窗口")


if __name__ == "__main__":
    main()