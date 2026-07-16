import os
import time
import requests
import random
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

def send_telegram_with_blue_dot(message, page, x=0, y=0):
    """带蓝点定位的 Telegram 截图发送功能"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: 
        return
    
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
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", 
                data={'chat_id': TELEGRAM_CHAT_ID, 'caption': message}, 
                files={'photo': f}
            )
    except Exception as e:
        print(f"Telegram 发送或画点失败: {e}")

def force_remove_and_disable_ads(page):
    """根据广告元素特征，强制销毁全屏广告遮罩并禁用"""
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
        if removed_list: 
            print(f"[LOG] 已销毁广告遮罩: {removed_list}")
    except Exception as e:
        print(f"[LOG] 广告清理脚本错误: {e}")

def human_like_click(page, locator_element):
    """为 Playwright 封装的模拟真人移动与点击逻辑，并返回中心物理坐标"""
    locator_element.wait_for(state="visible", timeout=30000)
    box = locator_element.bounding_box()
    if not box:
        raise Exception("无法获取元素的 bounding_box")
        
    cx = int(box["x"] + box["width"] / 2)
    cy = int(box["y"] + box["height"] / 2)
    
    page.mouse.move(960, 100)
    page.mouse.move(cx, cy)
    time.sleep(random.uniform(0.5, 1.2))
    
    page.mouse.down()
    page.mouse.up()
    return cx, cy

def run_automation():
    target_url = "https://eternalzero.cloud/servers/5541/info"
    
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录
                force_remove_and_disable_ads(page)
                page.goto("https://eternalzero.cloud/login")
                
                force_remove_and_disable_ads(page)
                page.fill("input#email", EMAIL)
                
                force_remove_and_disable_ads(page)
                page.fill("input#password", PASSWORD)
                
                force_remove_and_disable_ads(page)
                page.get_by_role("button", name="Sign in").click()
                
                page.wait_for_load_state("networkidle")
                time.sleep(10) 

                # 2. 访问并确保跳转
                for _ in range(3):
                    force_remove_and_disable_ads(page)
                    page.goto(target_url)
                    time.sleep(5)
                    if page.url == target_url: break
                
                # 3. 人机验证处理（纯元素交互）
                force_remove_and_disable_ads(page)
                hcaptcha_locator = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                if hcaptcha_locator.count() > 0:
                    print("检测到 hCaptcha，执行元素点击...")
                    force_remove_and_disable_ads(page)
                    hcaptcha_locator.click(force=True)

                    # 后续验证轮询逻辑...
                    verified = False
                    for i in range(60):
                        time.sleep(3)
                        force_remove_and_disable_ads(page)
                        if page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").get_attribute("aria-checked") == "true":
                            verified = True
                            break
                    
                    if not verified: raise Exception("验证超时")
                
                # 4. 执行续费
                print("执行续费...")
                force_remove_and_disable_ads(page)
                renew_btn = page.locator("#renew-button")
                force_remove_and_disable_ads(page)
                cx, cy = human_like_click(page, renew_btn)
                
                time.sleep(3)
                send_telegram_with_blue_dot("续费点击已触发。", page, cx, cy)
                    
            except Exception as e:
                print(f"任务出错: {e}")

if __name__ == "__main__":
    run_automation()
