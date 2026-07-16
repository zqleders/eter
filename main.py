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

def send_telegram_with_blue_dot(message, driver, x, y):
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
    var elements = document.querySelectorAll('.fc-monetization-dialog-container, div[class*="fixed"]');
    var removed = [];
    elements.forEach(function(el) {
        removed.push(el.className);
        el.remove();
    });
    var style = document.createElement('style');
    style.innerHTML = '.fc-monetization-dialog-container, div[class*="fixed"] { display: none !important; pointer-events: none !important; }';
    document.head.appendChild(style);
    return removed;
    """
    try:
        removed_list = page.evaluate(js)
        if removed_list: print(f"[LOG] 已销毁广告遮罩: {removed_list}")
    except Exception as e:
        print(f"[LOG] 广告清理脚本错误: {e}")

def human_like_click(page, target):
    """封装好的模拟真人点击逻辑"""
    box = target.bounding_box()
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
                # 登录
                print("[LOG] 正在访问登录页...")
                page.goto(f"{BASE_URL}/login")
                force_remove_and_disable_ads(page)
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                
                # 状态检查
                print("[LOG] 登录成功，正在检测服务器状态...")
                page.goto(f"{BASE_URL}/servers/5541/info")
                page.wait_for_load_state("networkidle")
                force_remove_and_disable_ads(page)
                
                status_text = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 服务器状态: {status_text}")
                
                # 状态判定逻辑
                should_renew = (status_text == "Suspended")
                if not should_renew:
                    try:
                        exp_date = datetime.datetime.strptime(status_text, "%d.%m.%Y")
                        if (exp_date - datetime.datetime.now()).total_seconds() < 7200:
                            should_renew = True
                    except: pass
                
                if not should_renew:
                    print("[LOG] 无需续期操作，跳过。")
                    return

                # 续期操作
                print("[LOG] 状态符合续期条件，前往续期页...")
                page.goto(f"{BASE_URL}/service/renew")
                page.wait_for_load_state("networkidle")
                
                # 人机验证循环监测
                checkbox = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                if checkbox.count() > 0:
                    print("[LOG] 发现人机验证，开始处理...")
                    checkbox.click(force=True)
                    for i in range(20):
                        time.sleep(5)
                        force_remove_and_disable_ads(page)
                        is_checked = checkbox.get_attribute("aria-checked")
                        print(f"[LOG] 人机验证监测... 当前 aria-checked: {is_checked}")
                        if is_checked == "true":
                            print("[LOG] 人机验证完成。")
                            break
                        checkbox.click(force=True)
                
                # 点击 Renew
                print("[LOG] 执行 Renew 点击操作...")
                force_remove_and_disable_ads(page)
                renew_btn = page.locator("#renew-button")
                cx, cy = human_like_click(page, renew_btn)
                
                # 最终状态确认
                time.sleep(5)
                page.goto(f"{BASE_URL}/servers/5541/info")
                final_status = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 续期结束，最终状态: {final_status}")
                send_telegram_with_blue_dot(f"续期操作完成，最终状态: {final_status}", page, cx, cy)
                    
            except Exception as e:
                print(f"[LOG] 流程出错: {e}")

if __name__ == "__main__":
    run_automation()
