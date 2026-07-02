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
    """鲁棒性处理：检测广告按钮、弹窗并交互"""
    try:
        # 1. 检查奖励广告按钮
        reward_ad_btn = page.locator("button.fc-rewarded-ad-button")
        if reward_ad_btn.count() > 0 and reward_ad_btn.is_visible():
            print("检测到奖励广告按钮，点击观看...")
            reward_ad_btn.click(force=True)
            time.sleep(22)  # 等待广告播放
            
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
                
                time.sleep(2)
                page.screenshot(path="login_debug.png", full_page=True)
                send_telegram("页面已加载，当前状态截图:", "login_debug.png")
                
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
                    if page.url != target_url:
                        print(f"当前 URL 为 {page.url}，与目标不符，重新尝试访问...")
                        continue
                    else:
                        break
                
                # 3. 广告处理
                handle_popups_and_ads(page)
                
                # 4. 人机验证检测
                if page.locator("iframe[data-hcaptcha-widget-id]").count() > 0:
                    print("检测到 hCaptcha，开始实时监控验证过程...")
                    try:
                        page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").click(force=True)
                    except: print("尝试触发交互失败，继续等待插件自动识别...")

                    verified = False
                    for i in range(60):
                        time.sleep(3)
                        handle_popups_and_ads(page)
                        
                        try:
                            checkbox_attr = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").get_attribute("aria-checked")
                            widget = page.locator("iframe[data-hcaptcha-widget-id]")
                            response_attr = widget.get_attribute("data-hcaptcha-response")
                            
                            print(f"[调试日志] 轮次 {i+1}: aria-checked='{checkbox_attr}', response_len={len(response_attr) if response_attr else 0}")
                            
                            if checkbox_attr == "true" and response_attr and len(response_attr) > 20:
                                print(f"✅ 联合判定通过！aria-checked='{checkbox_attr}', Token长度={len(response_attr)}")
                                page.screenshot(path="verified_snapshot.png", full_page=True)
                                send_telegram("验证已通过，此时页面状态:", "verified_snapshot.png")
                                verified = True
                                break
                        except Exception as e:
                            print(f"[调试日志] 读取属性出错: {e}")
                            
                        if i % 3 == 0:
                            screenshot_name = f"monitor_{i}.png"
                            page.screenshot(path=screenshot_name, full_page=True)
                            send_telegram(f"监控中...状态: 勾选={checkbox_attr if 'checkbox_attr' in locals() else '未知'} | Token长度={len(response_attr) if 'response_attr' in locals() and response_attr else 0}", screenshot_name)
                    
                    if not verified:
                        raise Exception("❌ 超时：验证码未在 180 秒内通过。")
                
                # 5. 续费
                print("验证已通过，进入最终等待校验...")
                # 额外增加一次等待，确保 Token 在网页后台已激活
                time.sleep(8) 
                
                print("执行续费...")
                handle_popups_and_ads(page)
                
                # 核心改进：直接执行 JS 调用
                # 这种方式不触发任何鼠标事件，能最大限度减少对页面其他元素的“干扰”
                print("准备直接调用 JS renewServer()...")
                page.evaluate("window.renewServer && window.renewServer()")
                
                # 点击后等待 10 秒，观察页面是否重定向或发生变化
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
