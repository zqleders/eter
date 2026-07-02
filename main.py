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

def run_automation():
    page = None
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录逻辑
                print("访问登录页...")
                page.goto("https://eternalzero.cloud/login")
                
                # 新增：页面加载后立即截图并发送，便于排查 Timeout 问题
                time.sleep(2)
                page.screenshot(path="login_debug.png", full_page=True)
                send_telegram("页面已加载，当前状态截图:", "login_debug.png")
                
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                time.sleep(5)

                # 2. 访问 Info 页面
                print("访问 Info 页面...")
                page.goto("https://eternalzero.cloud/servers/5541/info")
                time.sleep(5)
                page.reload()
                time.sleep(3)

                # 3. 清理广告
                page.evaluate("""() => {
                    const guard = document.getElementById('panel-guard-layer');
                    if(guard) { guard.style.display = 'none'; guard.style.visibility = 'hidden'; }

                    const selectors = [
                        'iframe[src*="googleads"]', 'iframe[src*="ads"]', 'iframe[src*="doubleclick"]',
                        '.adsbygoogle', '#dismiss-button-element', 'button.fc-cta-consent', '.modal-backdrop'
                    ];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => {
                            el.style.setProperty('display', 'none', 'important');
                            el.style.setProperty('pointer-events', 'none', 'important');
                        });
                    });
                }""")
                
                # 4. 人机验证检测与处理
                if page.locator("iframe[src*='hcaptcha']").count() > 0:
                    print("检测到 hCaptcha 容器...")
                    try:
                        captcha_frame = page.frame_locator("iframe[src*='hcaptcha']")
                        captcha_frame.locator("#checkbox").click(force=True, timeout=5000)
                    except: print("尝试触发交互失败，继续监控...")

                    verified = False
                    for i in range(36): 
                        time.sleep(5) 
                        try:
                            captcha_frame = page.frame_locator("iframe[src*='hcaptcha']")
                            is_checked = captcha_frame.locator("#checkbox, .checkbox-checked").get_attribute("aria-checked") == "true"
                            response = page.evaluate("document.querySelector('[name=h-captcha-response]')?.value")
                            has_response = response and len(response) > 10
                            
                            if is_checked or has_response:
                                print("✅ 验证已通过！")
                                verified = True
                                break
                        except: pass
                        if i % 2 == 0:
                            page.screenshot(path="monitor.png", full_page=True)
                            send_telegram(f"监控中...验证码处理状态: { (i+1)*5 }秒", "monitor.png")
                    
                    if not verified:
                        raise Exception("❌ 超时：验证码未在 180 秒内通过。")
                
                # 5. 续费
                print("执行续费...")
                page.wait_for_selector("#renew-button", state="visible", timeout=30000)
                page.locator("#renew-button").click(force=True)

                time.sleep(5)
                page.screenshot(path="final.png", full_page=True)
                send_telegram("流程结束，续费成功。", "final.png")
                    
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
