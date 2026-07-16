import os, time, datetime, requests, random
from playwright.sync_api import sync_playwright
from browser import BrowserManager

# --- 依赖项检查 ---
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 配置项
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = os.getenv("BASE_URL", "").rstrip('/')

def send_telegram_with_blue_dot(message, driver, x=0, y=0):
    file_path = "screenshot.png"
    driver.screenshot(path=file_path, full_page=True)
    if PIL_AVAILABLE and x != 0 and y != 0:
        img = Image.open(file_path)
        draw = ImageDraw.Draw(img)
        r = 20
        draw.ellipse((x - r, y - r, x + r, y + r), fill='blue', outline='blue')
        img.save(file_path)
    with open(file_path, "rb") as photo:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={'chat_id': TELEGRAM_CHAT_ID, 'caption': f"[gameserver] {message}"}, files={'photo': photo})

def force_remove_and_disable_ads(page):
    js = """
    var targets = document.querySelectorAll('.fc-monetization-dialog-container, div[class*="fixed"]');
    if (targets.length > 0) {
        targets.forEach(function(el) { el.remove(); });
        var style = document.createElement('style');
        style.innerHTML = '.fc-monetization-dialog-container, div[class*="fixed"] { display: none !important; pointer-events: none !important; }';
        document.head.appendChild(style);
    }
    """
    try: page.evaluate(js)
    except: pass

def human_like_click(page, target):
    force_remove_and_disable_ads(page) # 点击前清理
    box = target.bounding_box()
    if not box: raise Exception("无法获取元素坐标")
    cx, cy = int(box['x'] + box['width'] / 2), int(box['y'] + box['height'] / 2)
    page.mouse.move(960, 100)
    page.mouse.move(cx, cy)
    time.sleep(random.uniform(0.5, 1.2))
    page.mouse.click(cx, cy)
    return cx, cy

def run_automation():
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录
                print("[LOG] 访问登录页")
                page.goto(f"{BASE_URL}/login")
                force_remove_and_disable_ads(page)
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                force_remove_and_disable_ads(page)
                send_telegram_with_blue_dot("登录完成", page, 0, 0)
                
                # 2. 状态检查
                print("[LOG] 前往服务器页")
                page.goto(f"{BASE_URL}/servers/5541/info")
                page.wait_for_load_state("networkidle")
                force_remove_and_disable_ads(page)
                
                status_text = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 服务器状态: {status_text}")
                send_telegram_with_blue_dot(f"状态: {status_text}", page, 0, 0)
                
                should_renew = (status_text == "Suspended")
                if not should_renew:
                    try:
                        exp_date = datetime.datetime.strptime(status_text, "%d.%m.%Y")
                        if (exp_date - datetime.datetime.now()).total_seconds() < 7200: should_renew = True
                    except: pass
                
                if not should_renew: return

                # 3. 续期页面
                print("[LOG] 前往续期页")
                page.goto(f"{BASE_URL}/service/renew")
                page.wait_for_load_state("networkidle")
                force_remove_and_disable_ads(page)
                
                # 4. 人机验证
                checkbox = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                if checkbox.count() > 0:
                    force_remove_and_disable_ads(page)
                    checkbox.click(force=True)
                    for i in range(20):
                        time.sleep(5)
                        force_remove_and_disable_ads(page)
                        if checkbox.get_attribute("aria-checked") == "true":
                            send_telegram_with_blue_dot("人机验证通过", page, 0, 0)
                            break
                        checkbox.click(force=True)
                
                # 5. 点击续期
                print("[LOG] 执行 Renew 点击")
                force_remove_and_disable_ads(page)
                renew_btn = page.locator("#renew-button")
                cx, cy = human_like_click(page, renew_btn)
                send_telegram_with_blue_dot("已触发续期", page, cx, cy)
                
                # 6. 复核
                time.sleep(5)
                page.goto(f"{BASE_URL}/servers/5541/info")
                force_remove_and_disable_ads(page)
                final_status = page.locator("#server-status").inner_text().strip()
                send_telegram_with_blue_dot(f"最终状态: {final_status}", page, 0, 0)
                    
            except Exception as e:
                print(f"[LOG] 异常: {e}")
                try: send_telegram_with_blue_dot(f"异常: {str(e)[:100]}", page, 0, 0)
                except: pass

if __name__ == "__main__":
    run_automation()
