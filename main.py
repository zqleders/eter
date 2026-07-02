# 4. 人机验证检测 (精准监测容器属性变化)
                if page.locator("iframe[data-hcaptcha-widget-id]").count() > 0:
                    print("检测到 hCaptcha 容器，正在监控验证响应...")
                    
                    # 尝试点击触发
                    try:
                        page.frame_locator("iframe[data-hcaptcha-widget-id]").locator("#checkbox").click(force=True)
                    except: pass

                    verified = False
                    for i in range(60): # 循环 60 次，每次 3 秒
                        time.sleep(3) 
                        
                        # 检测逻辑：直接检查 iframe 容器本身的 data-hcaptcha-response 属性
                        # 验证通过时，该属性会被注入一个长字符串
                        try:
                            # 获取主 iframe 元素
                            widget_iframe = page.locator("iframe[data-hcaptcha-widget-id]")
                            response_val = widget_iframe.get_attribute("data-hcaptcha-response")
                            
                            # 如果该属性不为空且长度大于 20，说明验证已成功
                            if response_val and len(response_val) > 20:
                                print(f"✅ 检测到已通过验证，响应已注入: {response_val[:10]}...")
                                verified = True
                                break
                            else:
                                print(f"监控中...当前 response 属性: {response_val}")
                                
                        except Exception as e:
                            pass

                        if i % 4 == 0:
                            page.screenshot(path="monitor.png", full_page=True)
                            send_telegram("监控中...验证码处理中，等待响应注入...", "monitor.png")
                    
                    if not verified:
                        raise Exception("❌ 超时：验证码在 180 秒内未通过。")
