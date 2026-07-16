import os, time, datetime, requests, random
from playwright.sync_api import sync_playwright
from browser import BrowserManager

# --- 依赖项 ---
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# --- 配置 ---
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = os.getenv("BASE_URL", "").rstrip('/')

def send_telegram_with_blue_dot(message, page, x=0, y=0):
    file_path = "screenshot.png"
    page.screenshot(path=file_path, full_page=True)
    if PIL_AVAILABLE and x != 0 and y != 0:
        img = Image.open(file_path)
        draw = ImageDraw.Draw(img)
        r = 20
        draw.ellipse((x - r, y - r, x + r, y + r), fill='blue', outline='blue')
        img.save(file_path)
    with open(file_path, "rb") as photo:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={'chat_id': TELEGRAM_CHAT_ID, 'caption': f"[LOG] {message}"}, files={'photo': photo})

def force_remove_and_disable_ads(page):
    js = """
    (function() {
        var target = document.querySelector('[aria-label="View a Short ad"]') || document.querySelector('.fc-monetization-dialog-container');
        if (target) {
            target.remove();
            return "已清理广告";
        }
        return "无广告";
    })()
    """
    try:
        res = page.evaluate(js)
        print(f"[LOG] 广告检查: {res}")
    except Exception as e:
        print(f"[LOG] 广告检查异常: {e}")

def run_automation():
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录
                page.goto(f"{BASE_URL}/login")
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("domcontentloaded")
                
                # 2. 进入信息页
                page.goto(f"{BASE_URL}/servers/5541/info")
                page.wait_for_load_state("domcontentloaded")
                
                def check_and_start_server():
                    status_text = page.locator("#server-status").inner_text().strip()
                    if status_text == "Offline":
                        print("[LOG] 检测到状态 Offline，执行启动流程...")
                        page.goto(f"{BASE_URL}/servers/5541/console")
                        page.wait_for_load_state("domcontentloaded")
                        force_remove_and_disable_ads(page)
                        start_btn = page.locator('//*[@id="power-controls"]/button[1]')
                        start_btn.scroll_into_view_if_needed()
                        box = start_btn.bounding_box()
                    if box:
                            # 1. 模拟移动轨迹 (保持原有的真人视觉效果)
                            page.mouse.move(960, 100)
                            time.sleep(random.uniform(0.3, 0.6))
                            cx = box['x'] + box['width'] / 2
                            cy = box['y'] + box['height'] / 2
                            page.mouse.move(cx, cy)
                            time.sleep(random.uniform(0.5, 1.2))
                            
                            # 2. 核心修改：使用 dispatch_event 绕过遮挡强制触发点击
                            start_btn.dispatch_event("click")
                            
                            # 3. 记录日志并截图
                            send_telegram_with_blue_dot("Start按钮已强制点击(dispatch)", page, int(cx), int(cy))
                            print("[LOG] 强制点击成功")
                        page.goto(f"{BASE_URL}/servers/5541/info")
                        page.wait_for_load_state("domcontentloaded")

                # 初始检查
                check_and_start_server()
                
                # 3. 人机验证与自动续期循环
                status_text = page.locator("#server-status").inner_text().strip()
                needs_renew = False
                if status_text == "Suspended":
                    needs_renew = True
                else:
                    try:
                        expiry_date = datetime.datetime.strptime(status_text, "%d.%m.%Y")
                        if 0 <= (expiry_date - datetime.datetime.now()).total_seconds() <= 7200:
                            needs_renew = True
                    except: pass

                if needs_renew:
                    print("[LOG] 开始人机验证监测循环...")
                    hcaptcha_frame = page.frame_locator("iframe[data-hcaptcha-widget-id]")
                    checkbox = hcaptcha_frame.locator("#checkbox")
                    
                    if checkbox.count() > 0:
                        for i in range(30):
                            is_checked = checkbox.get_attribute("aria-checked")
                            send_telegram_with_blue_dot(f"人机验证监测中 (状态: {is_checked})", page)
                            if is_checked == "true":
                                renew_btn = page.locator("#renew-button")
                                renew_btn.scroll_into_view_if_needed()
                                box = renew_btn.bounding_box()
                                if box:
                                    page.mouse.move(960, 100)
                                    time.sleep(random.uniform(0.3, 0.6))
                                    cx = box['x'] + box['width'] / 2
                                    cy = box['y'] + box['height'] / 2
                                    page.mouse.move(cx, cy)
                                    time.sleep(random.uniform(0.5, 1.2))
                                    page.mouse.click(cx, cy)
                                    send_telegram_with_blue_dot("续期按钮已点击", page, int(cx), int(cy))
                                    # 续期后回查状态
                                    time.sleep(5)
                                    check_and_start_server()
                                break
                            time.sleep(10)
                    else:
                        print("[LOG] 未发现人机验证框")
                
            except Exception as e:
                print(f"[LOG] 发生错误: {e}")

if __name__ == "__main__":
    run_automation()
