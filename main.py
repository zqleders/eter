import os
import time
import requests
from playwright.sync_api import sync_playwright
from browser import BrowserManager 

# 获取环境配置
EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PROXY_SOCKS5 = os.getenv("PROXY_SOCKS5")

def send_telegram(message, photo_path=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': f})
    except Exception as e:
        print(f"Telegram 发送失败: {e}")

def handle_popups_and_ads(page):
    try:
        reward_ad_btn = page.locator("button.fc-rewarded-ad-button")
        if reward_ad_btn.count() > 0 and reward_ad_btn.is_visible():
            reward_ad_btn.click(force=True)
            time.sleep(22)
            close_btn = page.locator("#dismiss-button")
            if close_btn.count() > 0 and close_btn.is_visible():
                close_btn.click(force=True)
                time.sleep(2)
        page.evaluate("""() => {
            const guard = document.getElementById('panel-guard-layer');
            if(guard) { guard.style.display = 'none'; }
            document.querySelectorAll('.modal-backdrop, .fc-cta-consent').forEach(el => el.style.display = 'none');
        }""")
    except Exception as e:
        print(f"广告处理错误: {e}")

def run_automation():
    # 核心修正：通过环境变量传递代理，无需修改 BrowserManager
    if PROXY_SOCKS5:
        os.environ["HTTP_PROXY"] = PROXY_SOCKS5
        os.environ["HTTPS_PROXY"] = PROXY_SOCKS5
        print(f"代理已通过环境变量配置: {PROXY_SOCKS5}")

    target_url = "https://eternalzero.cloud/servers/5541/info"
    
    with sync_playwright() as p:
        # 这里移除 proxy 参数，使用原始的调用方式
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                print("访问登录页...")
                page.goto("https://eternalzero.cloud/login")
                
                time.sleep(2)
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                
                print("登录中，等待跳转...")
                page.wait_for_load_state("networkidle")
                time.sleep(10) 

                print(f"跳转到目标页面: {target_url}")
                for _ in range(3):
                    page.goto(target_url)
                    time.sleep(5)
                    if page.url == target_url: break
                
                handle_popups_and_ads(page)
                
                if page.locator("iframe[data-hcaptcha-widget-id]").count() > 0:
                    try:
                        page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").click(force=True)
                    except: pass
                    
                    verified = False
                    for i in range(60):
                        time.sleep(3)
                        handle_popups_and_ads(page)
                        widget = page.locator("iframe[data-hcaptcha-widget-id]")
                        response = widget.get_attribute("data-hcaptcha-response")
                        if response and len(response) > 20:
                            verified = True
                            break
                    if not verified: raise Exception("人机验证超时")
                
                print("执行续费...")
                handle_popups_and_ads(page)
                page.wait_for_selector("#renew-button", state="visible", timeout=30000)
                page.locator("#renew-button").click(force=True)

                time.sleep(5)
                page.screenshot(path="final.png", full_page=True)
                send_telegram("流程结束，续费成功。", "final.png")
                    
            except Exception as e:
                error_msg = f"任务执行出错: {str(e)}"
                print(error_msg)
                page.screenshot(path="error.png", full_page=True)
                send_telegram(error_msg, "error.png")

if __name__ == "__main__":
    run_automation()
