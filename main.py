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
    """鲁棒性处理：广告、弹窗及合规对话框"""
    try:
        # GDPR 弹窗处理
        consent_buttons = page.get_by_role("button", name="Consent")
        if consent_buttons.count() > 0 and consent_buttons.first.is_visible():
            consent_buttons.first.click(force=True)
            time.sleep(2)

        # 广告处理
        ad_btn = page.locator("button.fc-rewarded-ad-button")
        if ad_btn.count() > 0 and ad_btn.is_visible():
            ad_btn.click(force=True)
            time.sleep(25) 
            close_btn = page.locator("#dismiss-button")
            if close_btn.count() > 0 and close_btn.is_visible():
                close_btn.click(force=True)
                time.sleep(2)
    except Exception as e:
        print(f"非致命错误: {e}")

def run_automation():
    target_url = "https://eternalzero.cloud/servers/5541/info"
    
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 登录流程
                page.goto("https://eternalzero.cloud/login")
                handle_popups_and_ads(page)
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                time.sleep(5)

                # 进入目标页
                page.goto(target_url)
                time.sleep(5)
                
                # hCaptcha 验证逻辑 (重构定位)
                # 使用 frame_locator 锁定 iframe，确保能勾选上
                captcha_frame = page.frame_locator("iframe[data-hcaptcha-widget-id]")
                
                if captcha_frame.locator("#checkbox").count() > 0:
                    print("检测到 hCaptcha，正在尝试勾选...")
                    # 确保 frame 加载
                    captcha_frame.locator("#checkbox").click(force=True)
                    
                    verified = False
                    for i in range(60):
                        time.sleep(3)
                        handle_popups_and_ads(page)
                        
                        # 每 10 秒发送监控截图
                        if i % 3 == 0:
                            screenshot_name = f"monitor_{i}.png"
                            page.screenshot(path=screenshot_name, full_page=True)
                            send_telegram(f"监控中 (轮次 {i})...", screenshot_name)

                        # 状态检测逻辑
                        try:
                            # 必须使用之前绑定的 captcha_frame 句柄
                            checkbox_attr = captcha_frame.locator("#checkbox").get_attribute("aria-checked")
                            # 从主页面检查 Token 获取情况
                            response_attr = page.locator("iframe[data-hcaptcha-widget-id]").get_attribute("data-hcaptcha-response")
                            
                            if checkbox_attr == "true" and response_attr and len(response_attr) > 20:
                                print(f"✅ 验证已通过！")
                                page.screenshot(path="verified.png", full_page=True)
                                send_telegram("验证通过！", "verified.png")
                                verified = True
                                break
                        except Exception as e:
                            pass
                    
                    if not verified:
                        raise Exception("❌ 验证超时")
                
                # 执行续费
                print("准备续费...")
                handle_popups_and_ads(page)
                page.evaluate("window.renewServer && window.renewServer()")
                
                time.sleep(10)
                page.screenshot(path="final.png", full_page=True)
                send_telegram("流程结束。", "final.png")
                    
            except Exception as e:
                send_telegram(f"错误: {str(e)}")
                page.screenshot(path="error.png", full_page=True)

if __name__ == "__main__":
    run_automation()
