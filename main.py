import asyncio
import argparse
import json
import urllib.parse
from playwright.async_api import async_playwright, TimeoutError

async def unlocker(page, xsrf_token, modules_data):
    last_lessons = {}
    
    for module_id, lesson_ids in modules_data.items():
        if lesson_ids:
            last_lessons[module_id] = lesson_ids[-1]
            modules_data[module_id] = lesson_ids[:-1]
    
    total_regular_lessons = sum(len(lessons) for lessons in modules_data.values())
    processed = 0
    successful = 0
    failed = 0
    completed_successful = 0
    completed_failed = 0
    
    print(f"Starting to process {total_regular_lessons} regular lessons across {len(modules_data)} modules...")
    print(f"Last lessons (to be processed later): {list(last_lessons.values())}")
    
    payload_template = {
        "data": {
            "cmi": {
                "suspend_data": "{\"audio\":[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],\"video\":[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],\"doc\":[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],\"quiz\":[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],\"game\":[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],\"slider\":[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],\"quiz_results\":{}}"
            }
        }
    }
    
    first_lesson_payload = {
        "data": {
            "cmi": {
                "core": {
                    "score": {
                        "raw": "100"
                    },
                    "lesson_status": "completed",
                    "session_time": "00:00:30"
                }
            }
        }
    }
    
    completion_payload = {
        "data": {
            "cmi": {
                "core": {
                    "lesson_status": "completed"
                }
            }
        }
    }
    
    context = page.context
    
    failed_lessons = {}
    
    for module_id, lesson_ids in modules_data.items():
        print(f"\n--- Processing module {module_id} with {len(lesson_ids)} regular lessons ---")
        failed_lessons[module_id] = []
        
        try:
            print(f"Visiting module page: https://b5.engagebricks.com/modules/{module_id}")
            module_response = await page.goto(f"https://b5.engagebricks.com/modules/{module_id}")
            
            if module_response.status >= 200 and module_response.status < 300:
                print(f"✅ Successfully loaded module {module_id} page (Status: {module_response.status})")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
            else:
                print(f"⚠️ Failed to load module {module_id} page (Status: {module_response.status})")
                print(f"   Will still attempt to process lessons")
        
        except Exception as e:
            print(f"⚠️ Error loading module {module_id} page: {str(e)}")
            print(f"   Will still attempt to process lessons")
        
        lesson_idx = 0
        while lesson_idx < len(lesson_ids):
            lesson_id = lesson_ids[lesson_idx]
            processed += 1
            
            try:
                lesson_page = await context.new_page()
                lesson_url = f"https://b5.engagebricks.com/lessons/{lesson_id}"
                print(f"Opening lesson page: {lesson_url}")
                
                await lesson_page.goto(lesson_url)
                await lesson_page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                await lesson_page.close()
                
                lessons_response = await page.request.post(
                    f'https://b5.engagebricks.com/api/lessons/{lesson_id}',
                    headers={
                        'x-requested-with': 'XMLHttpRequest',
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-XSRF-TOKEN': xsrf_token or ''
                    },
                    data=json.dumps(payload_template)
                )
                
                lessons_text = await lessons_response.text()
                
                if lesson_idx == 0:
                    print(f"Making additional request for first lesson in module {module_id}")
                    
                    first_lesson_response = await page.request.post(
                        f'https://b5.engagebricks.com/api/lessons/{lesson_id}',
                        headers={
                            'x-requested-with': 'XMLHttpRequest',
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'X-XSRF-TOKEN': xsrf_token or ''
                        },
                        data=json.dumps(first_lesson_payload)
                    )
                    
                    first_lesson_text = await first_lesson_response.text()
                    
                    if first_lesson_response.status >= 200 and first_lesson_response.status < 300:
                        print(f"✅ Additional request for first lesson in module {module_id}: SUCCESS")
                    else:
                        print(f"⚠️ Additional request for first lesson in module {module_id}: FAILED ({first_lesson_response.status})")
                        print(f"   Response: {first_lesson_text[:100]}...")
                    
                    await asyncio.sleep(1)
                
                if lessons_response.status >= 200 and lessons_response.status < 300:
                    successful += 1
                    print(f"✅ Lesson {lesson_id} (Module {module_id}): SUCCESS")
                    
                    print(f"   Marking lesson {lesson_id} as completed...")
                    completion_response = await page.request.post(
                        f'https://b5.engagebricks.com/api/lessons/{lesson_id}',
                        headers={
                            'x-requested-with': 'XMLHttpRequest',
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'X-XSRF-TOKEN': xsrf_token or ''
                        },
                        data=json.dumps(completion_payload)
                    )
                    
                    completion_text = await completion_response.text()
                    
                    if completion_response.status >= 200 and completion_response.status < 300:
                        completed_successful += 1
                        print(f"   ✅ Lesson {lesson_id} successfully marked as completed")
                    else:
                        completed_failed += 1
                        print(f"   ❌ Failed to mark lesson {lesson_id} as completed ({completion_response.status})")
                        print(f"      Response: {completion_text[:100]}...")
                    
                    lesson_idx += 1
                else:
                    failed += 1
                    print(f"❌ Lesson {lesson_id} (Module {module_id}): FAILED ({lessons_response.status})")
                    print(f"   Response: {lessons_text[:100]}...")
                    print(f"   Will retry this lesson after a delay...")
                    failed_lessons[module_id].append(lesson_id)
                    await asyncio.sleep(5)
                    
                    await page.goto(f"https://b5.engagebricks.com/modules/{module_id}")
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(3)
                    
                await asyncio.sleep(1)
                
            except Exception as e:
                failed += 1
                print(f"❌ Lesson {lesson_id} (Module {module_id}): ERROR - {str(e)}")
                failed_lessons[module_id].append(lesson_id)
                
                await page.goto(f"https://b5.engagebricks.com/modules/{module_id}")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)
                
            if processed % 10 == 0:
                print(f"Progress: {processed}/{total_regular_lessons} lessons processed ({successful} successful, {failed} failed)")
                print(f"Completion status: {completed_successful} marked as completed, {completed_failed} completion failures")
    
    retry_count = sum(len(lessons) for lessons in failed_lessons.values())
    if retry_count > 0:
        print(f"\n{retry_count} lessons failed during initial processing. Retrying with longer delays...")
        
        for module_id, failed_ids in failed_lessons.items():
            if not failed_ids:
                continue
                
            print(f"\n--- Retrying failed lessons in module {module_id} ---")
            
            await page.goto(f"https://b5.engagebricks.com/modules/{module_id}")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            for lesson_id in failed_ids:
                print(f"Retrying lesson {lesson_id} (Module {module_id})...")
                
                try:
                    lesson_page = await context.new_page()
                    lesson_url = f"https://b5.engagebricks.com/lessons/{lesson_id}"
                    print(f"Opening lesson page: {lesson_url}")
                    
                    await lesson_page.goto(lesson_url)
                    await lesson_page.wait_for_load_state("networkidle")
                    await asyncio.sleep(3)
                    await lesson_page.close()
                    
                    lessons_response = await page.request.post(
                        f'https://b5.engagebricks.com/api/lessons/{lesson_id}',
                        headers={
                            'x-requested-with': 'XMLHttpRequest',
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'X-XSRF-TOKEN': xsrf_token or ''
                        },
                        data=json.dumps(payload_template)
                    )
                    
                    lessons_text = await lessons_response.text()
                    
                    if lessons_response.status >= 200 and lessons_response.status < 300:
                        successful += 1
                        failed -= 1
                        print(f"✅ Retry successful for lesson {lesson_id} (Module {module_id})")
                        
                        print(f"   Marking lesson {lesson_id} as completed...")
                        completion_response = await page.request.post(
                            f'https://b5.engagebricks.com/api/lessons/{lesson_id}',
                            headers={
                                'x-requested-with': 'XMLHttpRequest',
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                                'X-XSRF-TOKEN': xsrf_token or ''
                            },
                            data=json.dumps(completion_payload)
                        )
                        
                        completion_text = await completion_response.text()
                        
                        if completion_response.status >= 200 and completion_response.status < 300:
                            completed_successful += 1
                            print(f"   ✅ Lesson {lesson_id} successfully marked as completed")
                        else:
                            completed_failed += 1
                            print(f"   ❌ Failed to mark lesson {lesson_id} as completed ({completion_response.status})")
                            print(f"      Response: {completion_text[:100]}...")
                    else:
                        print(f"❌ Retry failed for lesson {lesson_id} (Module {module_id}): ({lessons_response.status})")
                        print(f"   Response: {lessons_text[:100]}...")
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"❌ Retry error for lesson {lesson_id} (Module {module_id}): {str(e)}")
                    await asyncio.sleep(2)
    
    print(f"\nPhase 1 complete! Processed {total_regular_lessons} regular lessons:")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"Completion status: {completed_successful} marked as completed, {completed_failed} completion failures")
    
    print("\n--- PHASE 2: Processing LAST lessons of each module ---")
    
    last_processed = 0
    last_successful = 0
    last_failed = 0
    last_completed_successful = 0
    last_completed_failed = 0
    
    for module_id, last_lesson_id in last_lessons.items():
        print(f"\n--- Processing last lesson {last_lesson_id} for module {module_id} ---")
        
        try:
            await page.goto(f"https://b5.engagebricks.com/modules/{module_id}")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            lesson_page = await context.new_page()
            lesson_url = f"https://b5.engagebricks.com/lessons/{last_lesson_id}"
            print(f"Opening last lesson page: {lesson_url}")
            
            await lesson_page.goto(lesson_url)
            await lesson_page.wait_for_load_state("networkidle") 
            await asyncio.sleep(3)
            await lesson_page.close()
            
            last_response = await page.request.post(
                f'https://b5.engagebricks.com/api/lessons/{last_lesson_id}',
                headers={
                    'x-requested-with': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-XSRF-TOKEN': xsrf_token or ''
                },
                data=json.dumps(payload_template)
            )
            
            last_text = await last_response.text()
            last_processed += 1
            
            if last_response.status >= 200 and last_response.status < 300:
                last_successful += 1
                print(f"✅ Last lesson {last_lesson_id} (Module {module_id}): SUCCESS")
                
                print(f"   Marking last lesson {last_lesson_id} as completed...")
                completion_response = await page.request.post(
                    f'https://b5.engagebricks.com/api/lessons/{last_lesson_id}',
                    headers={
                        'x-requested-with': 'XMLHttpRequest',
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-XSRF-TOKEN': xsrf_token or ''
                    },
                    data=json.dumps(completion_payload)
                )
                
                completion_text = await completion_response.text()
                
                if completion_response.status >= 200 and completion_response.status < 300:
                    last_completed_successful += 1
                    print(f"   ✅ Last lesson {last_lesson_id} successfully marked as completed")
                    
                    print(f"   Sending first_lesson_payload for last lesson {last_lesson_id}...")
                    first_lesson_response = await page.request.post(
                        f'https://b5.engagebricks.com/api/lessons/{last_lesson_id}',
                        headers={
                            'x-requested-with': 'XMLHttpRequest',
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'X-XSRF-TOKEN': xsrf_token or ''
                        },
                        data=json.dumps(first_lesson_payload)
                    )
                    
                    first_lesson_text = await first_lesson_response.text()
                    
                    if first_lesson_response.status >= 200 and first_lesson_response.status < 300:
                        print(f"   ✅ Successfully sent first_lesson_payload for last lesson {last_lesson_id}")
                    else:
                        print(f"   ❌ Failed to send first_lesson_payload for last lesson {last_lesson_id} ({first_lesson_response.status})")
                        print(f"      Response: {first_lesson_text[:100]}...")
                        
                else:
                    last_completed_failed += 1
                    print(f"   ❌ Failed to mark last lesson {last_lesson_id} as completed ({completion_response.status})")
                    print(f"      Response: {completion_text[:100]}...")
            else:
                last_failed += 1
                print(f"❌ Last lesson {last_lesson_id} (Module {module_id}): FAILED ({last_response.status})")
                print(f"   Response: {last_text[:100]}...")
                
                print(f"   Retrying last lesson {last_lesson_id}...")
                await asyncio.sleep(5)
                
                retry_page = await context.new_page()
                await retry_page.goto(lesson_url)
                await retry_page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)
                await retry_page.close()
                
                retry_response = await page.request.post(
                    f'https://b5.engagebricks.com/api/lessons/{last_lesson_id}',
                    headers={
                        'x-requested-with': 'XMLHttpRequest',
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-XSRF-TOKEN': xsrf_token or ''
                    },
                    data=json.dumps(payload_template)
                )
                
                retry_text = await retry_response.text()
                
                if retry_response.status >= 200 and retry_response.status < 300:
                    last_successful += 1
                    last_failed -= 1
                    print(f"✅ Retry successful for last lesson {last_lesson_id} (Module {module_id})")
                    
                    print(f"   Marking last lesson {last_lesson_id} as completed...")
                    completion_response = await page.request.post(
                        f'https://b5.engagebricks.com/api/lessons/{last_lesson_id}',
                        headers={
                            'x-requested-with': 'XMLHttpRequest',
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'X-XSRF-TOKEN': xsrf_token or ''
                        },
                        data=json.dumps(completion_payload)
                    )
                    
                    completion_text = await completion_response.text()
                    
                    if completion_response.status >= 200 and completion_response.status < 300:
                        last_completed_successful += 1
                        print(f"   ✅ Last lesson {last_lesson_id} successfully marked as completed")
                        
                        print(f"   Sending first_lesson_payload for last lesson {last_lesson_id}...")
                        first_lesson_response = await page.request.post(
                            f'https://b5.engagebricks.com/api/lessons/{last_lesson_id}',
                            headers={
                                'x-requested-with': 'XMLHttpRequest',
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                                'X-XSRF-TOKEN': xsrf_token or ''
                            },
                            data=json.dumps(first_lesson_payload)
                        )
                        
                        first_lesson_text = await first_lesson_response.text()
                        
                        if first_lesson_response.status >= 200 and first_lesson_response.status < 300:
                            print(f"   ✅ Successfully sent first_lesson_payload for last lesson {last_lesson_id}")
                        else:
                            print(f"   ❌ Failed to send first_lesson_payload for last lesson {last_lesson_id} ({first_lesson_response.status})")
                            print(f"      Response: {first_lesson_text[:100]}...")
                            
                    else:
                        last_completed_failed += 1
                        print(f"   ❌ Failed to mark last lesson {last_lesson_id} as completed ({completion_response.status})")
                        print(f"      Response: {completion_text[:100]}...")
                else:
                    print(f"❌ Retry failed for last lesson {last_lesson_id} (Module {module_id}): ({retry_response.status})")
                    print(f"   Response: {retry_text[:100]}...")
            
            await asyncio.sleep(2)
            
        except Exception as e:
            last_failed += 1
            print(f"❌ Last lesson {last_lesson_id} (Module {module_id}): ERROR - {str(e)}")
    
    print(f"\nPhase 2 complete! Processed {last_processed} last lessons:")
    print(f"✅ Successful: {last_successful}")
    print(f"❌ Failed: {last_failed}")
    print(f"Completion status: {last_completed_successful} marked as completed, {last_completed_failed} completion failures")
    
    total_successful = successful + last_successful
    total_failed = failed + last_failed
    total_completed_successful = completed_successful + last_completed_successful
    total_completed_failed = completed_failed + last_completed_failed
    
    print("\n--- FINAL RESULTS ---")
    print(f"Total lessons processed: {total_regular_lessons + len(last_lessons)}")
    print(f"✅ Total unlock successful: {total_successful}")
    print(f"❌ Total unlock failed: {total_failed}")
    print(f"✅ Total completion successful: {total_completed_successful}")
    print(f"❌ Total completion failed: {total_completed_failed}")
    
    return total_successful, total_failed, total_completed_successful, total_completed_failed

async def main(username, password):
    modules_data = {
        "305": [589, 865, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603],
        "306": [604, 866, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624],
        "307": [625, 867, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638],
        "308": [639, 868, 640, 641, 642, 643, 644, 645, 646, 647, 648],
        "309": [649, 650, 651, 652, 653, 654, 655, 656, 657, 658],
        "310": [659, 660, 661, 662, 663, 664, 665, 666, 667],
        "311": [668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679],
        "312": [680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691]
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        xsrf_token = None
        
        async def on_response(response):
            nonlocal xsrf_token
            
            if response.request.method == "POST" and "/login" in response.url:
                headers = response.headers
                if "set-cookie" in headers:
                    cookies = headers["set-cookie"].split(", ")
                    for cookie in cookies:
                        if "XSRF-TOKEN=" in cookie:
                            token_part = cookie.split("XSRF-TOKEN=")[1].split(";")[0]
                            xsrf_token = urllib.parse.unquote(token_part)
                            print(f"XSRF token captured from response: {xsrf_token}")
        
        page = await context.new_page()
        page.on("response", on_response)
        
        try:
            await page.goto('https://startupyourlife.engagebricks.com/login')
            await page.wait_for_selector('form', timeout=10000)
            
            email_selectors = ['input[type="email"]', 'input[name="email"]', 'input[id="email"]']
            for selector in email_selectors:
                if await page.query_selector(selector):
                    await page.fill(selector, username)
                    break
            
            password_selectors = ['input[type="password"]', 'input[name="password"]', 'input[id="password"]']
            for selector in password_selectors:
                if await page.query_selector(selector):
                    await page.fill(selector, password)
                    break
            
            submit_selectors = ['button[type="submit"]', 'input[type="submit"]']
            for selector in submit_selectors:
                if await page.query_selector(selector):
                    await page.click(selector)
                    break
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            if not xsrf_token:
                cookies = await context.cookies()
                for cookie in cookies:
                    if cookie["name"] == "XSRF-TOKEN":
                        xsrf_token = urllib.parse.unquote(cookie["value"])
                        print(f"XSRF token captured from cookies: {xsrf_token}")
                        break
            
            if not xsrf_token:
                print("XSRF token not found. Authentication may fail.")
                return
            
            status_response = await page.request.get(
                'https://b5.engagebricks.com/api/campaigns/30/20018/status',
                headers={
                    'x-requested-with': 'XMLHttpRequest',
                    'X-XSRF-TOKEN': xsrf_token or ''
                }
            )
            
            status_text = await status_response.text()
            
            if "unauthorized" in status_text.lower():
                print("Failed: Unauthorized access")
                print(f"Response: {status_text}")
            else:
                print("Status check successful")
                print(f"Status response: {status_text}")
                
                await unlocker(page, xsrf_token, modules_data)
            
            print("Script completed. Browser will close in 5 seconds...")
            await asyncio.sleep(5)
            
        except TimeoutError as e:
            print(f"Operation timed out: {str(e)}")
        except Exception as e:
            print(f"Error: {str(e)}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Login to Engage Bricks and unlock lessons')
    parser.add_argument('--username', required=True, help='Login username')
    parser.add_argument('--password', required=True, help='Login password')
    
    args = parser.parse_args()
    
    asyncio.run(main(args.username, args.password))
