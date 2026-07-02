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
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                time.sleep(5)

                # 2. 访问 Info 页面
                print("访问 Info 页面...")
                page.goto("https://eternalzero.cloud/servers/5541/info")
                time.sleep(5)

                # 3. 强制页面刷新一次，有时能触发插件重新挂载到 DOM
                page.reload()
                time.sleep(3)

                # 4. 清理广告
                page.evaluate("""() => {
                    const selectors = ['button.fc-cta-consent', 'button.fc-rewarded-ad-button', '#dismiss-button-element', 'ins.adsbygoogle', 'iframe[src*="ads"]', '.modal-backdrop'];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => { if(el.offsetParent !== null) el.click(); });
                    });
                }""")
                
                # 5. 人机验证检测与处理
                if page.locator("iframe[src*='hcaptcha']").count() > 0:
                    print("检测到 hCaptcha 容器...")
                    print("开始实时监控验证过程...")
                    verified = False
                    
                    # 循环检测 (最多 180 秒)
                    for i in range(36): 
                        time.sleep(5) 
                        
                        try:
                            # 方式一：检测打勾状态 (aria-checked)
                            captcha_frame = page.frame_locator("iframe[src*='hcaptcha']")
                            is_checked = captcha_frame.locator("#checkbox, .checkbox-checked").get_attribute("aria-checked") == "true"
                            
                            # 方式二：检测 Response 注入
                            response = page.evaluate("document.querySelector('[name=h-captcha-response]')?.value")
                            has_response = response and len(response) > 10
                            
                            if is_checked or has_response:
                                print("✅ 检测到验证已通过，立即执行续费！")
                                verified = True
                                break
                        except Exception:
                            pass

                        # 状态监控截图
                        if i % 2 == 0:
                            screenshot_name = f"monitor_{i}.png"
                            page.screenshot(path=screenshot_name, full_page=True)
                            send_telegram(f"监控中...验证码处理状态: { (i+1)*5 }秒", screenshot_name)
                    
                    if not verified:
                        raise Exception("❌ 超时：验证码在 180 秒内未通过。")
                
                # 6. 续费
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
