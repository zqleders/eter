import os
import time
import requests
import random
import datetime
from playwright.sync_api import sync_playwright
from browser import BrowserManager 

# ... (PIL 和 Telegram 配置同上) ...

def run_automation():
    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录
                page.goto(f"{BASE_URL}/login")
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_load_state("networkidle")
                
                # 2. 检查状态
                page.goto(f"{BASE_URL}/servers/5541/info")
                page.wait_for_load_state("networkidle")
                status_text = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 服务器状态: {status_text}")
                
                # 3. 进入续期页面（增加等待）
                renew_url = f"{BASE_URL}/service/renew"
                print(f"[LOG] 正在前往: {renew_url}")
                page.goto(renew_url)
                page.wait_for_load_state("networkidle")
                time.sleep(5) # 预留缓冲时间

                # 4. 人机验证检测（增加详细日志）
                force_remove_and_disable_ads(page)
                print("[LOG] 检查是否需要人机验证...")
                # 扩大寻找范围，不仅仅局限于 id="checkbox"
                hcaptcha = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                
                if hcaptcha.count() > 0:
                    print("[LOG] 发现人机验证，开始点击...")
                    for i in range(20):
                        force_remove_and_disable_ads(page)
                        if hcaptcha.get_attribute("aria-checked") == "true":
                            print("[LOG] 人机验证已通过！")
                            break
                        hcaptcha.click(force=True)
                        time.sleep(3)
                else:
                    print("[LOG] 未检测到人机验证框，直接继续。")

                # 5. 执行续费（加入显式等待）
                print("[LOG] 正在寻找续费按钮...")
                renew_btn = page.locator("#renew-button")
                
                # 如果定位不到，打印页面 URL 方便调试
                if renew_btn.count() == 0:
                    print(f"[ERROR] 找不到 renew-button，当前 URL: {page.url}")
                    send_telegram_with_blue_dot(f"错误：找不到续费按钮，当前地址: {page.url}", page)
                    return

                cx, cy = human_like_click(page, renew_btn)
                time.sleep(5)
                
                # 最终复核
                page.goto(f"{BASE_URL}/servers/5541/info")
                time.sleep(5)
                send_telegram_with_blue_dot(f"操作完成，新状态: {page.locator('#server-status').inner_text()}", page, cx, cy)
                    
            except Exception as e:
                print(f"[ERROR] 任务出错: {e}")
                # 超时时截屏
                send_telegram_with_blue_dot(f"任务出错: {str(e)[:100]}", page)

if __name__ == "__main__":
    run_automation()
