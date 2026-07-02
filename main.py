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
                
                time.sleep(2)
                page.screenshot(path="login_debug.png", full_page=True)
                send_telegram("页面已加载，当前状态截图:", "login_debug.png")
                
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                
                # 登录后缓冲，确保跳转完成
                print("登录中，等待跳转...")
                page.wait_for_load_state("networkidle")
                time.sleep(10) 

                # 2. 访问 Info 页面
                print("访问 Info 页面...")
                page.goto("https://eternalzero.cloud/servers/5541/info")
                time.sleep(5)
                page.reload()
                time.sleep(3)

                # 3. 清理广告 (隐藏而不删除，绕过反广告插件检测)
                page.evaluate("""() => {
                    const guard = document.getElementById('panel-guard-layer');
                    if(guard) { guard.style.display = 'none'; guard.style.visibility = 'hidden'; }
                    const selectors = ['iframe[src*="googleads"]', 'iframe[src*="ads"]', '.adsbygoogle', '#dismiss-button-element', 'button.fc-cta-consent', '.modal-backdrop'];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => {
                            el.style.setProperty('display', 'none', 'important');
                            el.style.setProperty('pointer-events', 'none', 'important');
                        });
                    });
                }""")
                
                # 4. 人机验证检测 (监听 widget 容器的 data-hcaptcha-response 属性)
                if page.locator("iframe[data-hcaptcha-widget-id]").count() > 0:
                    print("检测到 hCaptcha 容器，正在监控验证响应...")
                    
                    try:
                        page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").click(force=True)
                    except: print("尝试触发交互失败，继续等待插件自动识别...")

                    verified = False
                    for i in range(60): # 60次 * 3秒 = 180秒
                        time.sleep(3) 
                        
                        try:
                            # 监测最外层容器的 response 属性
                            widget = page.locator("iframe[data-hcaptcha-widget-id]")
                            response = widget.get_attribute("data-hcaptcha-response")
                            
                            if response and len(response) > 20:
                                print(f"✅ 验证已通过 (Token长度: {len(response)})，立即执行续费！")
                                verified = True
                                break
                            else:
                                print(f"监控中...等待验证成功...")
                        except: pass

                        if i % 4 == 0:
                            page.screenshot(path="monitor.png", full_page=True)
                            send_telegram("监控中...验证码处理中，等待响应注入...", "monitor.png")
                    
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
