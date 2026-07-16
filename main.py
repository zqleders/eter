import os
import time
import requests
import random
import datetime
from playwright.sync_api import sync_playwright
from browser import BrowserManager 

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = os.getenv("BASE_URL", "").rstrip('/')

def send_telegram_with_blue_dot(message, page, x=0, y=0):
    """带蓝点定位的 Telegram 截图发送功能"""
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
    """模拟鼠标轨迹移动并点击，返回中心坐标"""
    locator_element.wait_for(state="visible", timeout=30000)
    box = locator_element.bounding_box()
    cx, cy = int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2)
    page.mouse.move(960, 100)
    page.mouse.move(cx, cy)
    time.sleep(random.uniform(0.5, 1.2))
    page.mouse.down()
    page.mouse.up()
    return cx, cy

def run_automation():
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                print(f"[LOG] 正在访问: {BASE_URL}/login")
                page.goto(f"{BASE_URL}/login")
                force_remove_and_disable_ads(page)
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                
                print("[LOG] 登录成功，检查服务器状态...")
                force_remove_and_disable_ads(page)
                page.goto(f"{BASE_URL}/servers/5541/info")
                time.sleep(5)
                
                status_text = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 当前服务器状态: {status_text}")
                
                should_renew = (status_text == "Suspended")
                if not should_renew:
                    try:
                        exp_date = datetime.datetime.strptime(status_text, "%d.%m.%Y")
                        if (exp_date - datetime.datetime.now()).total_seconds() < 7200:
                            should_renew = True
                    except: pass
                
                if not should_renew:
                    print("[LOG] 无需续期。")
                    return

                print("[LOG] 进入续期页面...")
                force_remove_and_disable_ads(page)
                page.goto(f"{BASE_URL}/service/renew")
                
                last_shot_time = 0
                for _ in range(60):
                    force_remove_and_disable_ads(page)
                    hcaptcha = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                    if hcaptcha.count() > 0:
                        if hcaptcha.get_attribute("aria-checked") == "true":
                            break
                        if time.time() - last_shot_time > 10:
                            print("[LOG] 监控人机验证进度...")
                            send_telegram_with_blue_dot("正在监控人机验证...", page)
                            last_shot_time = time.time()
                        hcaptcha.click(force=True)
                    time.sleep(2)
                
                print("[LOG] 执行续期点击...")
                force_remove_and_disable_ads(page)
                cx, cy = human_like_click(page, page.locator("#renew-button"))
                time.sleep(5)
                
                print("[LOG] 续期完成，复核最终状态...")
                page.goto(f"{BASE_URL}/servers/5541/info")
                time.sleep(5)
                new_status = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 续期后状态: {new_status}")
                send_telegram_with_blue_dot(f"续期流程执行完毕，当前状态: {new_status}", page, cx, cy)
                    
            except Exception as e:
                print(f"[ERROR] 任务出错: {e}")
                send_telegram_with_blue_dot(f"任务出错: {e}", page)

if __name__ == "__main__":
    run_automation()
