import os
import time
import requests
import random
import datetime
from playwright.sync_api import sync_playwright
from browser import BrowserManager 

# ... (依赖项检查与辅助函数定义保持不变) ...

def run_automation():
    if not BASE_URL:
        print("[ERROR] BASE_URL 未定义！")
        return

    with sync_playwright() as p:
        with BrowserManager(p) as context:
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                # 1. 登录
                print(f"[LOG] 正在访问登录页: {BASE_URL}/login")
                page.goto(f"{BASE_URL}/login")
                page.fill("input#email", EMAIL)
                page.fill("input#password", PASSWORD)
                page.get_by_role("button", name="Sign in").click()
                print("[LOG] 已触发 Sign in 点击，等待网络空闲...")
                page.wait_for_load_state("networkidle")
                
                # 2. 状态检查
                print("[LOG] 登录完成，前往服务器信息页...")
                page.goto(f"{BASE_URL}/servers/5541/info")
                page.wait_for_load_state("networkidle")
                
                status_element = page.locator("#server-status")
                status_text = status_element.inner_text().strip()
                print(f"[LOG] 服务器当前状态检测为: {status_text}")
                
                should_renew = (status_text == "Suspended")
                if not should_renew:
                    try:
                        exp_date = datetime.datetime.strptime(status_text, "%d.%m.%Y")
                        days_left = (exp_date - datetime.datetime.now()).total_seconds()
                        if days_left < 7200:
                            print(f"[LOG] 即将过期 (剩余 {days_left/3600:.1f} 小时)，需要续期。")
                            should_renew = True
                        else:
                            print(f"[LOG] 服务器状态健康，无需续期，结束任务。")
                            return
                    except Exception as e:
                        print(f"[LOG] 状态日期解析失败，视作无需续期: {e}")
                        return

                # 3. 进入续期页
                print("[LOG] 正在跳转至续期页面...")
                page.goto(f"{BASE_URL}/service/renew")
                page.wait_for_load_state("networkidle")

                # 4. 人机验证流程 (严格监测 aria-checked)
                print("[LOG] 寻找人机验证模块...")
                checkbox = page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox")
                
                if checkbox.count() > 0:
                    print("[LOG] 发现人机验证，开始交互...")
                    # 尝试点击
                    checkbox.click(force=True)
                    
                    # 严谨的轮询等待
                    for i in range(30):
                        time.sleep(5)
                        force_remove_and_disable_ads(page)
                        is_checked = checkbox.get_attribute("aria-checked")
                        print(f"[LOG] 人机验证监测... 第 {i+1} 次尝试，当前 aria-checked 为: {is_checked}")
                        
                        if is_checked == "true":
                            print("[LOG] 验证已成功勾选！")
                            break
                        else:
                            print("[LOG] 验证尚未通过，正在尝试再次点击...")
                            checkbox.click(force=True)
                else:
                    print("[LOG] 页面未发现人机验证模块，尝试直接执行下一步。")

                # 5. 点击 Renew
                print("[LOG] 准备执行 Renew 按钮点击...")
                renew_btn = page.locator("#renew-button")
                # 只有这里才会触发 30s 超时检查
                cx, cy = human_like_click(page, renew_btn)
                print(f"[LOG] 已成功触发 Renew 点击，坐标: {cx}, {cy}")
                
                time.sleep(10)
                
                # 6. 复核
                page.goto(f"{BASE_URL}/servers/5541/info")
                new_status = page.locator("#server-status").inner_text().strip()
                print(f"[LOG] 最终服务器状态为: {new_status}")
                send_telegram_with_blue_dot(f"流程执行完毕，最终状态: {new_status}", page, cx, cy)
                    
            except Exception as e:
                print(f"[ERROR] 任务执行过程中出现严重错误: {e}")
                send_telegram_with_blue_dot(f"任务出错: {str(e)[:100]}", page)

if __name__ == "__main__":
    run_automation()
