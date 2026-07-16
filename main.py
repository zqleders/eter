import os, time, datetime, requests, random
from playwright.sync_api import sync_playwright
from browser import BrowserManager

# --- 配置 ---
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = os.getenv("BASE_URL", "").rstrip('/')

def send_telegram_with_blue_dot(message, driver, x=0, y=0):
    file_path = "screenshot.png"
    driver.screenshot(path=file_path, full_page=True)
    if os.path.exists("screenshot.png"):
        try:
            from PIL import Image, ImageDraw
            img = Image.open(file_path)
            if x != 0 and y != 0:
                draw = ImageDraw.Draw(img)
                r = 20
                draw.ellipse((x - r, y - r, x + r, y + r), fill='blue', outline='blue')
            img.save(file_path)
        except: pass
        with open(file_path, "rb") as photo:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", 
                          data={'chat_id': TELEGRAM_CHAT_ID, 'caption': f"[LOG] {message}"}, 
                          files={'photo': photo})

def force_remove_and_disable_ads(page):
    js = """
    (function() {
        var targets = document.querySelectorAll('.fc-monetization-dialog-container, div[class*="fixed"]');
        if (targets.length === 0) return "未检测到广告";
        targets.forEach(function(el) { el.remove(); });
        var style = document.createElement('style');
        style.innerHTML = '.fc-monetization-dialog-container, div[class*="fixed"] { display: none !important; pointer-events: none !important; }';
        document.head.appendChild(style);
        return "已清理 " + targets.length + " 个广告";
    })()
    """
    try:
        res = page.evaluate(js)
        print(f"[LOG] 去广告操作: {res}")
    except: pass

def execute_with_ad_cleanup(page, action_func, *args):
    """科学做法：操作失败则清理广告并重试一次"""
    try:
        return action_func(*args)
    except Exception as e:
        print(f"[LOG] 操作遇到阻碍，执行清理并重试... 错误: {e}")
        force_remove_and_disable_ads(page)
        return action_func(*args)

def human_like_click(page, target):
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
                page.goto(f"{BASE_URL}/login")
                force_remove_and_disable_ads(page)
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                
                print("[LOG] 等待登录加载...")
                page.wait_for_load_state("networkidle")
                
                print("[LOG] 前往信息页...")
                page.goto(f"{BASE_URL}/servers/5541/info")
                force_remove_and_disable_ads(page)
                
                status_text = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 当前状态: {status_text}")
                
                if status_text == "Suspended":
                    print("[LOG] 状态符合，前往续期页...")
                    page.goto(f"{BASE_URL}/service/renew")
                    
                    # 人机验证监测
                    checkbox = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                    if checkbox.count() > 0:
                        execute_with_ad_cleanup(page, checkbox.click, {"force": True})
                        for _ in range(20):
                            time.sleep(5)
                            force_remove_and_disable_ads(page)
                            if checkbox.get_attribute("aria-checked") == "true": break
                            checkbox.click(force=True)
                    
                    # 续期点击
                    renew_btn = page.locator("#renew-button")
                    print("[LOG] 执行续期...")
                    cx, cy = execute_with_ad_cleanup(page, human_like_click, page, renew_btn)
                    
                    send_telegram_with_blue_dot(f"续期点击成功，坐标: {cx}, {cy}", page, cx, cy)
                
            except Exception as e:
                print(f"[ERROR] 流程最终异常: {e}")
                try: send_telegram_with_blue_dot(f"最终异常: {str(e)[:50]}", page)
                except: pass

if __name__ == "__main__":
    run_automation()
