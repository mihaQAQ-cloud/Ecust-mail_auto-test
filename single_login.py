"""
第一步：启动调试模式浏览器，登录并保存会话信息
"""

import time
import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# 配置
URL = "https://stu.mail.ecust.edu.cn/"
USERNAME = "********"    #保护隐私，自行修改
PASSWORD = "******"

# 调试端口和会话文件
DEBUG_PORT = 9223  # 改为9223，避免9222被占用
SESSION_FILE = "browser_session.json"


def create_debug_driver():
    """创建带调试端口的Edge浏览器"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # 关键：添加远程调试端口
    options.add_argument(f"--remote-debugging-port={DEBUG_PORT}")
    
    # 使用唯一用户数据目录，避免冲突
    import tempfile
    user_data_dir = os.path.join(tempfile.gettempdir(), f"edge_profile_{int(time.time())}")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # 其他稳定化参数
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    try:
        service = Service(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
    except Exception as e:
        print(f"自动驱动失败: {e}")
        print("[*] 尝试使用系统默认Edge...")
        driver = webdriver.Edge(options=options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    return driver


def login(driver):
    """执行登录"""
    driver.get(URL)
    print("[1] 已打开登录页")
    time.sleep(4)
    
    # 输入用户名
    try:
        username_input = driver.find_element(By.XPATH, "//input[@placeholder='请输入登录账号']")
    except:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        username_input = [inp for inp in inputs if inp.get_attribute("type") == "text"][0]
    
    username_input.clear()
    username_input.send_keys(USERNAME)
    print(f"[2] 已输入账号: {USERNAME}")
    time.sleep(1)
    
    # 输入密码
    password_input = driver.find_element(By.XPATH, "//input[@type='password']")
    password_input.clear()
    password_input.send_keys(PASSWORD)
    print("[3] 已输入密码")
    time.sleep(1)
    
    # 回车登录
    password_input.send_keys(Keys.ENTER)
    print("[4] 已提交登录")
    time.sleep(6)
    
    # 检查登录结果
    current_url = driver.current_url
    if "main.jsp" in current_url:
        print(f"[+] 登录成功: {current_url[:80]}...")
        
        # 提取sid
        import re
        sid_match = re.search(r'sid=([^&]+)', current_url)
        sid = sid_match.group(1) if sid_match else ""
        
        # 保存会话信息
        session = {
            "debug_port": DEBUG_PORT,
            "sid": sid,
            "current_url": current_url,
            "login_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
        
        print(f"[+] 会话已保存到: {SESSION_FILE}")
        print(f"[+] sid: {sid}")
        
        return True
    else:
        print(f"[-] 登录失败: {current_url}")
        return False


def main():
    print("="*60)
    print("第一步：启动调试浏览器并登录")
    print("="*60)
    print(f"调试端口: {DEBUG_PORT}")
    print("登录成功后，请运行第二个脚本进入写信页面")
    print("="*60)
    
    driver = create_debug_driver()
    
    try:
        if login(driver):
            print("\n[*] 登录完成，浏览器保持打开")
            print(f"[*] 调试端口: {DEBUG_PORT}")
            print("[*] 按回车键关闭浏览器...")
            input()
        else:
            print("\n[-] 登录失败")
            input("按回车关闭...")
            
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        driver.quit()
        print("[*] 已关闭")


if __name__ == "__main__":
    # 带 --run-login 标志时执行原始登录逻辑（由 GUI 子进程调用）
    # 不带标志时启动 GUI 图形界面
    if "--run-login" in sys.argv:
        main()
    else:
        import gui_main
        gui_main.run()
