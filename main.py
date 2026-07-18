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
        var selectors = [
            '[aria-label="View a Short ad"]',
            '.fc-monetization-dialog-container',
            '[data-google-ad-efd="true"]',
            '.ez-top-ad'
        ];
        var found = false;
        selectors.forEach(function(sel) {
            var target = document.querySelector(sel);
            if (target) {
                target.remove();
                found = true;
            }
        });
        return found ? "已清理广告" : "无广告";
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
                print("[LOG] 成功登录")
                
                # 2. 进入信息页
                page.goto(f"{BASE_URL}/servers/5541/info")
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)
                force_remove_and_disable_ads(page)
                print("[LOG] 跳转信息页")
                
                # --- 续期逻辑 (逻辑前置) ---
                needs_renew = False
                try:
                    time_str = page.locator("#rnw-ring-label").inner_text().strip()
                    print(f"[LOG] 原始时间字符串: {time_str}")
                    
                    if time_str == "Expired":
                        needs_renew = True
                    else:
                        # 兼容处理：将 '11h 58m' 转换为秒
                        total_seconds = 0
                        if 'h' in time_str:
                            hours = int(time_str.split('h')[0].strip())
                            minutes = int(time_str.split('h')[1].replace('m', '').strip())
                            total_seconds = hours * 3600 + minutes * 60
                        elif ':' in time_str:
                            m, s = map(int, time_str.split(':'))
                            total_seconds = m * 60 + s
                        
                        if 0 <= total_seconds <= 7200:
                            needs_renew = True
                except Exception as e:
                    print(f"[LOG] 续期状态解析失败: {e}")

                if not needs_renew:
                    print(f"[LOG] eter当前无需续期")
                    send_telegram_with_blue_dot(f"eter当前无需续期", page)
                else:
                    print(f"[LOG] 检测到需要续期，解除拦截并开始监测...")
                    # page.reload()       # 刷新以加载验证码脚本
                    time.sleep(5)
                    force_remove_and_disable_ads(page)
                    
                    hcaptcha_frame = page.frame_locator("iframe[data-hcaptcha-widget-id]")
                    checkbox = hcaptcha_frame.locator("#checkbox")
                    
                    if checkbox.count() > 0:
                        print("[LOG] 发现人机验证，开始监测...")
                        force_remove_and_disable_ads(page)
                        for i in range(30):
                           force_remove_and_disable_ads(page)
                           is_checked = checkbox.get_attribute("aria-checked")
                           print(f"[LOG] 监测中... 第{i+1}次, 勾选状态: {is_checked}")
                           send_telegram_with_blue_dot(f"人机验证监测中 第{i+1}次 (状态: {is_checked})", page)
                           
                           if is_checked == "true":
                               print("[LOG] 检测到验证通过，准备点击续期...")
                               time.sleep(2)
                               renew_btn = page.locator("#renew-button")
                               box = renew_btn.bounding_box()
                               if box:
                                   page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                                   send_telegram_with_blue_dot("eter续期按钮已点击", page, box['x'], box['y'])
                                   print("[LOG] 续期按钮点击成功")
                               break
                           time.sleep(10)
                    else:
                        print("[LOG] 未发现人机验证框，重新访问页面...")
                        page.goto(f"{BASE_URL}/servers/5541/info")
                        page.wait_for_load_state("domcontentloaded")
                        time.sleep(5)
                        force_remove_and_disable_ads(page)

                # --- 离线启动逻辑 (后续处理) ---
                page.goto(f"{BASE_URL}/servers/5541/info")
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)
                force_remove_and_disable_ads(page)
                status_element = page.locator("#server-status")
                status_text = status_element.inner_text().strip()
                print(f"[LOG] 当前服务器状态: {status_text}")
                
                if status_text == "Offline":
                    print("[LOG] 检测到状态 Offline，执行启动流程...")
                    page.goto(f"{BASE_URL}/servers/5541/console")
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(3)
                    force_remove_and_disable_ads(page)
                    start_btn = page.locator('//*[@id="power-controls"]/button[1]')
                    if start_btn.count() > 0:
                        start_btn.dispatch_event("click")
                        send_telegram_with_blue_dot("eter Start按钮已点击", page)
                    print("[LOG] Start按钮已点击")
                    
            except Exception as e:
                print(f"[LOG] 发生错误: {e}")

if __name__ == "__main__":
    run_automation()
