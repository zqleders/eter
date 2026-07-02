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
    """鲁棒性处理：检测广告、弹窗、欧洲IP合规询问对话框"""
    try:
        # 1. 深度处理 GDPR 弹窗
        consent_buttons = page.get_by_role("button", name="Consent")
        if consent_buttons.count() > 0 and consent_buttons.first.is_visible():
            print("检测到 GDPR 弹窗，点击 Consent...")
            consent_buttons.first.click(force=True)
            time.sleep(2)

        # 2. 深度处理 "View a Short ad" 按钮
        ad_btn = page.locator("button.fc-rewarded-ad-button")
        if ad_btn.count() > 0 and ad_btn.is_visible():
            print("检测到 View a Short ad 按钮，点击触发播放...")
            ad_btn.click(force=True)
            print("广告播放中，等待 25 秒...")
            time.sleep(25) 
            
            # 3. 广告播放完成后，点击关闭按钮
            close_btn = page.locator("#dismiss-button")
            if close_btn.count() > 0 and close_btn.is_visible():
                print("广告播放结束，关闭广告...")
                close_btn.click(force=True)
                time.sleep(2)

        # 4. 基础遮罩清理
        page.evaluate("""() => {
            const guard = document.getElementById('panel-guard-layer');
            if(guard) { guard.style.display = 'none'; }
            document.querySelectorAll('.modal-backdrop, .fc-cta-consent').forEach(el => el.style.display = 'none');
        }""")
    except Exception as e:
        print(f"广告处理过程中的非致命错误: {e}")

def run_automation():
    target_url = "https://eternalzero.cloud/servers/5541/info"
    
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录
                print("访问登录页...")
                page.goto("https://eternalzero.cloud/login")
                time.sleep(2)
                handle_popups_and_ads(page)
                
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                
                print("登录中，等待跳转...")
                page.wait_for_load_state("networkidle")
                time.sleep(10) 

                # 2. 访问并确保跳转到目标页面
                print(f"跳转到目标页面: {target_url}")
                for _ in range(3):
                    page.goto(target_url)
                    time.sleep(5)
                    if page.url == target_url:
                        break
                
                # 3. 循环处理
                for _ in range(5):
                    handle_popups_and_ads(page)
                    time.sleep(3)
                
                # 4. 人机验证监控 (保留每10秒发送截图逻辑)
                if page.locator("iframe[data-hcaptcha-widget-id]").count() > 0:
                    print("检测到 hCaptcha，开始实时监控验证过程...")
                    try:
                        page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").click(force=True)
                    except: pass

                    verified = False
                    for i in range(60):
                        time.sleep(3)
                        handle_popups_and_ads(page)
                        
                        # --- 监控逻辑：每 10 秒发送截图 ---
                        if i % 3 == 0:
                            screenshot_name = f"monitor_{i}.png"
                            page.screenshot(path=screenshot_name, full_page=True)
                            send_telegram(f"监控中 (轮次 {i})...", screenshot_name)

                        try:
                            checkbox_attr = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").get_attribute("aria-checked")
                            response_attr = page.locator("iframe[data-hcaptcha-widget-id]").get_attribute("data-hcaptcha-response")
                            
                            if checkbox_attr == "true" and response_attr and len(response_attr) > 20:
                                print(f"✅ 联合判定通过！")
                                page.screenshot(path="verified_snapshot.png", full_page=True)
                                send_telegram("验证已通过，此时页面状态:", "verified_snapshot.png")
                                verified = True
                                break
                        except: pass
                    
                    if not verified:
                        raise Exception("❌ 超时：验证码未在 180 秒内通过。")
                
                # 5. 续费
                print("验证已通过，进入最终等待校验...")
                time.sleep(8) 
                print("执行续费...")
                handle_popups_and_ads(page)
                page.evaluate("window.renewServer && window.renewServer()")
                
                time.sleep(10)
                page.screenshot(path="final.png", full_page=True)
                send_telegram("流程结束，请查看截图确认续费状态。", "final.png")
                    
            except Exception as e:
                error_msg = f"任务执行出错: {str(e)}"
                print(error_msg)
                page.screenshot(path="error.png", full_page=True)
                send_telegram(error_msg, "error.png")

if __name__ == "__main__":
    run_automation()
