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
            return "成功找到并删除了广告元素";
        } else {
            return "未找到广告元素";
        }
    })()
    """
    try:
        res = page.evaluate(js)
        print(f"[LOG] 去广告探测结果: {res}")
    except Exception as e:
        print(f"[LOG] 去广告探测脚本异常: {e}")

def human_like_click(page, target):
    force_remove_and_disable_ads(page)
    box = target.bounding_box()
    if not box: raise Exception("无法获取目标元素的 bounding_box")
    cx, cy = int(box['x'] + box['width'] / 2), int(box['y'] + box['height'] / 2)
    page.mouse.move(960, 100)
    page.mouse.move(cx, cy)
    time.sleep(random.uniform(0.5, 1.2))
    page.mouse.click(cx, cy)
    return cx, cy

def execute_with_ad_cleanup(page, action_func, target):
    try:
        return action_func(page, target)
    except Exception as e:
        print(f"[LOG] 操作受阻，再次清理并重试... 错误: {e}")
        force_remove_and_disable_ads(page)
        return action_func(page, target)

def run_automation():
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录
                page.goto(f"{BASE_URL}/login")
                time.sleep(3)
                force_remove_and_disable_ads(page)
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)
                
                # 2. 在信息页执行所有操作
                info_url = f"{BASE_URL}/servers/5541/info"
                print(f"[LOG] 步骤2: 访问服务器信息页: {info_url}")
                page.goto(info_url)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)
                force_remove_and_disable_ads(page)
                
                status_text = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 当前状态: {status_text}")
                send_telegram_with_blue_dot(f"状态页状态: {status_text}", page)
                
                if status_text == "Suspended":
                    # 4. 在当前页面处理人机验证
                    print("[LOG] 监测人机验证...")
                    checkbox = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                    if checkbox.count() > 0:
                        checkbox.click(force=True)
                        for i in range(20):
                            time.sleep(5)
                            force_remove_and_disable_ads(page)
                            if checkbox.get_attribute("aria-checked") == "true":
                                break
                            checkbox.click(force=True)
                    
                    # 5. 在当前页面执行续期
                    print("[LOG] 执行页面内续期点击")
                    renew_btn = page.locator("#renew-button")
                    execute_with_ad_cleanup(page, human_like_click, renew_btn)
                    
                    # 6. 复核
                    time.sleep(5)
                    page.reload()
                    time.sleep(3)
                    force_remove_and_disable_ads(page)
                    final_status = page.locator("#server-status").inner_text().strip()
                    print(f"[LOG] 续期后状态: {final_status}")
                    send_telegram_with_blue_dot(f"续期结束，状态: {final_status}", page)
                    
            except Exception as e:
                print(f"[LOG] 流程出错: {e}")
                try: send_telegram_with_blue_dot(f"出错: {str(e)[:50]}", page)
                except: pass

if __name__ == "__main__":
    run_automation()
