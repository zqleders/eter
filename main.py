import os, time, datetime, requests, random
from playwright.sync_api import sync_playwright
from browser import BrowserManager

# --- 依赖项 ---
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# --- 配置 ---
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = os.getenv("BASE_URL", "").rstrip('/')

def send_telegram_with_blue_dot(message, page, x=0, y=0):
    file_path = "screenshot.png"
    page.screenshot(path=file_path, full_page=True)
    if PIL_AVAILABLE and x != 0 and y != 0:
        img = Image.open(file_path)
        draw = ImageDraw.Draw(img)
        r = 20
        draw.ellipse((x - r, y - r, x + r, y + r), fill='blue', outline='blue')
        img.save(file_path)
    with open(file_path, "rb") as photo:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={'chat_id': TELEGRAM_CHAT_ID, 'caption': f"[LOG] {message}"}, files={'photo': photo})

def force_remove_and_disable_ads(page):
    """使用更鲁棒的 ARIA 属性特征进行定位并删除"""
    js = """
    (function() {
        // 使用 aria-label 属性特征定位，这比类名更稳定
        var adDiv = document.querySelector('[aria-label="View a Short ad"]');
        
        // 如果上面找不到，作为备选，尝试查找包含特定按钮文本的容器
        if (!adDiv) {
            var buttons = Array.from(document.querySelectorAll('button'));
            var targetBtn = buttons.find(b => b.innerText && b.innerText.includes('View a short ad'));
            if (targetBtn) {
                // 向上查找其祖先容器，直到找到弹窗的最外层
                adDiv = targetBtn.closest('.fc-monetization-dialog-container') || targetBtn.closest('[role="dialog"]');
            }
        }

        if (adDiv) {
            adDiv.remove();
            return "已通过属性定位并删除广告元素";
        } else {
            return "未检测到广告元素";
        }
    })()
    """
    try:
        res = page.evaluate(js)
        print(f"[LOG] 去广告探测结果: {res}")
    except Exception as e:
        print(f"[LOG] 去广告脚本执行异常: {e}")

def human_like_click(page, target):
    force_remove_and_disable_ads(page)
    box = target.bounding_box()
    if not box: raise Exception("无法获取目标元素的 bounding_box")
    cx, cy = int(box['x'] + box['width'] / 2), int(box['y'] + box['height'] / 2)
    page.mouse.move(960, 100)
    page.mouse.move(cx, cy)
    time.sleep(random.uniform(0.5, 1.2))
    page.mouse.click(cx, cy)
    return cx, cy

def execute_with_ad_cleanup(page, action_func, target):
    try:
        return action_func(page, target)
    except Exception as e:
        print(f"[LOG] 操作受阻，再次清理并重试... 错误: {e}")
        force_remove_and_disable_ads(page)
        return action_func(page, target)

def run_automation():
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录
                print("[LOG] 步骤1: 访问登录页")
                page.goto(f"{BASE_URL}/login")
                time.sleep(3)
                force_remove_and_disable_ads(page)
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                print("[LOG] 步骤1: 点击登录按钮")
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                send_telegram_with_blue_dot("登录成功即时截图（去广告前）", page)
                force_remove_and_disable_ads(page)
                send_telegram_with_blue_dot("登录成功已截图（去广告后）", page)
                
                # 2. 状态检查
                print("[LOG] 步骤2: 访问服务器信息页")
                page.goto(f"{BASE_URL}/servers/5541/info")
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                force_remove_and_disable_ads(page)
                status_text = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 服务器状态: {status_text}")
                send_telegram_with_blue_dot(f"当前状态: {status_text}", page)
                
                if status_text != "Suspended": return

                # 3. 续期页面
                print("[LOG] 步骤3: 访问续期页")
                page.goto(f"{BASE_URL}/service/renew")
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                force_remove_and_disable_ads(page)
                
                # 4. 人机验证
                print("[LOG] 步骤4: 监测人机验证")
                checkbox = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                if checkbox.count() > 0:
                    print("[LOG] 发现人机验证框，尝试交互")
                    checkbox.click(force=True)
                    for i in range(20):
                        time.sleep(5)
                        force_remove_and_disable_ads(page)
                        status = checkbox.get_attribute("aria-checked")
                        print(f"[LOG] 人机验证检测中 (第{i+1}次): {status}")
                        if status == "true":
                            print("[LOG] 人机验证通过")
                            send_telegram_with_blue_dot("人机验证通过", page)
                            break
                        checkbox.click(force=True)
                
                # 5. 执行续期
                print("[LOG] 步骤5: 执行续期点击")
                renew_btn = page.locator("#renew-button")
                cx, cy = execute_with_ad_cleanup(page, human_like_click, renew_btn)
                print(f"[LOG] Renew 按钮已点击，坐标: {cx}, {cy}")
                send_telegram_with_blue_dot("续期按钮已点击", page, cx, cy)
                
                # 6. 复核
                time.sleep(5)
                page.goto(f"{BASE_URL}/servers/5541/info")
                time.sleep(3)
                force_remove_and_disable_ads(page)
                final_status = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 续期最终状态: {final_status}")
                send_telegram_with_blue_dot(f"续期结束，状态: {final_status}", page)
                    
            except Exception as e:
                print(f"[LOG] 流程出错: {e}")
                try: send_telegram_with_blue_dot(f"出错原因: {str(e)[:50]}", page)
                except: pass

if __name__ == "__main__":
    run_automation()
