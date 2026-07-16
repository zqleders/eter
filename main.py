import os
import time
import requests
import random
import datetime
from playwright.sync_api import sync_playwright
from browser import BrowserManager 

# --- 全局配置：在最上方定义，确保全局可访问 ---
EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# 强制处理 BASE_URL，确保其不会因为 None 导致逻辑错误
_RAW_BASE_URL = os.getenv("BASE_URL", "")
BASE_URL = _RAW_BASE_URL.rstrip('/')

# --- 辅助函数定义 ---
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def send_telegram_with_blue_dot(message, page, x=0, y=0):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    file_path = "screenshot.png"
    try:
        page.screenshot(path=file_path, full_page=True)
        if PIL_AVAILABLE and x != 0 and y != 0:
            img = Image.open(file_path)
            draw = ImageDraw.Draw(img)
            r = 20
            draw.ellipse((x - r, y - r, x + r, y + r), fill='blue', outline='blue')
            img.save(file_path)
        with open(file_path, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={'chat_id': TELEGRAM_CHAT_ID, 'caption': message}, files={'photo': f})
    except Exception as e:
        print(f"[LOG] Telegram 发送失败: {e}")

def force_remove_and_disable_ads(page):
    js = """
    var elements = document.querySelectorAll('.fc-monetization-dialog-container, div[class*="fixed"]');
    elements.forEach(function(el) { el.remove(); });
    var style = document.createElement('style');
    style.innerHTML = '.fc-monetization-dialog-container, div[class*="fixed"] { display: none !important; pointer-events: none !important; }';
    document.head.appendChild(style);
    """
    try: page.evaluate(js)
    except: pass

def human_like_click(page, locator_element):
    locator_element.wait_for(state="visible", timeout=30000)
    box = locator_element.bounding_box()
    cx, cy = int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2)
    page.mouse.move(960, 100)
    page.mouse.move(cx, cy)
    time.sleep(random.uniform(0.5, 1.2))
    page.mouse.down()
    page.mouse.up()
    return cx, cy

# --- 主程序逻辑 ---
def run_automation():
    # 使用全局常量 BASE_URL
    if not BASE_URL:
        print("[ERROR] BASE_URL 未定义！请检查环境变量配置。")
        return

    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                print(f"[LOG] 正在访问: {BASE_URL}/login")
                page.goto(f"{BASE_URL}/login")
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                print("[LOG] 登录点击操作完成，等待跳转...")
                page.wait_for_load_state("networkidle")
                
                print("[LOG] 前往服务器信息页...")
                page.goto(f"{BASE_URL}/servers/5541/info")
                page.wait_for_load_state("networkidle")
                
                status_text = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 服务器当前状态: {status_text}")
                
                # 续期逻辑判定
                should_renew = (status_text == "Suspended")
                if not should_renew:
                    try:
                        exp_date = datetime.datetime.strptime(status_text, "%d.%m.%Y")
                        if (exp_date - datetime.datetime.now()).total_seconds() < 7200:
                            should_renew = True
                    except: pass
                
                if not should_renew:
                    print("[LOG] 服务器状态健康，无需续期。")
                    return

                print("[LOG] 跳转至续期页面...")
                page.goto(f"{BASE_URL}/service/renew")
                page.wait_for_load_state("networkidle")

                # 人机验证循环
                checkbox = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                if checkbox.count() > 0:
                    print("[LOG] 发现人机验证，开始监测...")
                    for i in range(20):
                        force_remove_and_disable_ads(page)
                        is_checked = checkbox.get_attribute("aria-checked")
                        print(f"[LOG] 人机验证检测中... (第 {i+1} 次), aria-checked: {is_checked}")
                        if is_checked == "true":
                            print("[LOG] 验证已通过！")
                            break
                        checkbox.click(force=True)
                        time.sleep(5)
                else:
                    print("[LOG] 未发现人机验证，跳过验证步骤。")

                print("[LOG] 准备点击续费按钮...")
                renew_btn = page.locator("#renew-button")
                cx, cy = human_like_click(page, renew_btn)
                print(f"[LOG] 续费点击坐标: {cx}, {cy}")
                
                time.sleep(10)
                
                # 复核
                page.goto(f"{BASE_URL}/servers/5541/info")
                new_status = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 最终状态复核: {new_status}")
                send_telegram_with_blue_dot(f"续期流程执行完毕，当前状态: {new_status}", page, cx, cy)
                    
            except Exception as e:
                print(f"[ERROR] 发生错误: {e}")
                # 最后的补救尝试，防止 Telegram 发送函数再次报错
                try: send_telegram_with_blue_dot(f"任务出错: {str(e)[:100]}", page)
                except: pass

if __name__ == "__main__":
    run_automation()
