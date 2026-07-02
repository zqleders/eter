import os
import time
import requests
from playwright.sync_api import sync_playwright
from browser import BrowserManager  # 使用你要求的 BrowserManager

# 获取环境配置
EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message, photo_path=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': f})
    except Exception as e:
        print(f"Telegram 发送失败: {e}")

def run_automation():
    page = None
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录逻辑 (我们的业务)
                print("访问登录页...")
                page.goto("https://eternalzero.cloud/login")
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                time.sleep(5)

                # 2. 访问 Info 页面 (我们的业务)
                print("访问 Info 页面...")
                page.goto("https://eternalzero.cloud/servers/5541/info")
                time.sleep(5)

                # 3. 清理广告 (我们的业务)
                page.evaluate("""() => {
                    const selectors = ['button.fc-cta-consent', 'button.fc-rewarded-ad-button', '#dismiss-button-element', 'ins.adsbygoogle', 'iframe[src*="ads"]', '.modal-backdrop'];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => { if(el.offsetParent !== null) el.click(); });
                    });
                }""")
                
                print("点击 Renew server...")
                page.wait_for_selector("#renew-button", state="visible", timeout=30000)
                page.locator("#renew-button").click(force=True)
                
                # 4. 验证码监控逻辑 (100% COPY 逻辑)
                time.sleep(3)
                # 针对 hCaptcha 调整选择器，通常容器包含 h-captcha
                if page.locator("iframe[src*='hcaptcha']").count() > 0:
                    print("检测到验证码，准备激活...")
                    try:
                        # 尝试点击验证框
                        page.locator("iframe[src*='hcaptcha']").content_frame.locator("#checkbox").click()
                    except: pass
                    
                    print("开始实时监控验证过程...")
                    for i in range(18): # 总共 180 秒监控
                        time.sleep(10)
                        screenshot_name = f"monitor_{i}.png"
                        page.screenshot(path=screenshot_name, full_page=True)
                        send_telegram(f"验证码处理中... ({ (i+1)*10 }秒)", screenshot_name)
                        
                        # 检查验证码是否消失 (hcaptcha 通常在解决后会更新或消失)
                        if page.locator("iframe[src*='hcaptcha']").count() == 0:
                            print("✅ 验证码已通过！")
                            break
                
                print("执行最终确认...")
                try:
                    page.locator("#renew-button").click(force=True)
                except Exception as e:
                    print(f"最终确认失败: {e}")

                time.sleep(5)
                page.screenshot(path="final.png", full_page=True)
                send_telegram("流程结束，查看截图确认结果。", "final.png")
                    
            except Exception as e:
                error_msg = f"任务执行出错: {str(e)}"
                print(error_msg)
                if page:
                    page.screenshot(path="error.png", full_page=True)
                    send_telegram(error_msg, "error.png")
                else:
                    send_telegram(error_msg)

if __name__ == "__main__":
    run_automation()
