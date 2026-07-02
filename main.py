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
    """底层清理逻辑：检测并移除所有遮罩、弹窗、广告"""
    try:
        # 1. 强制点击所有包含 Consent/Agree 的合规按钮
        page.evaluate("""() => {
            document.querySelectorAll('button').forEach(btn => {
                const t = btn.innerText.toLowerCase();
                if (t.includes('consent') || t.includes('agree')) btn.click();
            });
        }""")
        
        # 2. 广告交互
        reward_ad_btn = page.locator("button.fc-rewarded-ad-button")
        if reward_ad_btn.count() > 0 and reward_ad_btn.is_visible():
            reward_ad_btn.click(force=True)
            time.sleep(22)
            close_btn = page.locator("#dismiss-button")
            if close_btn.count() > 0 and close_btn.is_visible():
                close_btn.click(force=True)
                time.sleep(2)

        # 3. 遮罩移除
        page.evaluate("""() => {
            const guard = document.getElementById('panel-guard-layer');
            if(guard) guard.style.display = 'none';
            document.querySelectorAll('.modal-backdrop, .fc-cta-consent, .fc-dialog-container, #fc-consent-modal').forEach(el => el.style.display = 'none');
            document.body.style.overflow = 'auto';
        }""")
    except Exception as e:
        print(f"清理过程中的非致命错误: {e}")

def ensure_clean_screen(page):
    """前置守护函数：在操作前确保页面无遮挡"""
    handle_popups_and_ads(page)
    time.sleep(1) # 给弹窗消失留出短暂缓冲

def run_automation():
    target_url = "https://eternalzero.cloud/servers/5541/info"
    
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录流程
                page.goto("https://eternalzero.cloud/login")
                ensure_clean_screen(page) # 操作前检查
                
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                
                ensure_clean_screen(page)
                page.get_by_role("button", name="Sign in").click()
                
                print("登录中，等待跳转...")
                page.wait_for_load_state("networkidle")
                time.sleep(10) 

                # 2. 访问目标页面
                print(f"跳转到目标页面: {target_url}")
                for _ in range(3):
                    ensure_clean_screen(page)
                    page.goto(target_url)
                    time.sleep(5)
                    if page.url == target_url: break
                
                # 3. 人机验证检测
                if page.locator("iframe[data-hcaptcha-widget-id]").count() > 0:
                    print("检测到 hCaptcha...")
                    ensure_clean_screen(page)
                    page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").click(force=True)

                    verified = False
                    for i in range(60):
                        time.sleep(3)
                        ensure_clean_screen(page) # 循环中持续监控
                        
                        try:
                            checkbox_attr = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").get_attribute("aria-checked")
                            response_attr = page.locator("iframe[data-hcaptcha-widget-id]").get_attribute("data-hcaptcha-response")
                            
                            if checkbox_attr == "true" and response_attr and len(response_attr) > 20:
                                verified = True
                                break
                        except: pass
                    
                    if not verified: raise Exception("❌ 验证超时")
                
                # 4. 续费
                print("准备执行续费...")
                ensure_clean_screen(page)
                
                button = page.locator("#renew-button")
                button.wait_for(state="visible", timeout=30000)
                box = button.bounding_box()
                if box:
                    page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                    page.mouse.down()
                    page.mouse.up()
                
                time.sleep(5)
                page.screenshot(path="final.png", full_page=True)
                send_telegram("流程结束。", "final.png")
                    
            except Exception as e:
                error_msg = f"任务执行出错: {str(e)}"
                print(error_msg)
                page.screenshot(path="error.png", full_page=True)
                send_telegram(error_msg, "error.png")

if __name__ == "__main__":
    run_automation()
