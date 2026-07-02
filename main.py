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
    """鲁棒性处理：检测广告按钮并进行交互"""
    try:
        # 1. 检查奖励广告按钮 (View a short ad)
        reward_ad_btn = page.locator("button.fc-rewarded-ad-button")
        if reward_ad_btn.count() > 0 and reward_ad_btn.is_visible():
            print("检测到奖励广告按钮，点击观看...")
            reward_ad_btn.click(force=True)
            time.sleep(20)  # 等待广告播放
            
            # 2. 点击关闭按钮
            close_btn = page.locator("#dismiss-button")
            if close_btn.count() > 0 and close_btn.is_visible():
                print("广告播放结束，关闭广告...")
                close_btn.click(force=True)
                time.sleep(2)

        # 3. 基础遮罩清理
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
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                time.sleep(10) 

                # 2. 访问并确保跳转到目标页面
                print(f"跳转到目标页面: {target_url}")
                for _ in range(3): # 最多重试3次
                    page.goto(target_url)
                    time.sleep(5)
                    if page.url == target_url:
                        break
                    print("跳转未成功，重试中...")
                
                # 3. 主循环前清理广告与弹窗
                handle_popups_and_ads(page)
                
                # 4. 人机验证检测
                if page.locator("iframe[data-hcaptcha-widget-id]").count() > 0:
                    print("检测到 hCaptcha，监控验证响应...")
                    try:
                        page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").click(force=True)
                    except: pass

                    verified = False
                    for i in range(60):
                        time.sleep(3)
                        # 再次处理可能出现的弹窗
                        handle_popups_and_ads(page)
                        
                        widget = page.locator("iframe[data-hcaptcha-widget-id]")
                        response = widget.get_attribute("data-hcaptcha-response")
                        if response and len(response) > 20:
                            print("✅ 验证通过！")
                            verified = True
                            break
                    if not verified: raise Exception("人机验证超时")
                
                # 5. 续费
                print("执行续费...")
                handle_popups_and_ads(page)
                page.wait_for_selector("#renew-button", state="visible", timeout=30000)
                page.locator("#renew-button").click(force=True)

                time.sleep(5)
                page.screenshot(path="final.png", full_page=True)
                send_telegram("续费成功。", "final.png")
                    
            except Exception as e:
                error_msg = f"任务执行出错: {str(e)}"
                print(error_msg)
                page.screenshot(path="error.png", full_page=True)
                send_telegram(error_msg, "error.png")

if __name__ == "__main__":
    run_automation()
