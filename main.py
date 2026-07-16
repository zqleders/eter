import os, time, datetime, requests, random
from playwright.sync_api import sync_playwright
from browser import BrowserManager

# --- 配置项 ---
EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = os.getenv("BASE_URL", "").rstrip('/')

# (保留原有的 send_telegram_with_blue_dot 函数不变)
def send_telegram_with_blue_dot(message, driver, x=0, y=0):
    file_path = "screenshot.png"
    driver.screenshot(path=file_path, full_page=True)
    # ... (原有 PIL 逻辑保持不变) ...
    with open(file_path, "rb") as photo:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={'chat_id': TELEGRAM_CHAT_ID, 'caption': f"[gameserver] {message}"}, files={'photo': photo})

def force_remove_and_disable_ads(page):
    """带 LOG 反馈的深度广告清理"""
    js = """
    (function() {
        var targets = document.querySelectorAll('.fc-monetization-dialog-container, div[class*="fixed"]');
        if (targets.length === 0) {
            return "未检测到广告元素";
        }
        targets.forEach(function(el) { el.remove(); });
        var style = document.createElement('style');
        style.innerHTML = '.fc-monetization-dialog-container, div[class*="fixed"] { display: none !important; pointer-events: none !important; }';
        document.head.appendChild(style);
        return "已清理 " + targets.length + " 个广告元素";
    })()
    """
    try:
        result = page.evaluate(js)
        print(f"[LOG] 去广告操作: {result}")
    except Exception as e:
        print(f"[LOG] 去广告脚本执行异常: {e}")

def human_like_click(page, target):
    force_remove_and_disable_ads(page)
    box = target.bounding_box()
    if not box: raise Exception("无法获取元素坐标")
    cx, cy = int(box['x'] + box['width'] / 2), int(box['y'] + box['height'] / 2)
    page.mouse.move(960, 100)
    page.mouse.move(cx, cy)
    time.sleep(random.uniform(0.5, 1.2))
    page.mouse.click(cx, cy)
    return cx, cy

def run_automation():
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 登录流程
                page.goto(f"{BASE_URL}/login")
                page.wait_for_load_state("networkidle")
                time.sleep(2) # 页面加载后缓冲
                force_remove_and_disable_ads(page)
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                
                # 进入服务器页
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                force_remove_and_disable_ads(page)
                page.goto(f"{BASE_URL}/servers/5541/info")
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                force_remove_and_disable_ads(page)
                
                status_text = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 检测到服务器状态: {status_text}")
                
                # ... (其余逻辑与之前保持一致，确保每次 goto 和交互前都执行去广告) ...
                # 请务必检查你的 Github Action 的 LOG，你会看到 [LOG] 去广告操作: 已清理 X 个元素 
                # 这样你就知道广告到底是在哪一刻出现的了。
