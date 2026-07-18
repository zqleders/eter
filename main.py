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

                

                # 3. 人机验证与自动续期循环

                print("[LOG] 开始人机验证监测循环...")

                # 假设 iframe 包含 hcaptcha 标识

                hcaptcha_frame = page.frame_locator("iframe[data-hcaptcha-widget-id]")

                checkbox = hcaptcha_frame.locator("#checkbox")

                

                if checkbox.count() > 0:

                    print("[LOG] 发现人机验证，开始监测...")

                    # 循环监测

                    for i in range(30): # 限制循环次数防止死循环

                        force_remove_and_disable_ads(page)

                        

                        # 检查勾选状态

                        is_checked = checkbox.get_attribute("aria-checked")

                        print(f"[LOG] 监测中... 第{i+1}次, 勾选状态: {is_checked}")

                        

                        # 每10秒截图

                        send_telegram_with_blue_dot(f"人机验证监测中 (状态: {is_checked})", page)

                        

                        if is_checked == "true":

                            print("[LOG] 检测到验证通过，准备点击续期...")

                            time.sleep(2)

                            renew_btn = page.locator("#renew-button")

                            box = renew_btn.bounding_box()

                            if box:

                                page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)

                                send_telegram_with_blue_dot("续期按钮已点击", page, box['x'], box['y'])

                                print("[LOG] 点击成功")

                            break

                        

                        time.sleep(10)

                else:
                        page.goto(f"{BASE_URL}/servers/5541/info")
                        page.wait_for_load_state("domcontentloaded")
                        time.sleep(5)
                        force_remove_and_disable_ads(page)
                        print("[LOG] 未发现人机验证框")

                    

            except Exception as e:

                print(f"[LOG] 发生错误: {e}")



if __name__ == "__main__":

    run_automation() 

