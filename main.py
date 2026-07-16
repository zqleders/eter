import os
import time
import requests
import random
import datetime
from playwright.sync_api import sync_playwright
from browser import BrowserManager 

# --- 依赖项检查 ---
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 获取环境配置
EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = os.getenv("BASE_URL") # Repository Secret

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
        print(f"Telegram 发送失败: {e}")

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

def run_automation():
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录
                force_remove_and_disable_ads(page)
                page.goto(f"{BASE_URL}/login")
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                
                # 2. 状态检查
                force_remove_and_disable_ads(page)
                page.goto(f"{BASE_URL}/servers/5541/info")
                time.sleep(5)
                
                status_text = page.locator("#server-status").inner_text().strip()
                should_renew = False
                
                if status_text == "Suspended":
                    should_renew = True
                else:
                    try:
                        # 假设日期格式为 DD.MM.YYYY，解析并对比
                        exp_date = datetime.datetime.strptime(status_text, "%d.%m.%Y")
                        if (exp_date - datetime.datetime.now()).total_seconds() < 7200:
                            should_renew = True
                    except: pass
                
                if not should_renew:
                    print(f"服务器状态 {status_text}，无需续期。")
                    return

                # 3. 续期操作
                page.goto(f"{BASE_URL}/service/renew") # 根据实际路径调整
                
                # 人机验证
                hcaptcha_locator = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                if hcaptcha_locator.count() > 0:
                    force_remove_and_disable_ads(page)
                    hcaptcha_locator.click(force=True)
                    # 轮询验证...
                
                force_remove_and_disable_ads(page)
                renew_btn = page.locator("#renew-button")
                cx, cy = human_like_click(page, renew_btn)
                send_telegram_with_blue_dot("续费操作已触发。", page, cx, cy)
                    
            except Exception as e:
                print(f"任务出错: {e}")

if __name__ == "__main__":
    run_automation()
