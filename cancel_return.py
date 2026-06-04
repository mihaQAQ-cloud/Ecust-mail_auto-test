"""
第五层：连接到已打开的调试浏览器，直接查找并点击"取消"按钮返回
"""

import time
import json
import os
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# 会话文件（与第一个文件共享）
SESSION_FILE = "browser_session.json"

# 结果目录
RESULT_DIR = "result"
PIC_DIR = os.path.join(RESULT_DIR, "pic")
LOG_DIR = os.path.join(RESULT_DIR, "log")


def ensure_dirs():
    """确保结果目录存在"""
    os.makedirs(PIC_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def log_print(message, level="INFO"):
    """打印日志，同时写入日志文件"""
    timestamp = time.strftime(fr"%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "[*]", "PASS": "[+]", "FAIL": "[-]", "ERROR": "[!]", "WARN": "[?]"}
    p = prefix.get(level, "[*]")
    log_line = f"[{timestamp}] {p} {message}"
    print(log_line)

    ensure_dirs()
    log_file = os.path.join(LOG_DIR, f"layer5_{time.strftime(fr'%Y%m%d')}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def connect_to_existing_browser():
    """
    连接到第一个文件打开的浏览器
    通过读取 browser_session.json 获取调试端口
    """

    # 检查会话文件是否存在
    if not os.path.exists(SESSION_FILE):
        print("="*60)
        print("[-] 错误：未找到会话文件")
        print("[-] 请先运行第一个脚本完成登录")
        print("="*60)
        return None

    # 读取会话信息
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        session = json.load(f)

    debug_port = session.get("debug_port", 9223)

    print("="*60)
    print("第五层：连接到已打开的浏览器，点击取消返回")
    print("="*60)
    print(f"[*] 调试端口: {debug_port}")
    print("-"*60)

    # 使用Chrome DevTools Protocol连接到现有浏览器
    options = Options()
    options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")

    try:
        driver = webdriver.Edge(options=options)
        print(f"[+] 成功连接到已打开的浏览器！")
        print(f"[+] 当前页面标题: {driver.title}")
        print(f"[+] 当前URL: {driver.current_url[:80]}...")
        return driver

    except Exception as e:
        print(f"[-] 连接失败: {e}")
        print("[-] 可能原因：")
        print("    1. 第一个脚本已关闭（浏览器被关闭）")
        print("    2. 调试端口错误")
        print("    3. 浏览器崩溃")
        print("\n[*] 解决方式：重新运行第一个脚本登录")
        return None


def safe_click(driver, elem, desc=""):
    """安全点击元素，尝试多种点击方式"""
    log_print(f"尝试点击: {desc}")

    # 方式1：滚动到元素并点击
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
        time.sleep(0.5)
        elem.click()
        log_print("方式1(直接点击)成功")
        return True
    except Exception as e1:
        log_print(f"方式1失败: {str(e1)[:80]}")

    # 方式2：ActionChains点击
    try:
        ActionChains(driver).move_to_element(elem).click().perform()
        log_print("方式2(ActionChains)成功")
        return True
    except Exception as e2:
        log_print(f"方式2失败: {str(e2)[:80]}")

    # 方式3：JavaScript点击
    try:
        driver.execute_script("arguments[0].click();", elem)
        log_print("方式3(JavaScript点击)成功")
        return True
    except Exception as e3:
        log_print(f"方式3失败: {str(e3)[:80]}")

    return False


def click_cancel_return(driver):
    """
    直接查找并点击"取消"按钮，不判断页面状态
    优先选择具体的按钮元素，排除页面大容器
    """
    log_print("\n[*] 开始查找并点击'取消'按钮...")

    # 等待页面完全加载
    time.sleep(3)

    # 策略1：优先查找具体的按钮/链接/span元素，排除大容器
    # 使用更精确的XPath，限制在toolbar/header区域
    cancel_selectors = [
        # 优先：toolbar区域内的取消按钮
        "//div[contains(@class,'toolbar')]//button[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'toolbar')]//a[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'toolbar')]//span[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'toolbar')]//div[contains(.,'取') and contains(.,'消')]",
        # header区域
        "//div[contains(@class,'header')]//button[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'header')]//a[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'header')]//span[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'header')]//div[contains(.,'取') and contains(.,'消')]",
        # 按钮组区域
        "//div[contains(@class,'btn-group')]//button[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'btn-group')]//a[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'btn-group')]//span[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'btn-group')]//div[contains(.,'取') and contains(.,'消')]",
        # action区域
        "//div[contains(@class,'action')]//button[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'action')]//a[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'action')]//span[contains(.,'取') and contains(.,'消')]",
        "//div[contains(@class,'action')]//div[contains(.,'取') and contains(.,'消')]",
    ]

    all_candidates = []

    for xpath in cancel_selectors:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for elem in elements:
                if elem.is_displayed():
                    elem_text = elem.text or ""
                    text_content = elem.get_attribute("textContent") or ""
                    elem_class = elem.get_attribute("class") or ""
                    elem_tag = elem.tag_name

                    # 获取元素尺寸，排除过大的容器
                    try:
                        size = elem.size
                        width = size['width']
                        height = size['height']
                    except:
                        width = 9999
                        height = 9999

                    # 排除明显是页面容器的大元素（宽度或高度超过500px）
                    if width > 500 or height > 500:
                        continue

                    # 排除frame/main/outer类的大容器
                    if any(kw in elem_class.lower() for kw in ['frame', 'main', 'outer', 'container', 'wrapper']):
                        if width > 200 or height > 200:
                            continue

                    # 获取y坐标
                    try:
                        y_pos = elem.location['y']
                    except:
                        y_pos = 999999

                    # 检查是否包含"取"和"消"
                    combined_text = (elem_text + text_content).replace(" ", "").replace("\n", "")
                    has_qu = "取" in combined_text
                    has_xiao = "消" in combined_text

                    if has_qu and has_xiao:
                        all_candidates.append({
                            'elem': elem,
                            'xpath': xpath,
                            'tag': elem_tag,
                            'text': elem_text[:30],
                            'class': elem_class[:40],
                            'y': y_pos,
                            'width': width,
                            'height': height,
                            'combined': combined_text[:40]
                        })
        except:
            pass

    # 策略2：如果toolbar区域没找到，全局查找但严格过滤
    if not all_candidates:
        log_print("[*] toolbar区域未找到，尝试全局查找...")

        global_selectors = [
            "//button[contains(.,'取') and contains(.,'消')]",
            "//a[contains(.,'取') and contains(.,'消')]",
            "//span[contains(.,'取') and contains(.,'消')]",
            "//div[contains(.,'取') and contains(.,'消')]",
        ]

        for xpath in global_selectors:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for elem in elements:
                    if elem.is_displayed():
                        elem_text = elem.text or ""
                        text_content = elem.get_attribute("textContent") or ""
                        elem_class = elem.get_attribute("class") or ""
                        elem_tag = elem.tag_name

                        # 获取元素尺寸
                        try:
                            size = elem.size
                            width = size['width']
                            height = size['height']
                        except:
                            width = 9999
                            height = 9999

                        # 严格排除大容器
                        if width > 300 or height > 100:
                            continue

                        if any(kw in elem_class.lower() for kw in ['frame', 'main', 'outer', 'container', 'wrapper', 'body', 'html']):
                            continue

                        try:
                            y_pos = elem.location['y']
                        except:
                            y_pos = 999999

                        combined_text = (elem_text + text_content).replace(" ", "").replace("\n", "")
                        has_qu = "取" in combined_text
                        has_xiao = "消" in combined_text

                        if has_qu and has_xiao:
                            all_candidates.append({
                                'elem': elem,
                                'xpath': xpath,
                                'tag': elem_tag,
                                'text': elem_text[:30],
                                'class': elem_class[:40],
                                'y': y_pos,
                                'width': width,
                                'height': height,
                                'combined': combined_text[:40]
                            })
            except:
                pass

    if not all_candidates:
        log_print("[-] 未找到任何'取消'按钮", "FAIL")

        # 调试截图
        ensure_dirs()
        debug_path = os.path.join(PIC_DIR, f"debug_no_cancel_{time.strftime(fr'%Y%m%d_%H%M%S')}.png")
        driver.save_screenshot(debug_path)
        log_print(f"调试截图已保存: {debug_path}")
        return False

    # 按y坐标排序，选择最顶部的
    all_candidates.sort(key=lambda x: x['y'])

    log_print(f"找到 {len(all_candidates)} 个候选,显示前3个:")
    for i, c in enumerate(all_candidates[:3]):
        log_print(f"  候选{i+1}: <{c['tag']}> y={c['y']} w={c['width']} h={c['height']} 文本='{c['text']}' class='{c['class']}'")

    target = all_candidates[0]['elem']

    # 点击
    clicked = safe_click(driver, target, f"取消按钮 (y={all_candidates[0]['y']}, w={all_candidates[0]['width']}, h={all_candidates[0]['height']}, 文本='{all_candidates[0]['text']}')")

    if clicked:
        time.sleep(3)

        # 记录点击后的页面状态
        current_url = driver.current_url
        page_title = driver.title
        log_print(f"点击后URL: {current_url[:80]}...")
        log_print(f"点击后标题: {page_title}")

        # 截图保存
        ensure_dirs()
        screenshot_path = os.path.join(PIC_DIR, f"after_cancel_{time.strftime(fr'%Y%m%d_%H%M%S')}.png")
        driver.save_screenshot(screenshot_path)
        log_print(f"截图已保存: {screenshot_path}")

        return True
    else:
        log_print("[-] 点击失败", "FAIL")

        # 调试截图
        ensure_dirs()
        debug_path = os.path.join(PIC_DIR, f"debug_click_fail_{time.strftime(fr'%Y%m%d_%H%M%S')}.png")
        driver.save_screenshot(debug_path)
        log_print(f"调试截图已保存: {debug_path}")

        return False


def main():
    """主程序：连接到已有浏览器，点击取消返回"""

    # 连接到第一个文件打开的浏览器
    driver = connect_to_existing_browser()

    if not driver:
        input("\n按回车键退出...")
        return

    try:
        # 点击取消返回
        if click_cancel_return(driver):
            log_print("\n[*] 已完成：点击取消")
            log_print("[*] 浏览器保持打开，按回车键关闭...")
            input()
        else:
            log_print("\n[-] 无法点击取消")
            log_print("[*] 浏览器保持打开，按回车键关闭...")
            input()

    except KeyboardInterrupt:
        log_print("\n[*] 用户中断")
    except Exception as e:
        log_print(f"\n[!] 异常: {e}", "ERROR")
    finally:
        driver.quit()
        log_print("[*] 已关闭")


if __name__ == "__main__":
    main()