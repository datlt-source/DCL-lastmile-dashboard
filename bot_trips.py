import json
import os
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

OUTPUT_FILE = "all_region_trips.json"

# Tự động lấy ngày hôm nay (Ví dụ: "28/06/2026")
TODAY_STR = datetime.now().strftime("%d/%m/%Y")
TARGET_DATE = TODAY_STR 

TODAY_DASH_1 = datetime.now().strftime("%d-%m-%Y")  
TODAY_DASH_2 = datetime.now().strftime("%Y-%m-%d")  

def clean_and_check_date(date_raw):
    if not date_raw:
        return False
    d_str = str(date_raw).strip().lower()
    d_clean = d_str.replace("/", "-")
    if TODAY_DASH_1 in d_clean or TODAY_DASH_2 in d_clean:
        return True
    return False

def calculate_trip_delivery_return(stats_str):
    if not stats_str or not isinstance(stats_str, str):
        return 0
    match = re.search(r'(\d+)-(\d+)-(\d+)', stats_str)
    if match:
        try:
            giao = int(match.group(2))
            tra = int(match.group(3))
            return giao + tra
        except ValueError:
            return 0
    return 0

def run_isolated_trips():
    # --- ĐÃ ĐỔI SANG ĐỌC FILE TỔNG CỦA BẠN TẠI ĐÂY ---
    file_buu_cuc = "all_buu_cuc.json" 
    if not os.path.exists(file_buu_cuc):
        print(f"❌ Không tìm thấy file {file_buu_cuc}. Vui lòng kiểm tra lại bưu cục tổng!")
        return
        
    with open(file_buu_cuc, "r", encoding="utf-8") as f:
        hubs_list = json.load(f)
        
    print(f"🚀 [CHÍNH THỨC] Tìm thấy {len(hubs_list)} bưu cục trong file all_buu_cuc.json.")
    print(f"📅 Hệ thống tự động thiết lập quét ngày hôm nay: {TARGET_DATE}")

    all_trips = []
    captured_ids = set()
    
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                all_trips = json.load(f)
                for t in all_trips:
                    t_id = t.get("id") or t.get("trip_code") or t.get("code")
                    if t_id: captured_ids.add(t_id)
            print(f"ℹ️ Đã nạp nối tiếp {len(all_trips)} chuyến từ file json...")
        except:
            all_trips = []

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir="./bot_profile",
                headless=False,
                channel="chrome"
            )
            page = context.pages[0]
            page.goto("https://nhanh.ghn.vn/lastmile/trip-list?status=ON_TRIP")
            
            print("🌐 Đã mở Chrome ảo.")
            input("Nhấn Enter tại Terminal này sau khi giao diện trang Chuyến đi đã hiển thị đầy đủ...")
            
            tab_captured_count = [0]

            # --- KÊNH 1: INTERCEPT API ---
            def handle_response(response):
                if "trip" in response.url.lower() and response.status == 200:
                    try:
                        res_data = response.json()
                        trips = []
                        if isinstance(res_data, list): trips = res_data
                        elif isinstance(res_data, dict):
                            trips = res_data.get("data") or res_data.get("items") or []
                            if isinstance(trips, dict) and "data" in trips: trips = trips["data"]
                        
                        if isinstance(trips, list) and trips:
                            for trip in trips:
                                trip_id = trip.get("id") or trip.get("trip_code") or trip.get("code")
                                created_at = trip.get("created_at") or trip.get("start_time") or trip.get("createdAt") or ""
                                
                                if trip_id and clean_and_check_date(created_at) and trip_id not in captured_ids:
                                    status_raw = trip.get("status", "")
                                    trip["trip_status_group"] = "Đang chạy" if status_raw == "ON_TRIP" else "Kết thúc"
                                    
                                    logistics_stats = trip.get("total_statistics") or "0-0-0"
                                    trip["delivery_return_sum"] = calculate_trip_delivery_return(logistics_stats)
                                    
                                    driver_obj = trip.get("driver") or {}
                                    if driver_obj:
                                        driver_name = driver_obj.get("name") or driver_obj.get("full_name") or ""
                                        driver_id = driver_obj.get("id") or driver_obj.get("code") or ""
                                        if driver_name:
                                            trip["driver_name"] = f"{driver_id} - {driver_name}" if driver_id else driver_name
                                    
                                    all_trips.append(trip)
                                    captured_ids.add(trip_id)
                                    tab_captured_count[0] += 1
                    except:
                        pass

            page.on("response", handle_response)
            
            for index, hub in enumerate(hubs_list):
                hub_id = hub.get("locationId") or hub.get("id")
                hub_name = hub.get("locationName") or hub.get("name")
                if not hub_id: continue
                
                for status_tab in ["ON_TRIP", "FINISHED"]:
                    tab_captured_count[0] = 0
                    print(f"🔄 [{index+1}/{len(hubs_list)}] Duyệt bưu cục: {hub_name} ({hub_id}) | Tab: {status_tab}")
                    
                    try:
                        page.goto(f"https://nhanh.ghn.vn/lastmile/trip-list?status={status_tab}")
                        page.wait_for_load_state("networkidle")
                        time.sleep(0.8)
                        
                        page.wait_for_selector(".ant-select-selector", timeout=5000)
                        page.locator(".ant-select-selector").first.click()
                        time.sleep(0.3)
                        
                        search_input = page.locator("input.ant-select-selection-search-input").first
                        search_input.fill(str(hub_id))
                        time.sleep(0.3)
                        search_input.press("Enter")
                        
                        time.sleep(3.0) 
                        
                        try:
                            size_changer = page.locator(".ant-pagination-options-size-changer .ant-select-selector")
                            if size_changer.count() > 0:
                                size_changer.first.click()
                                time.sleep(0.5)
                                option_50 = page.locator(".ant-select-item-option-content:has-text('50 / trang')")
                                if option_50.count() > 0:
                                    option_50.first.click()
                                    time.sleep(2.0)
                        except Exception:
                            pass
                        
                        # --- KÊNH 2: DOM SCRAPER ---
                        rows = page.locator(".ant-table-row").all()
                        
                        if rows:
                            for row in rows:
                                try:
                                    row_text = row.inner_text()
                                    if TARGET_DATE in row_text:
                                        match_id = re.search(r'(266\d+[A-Z0-9]+)', row_text)
                                        if match_id:
                                            trip_code = match_id.group(1)
                                            if trip_code not in captured_ids:
                                                
                                                driver_find = "Chưa gán tài xế"
                                                match_driver_code = re.search(r'(\d{5,})', row_text)
                                                if match_driver_code:
                                                    lines = [l.strip() for l in row_text.split("\n") if l.strip()]
                                                    for line in lines:
                                                        if match_driver_code.group(1) in line and "Người tạo" not in line:
                                                            driver_find = line
                                                            break
                                                
                                                stats_match_str = "0-0-0"
                                                stats_match = re.search(r'(\d+-\d+-\d+)', row_text)
                                                if stats_match:
                                                    stats_match_str = stats_match.group(1)
                                                
                                                del_ret_sum = calculate_trip_delivery_return(stats_match_str)
                                                
                                                mock_trip = {
                                                    "id": trip_code,
                                                    "trip_code": trip_code,
                                                    "hub_name": hub_name,
                                                    "hub_id": hub_id,
                                                    "created_at": f"{TARGET_DATE} - Qua UI",
                                                    "driver_name": driver_find,
                                                    "total_statistics": stats_match_str,
                                                    "delivery_return_sum": del_ret_sum,
                                                    "trip_status_group": "Đang chạy" if status_tab == "ON_TRIP" else "Kết thúc"
                                                }
                                                    
                                                all_trips.append(mock_trip)
                                                captured_ids.add(trip_code)
                                                tab_captured_count[0] += 1
                                except Exception:
                                    pass

                        if tab_captured_count[0] > 0:
                            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                                json.dump(all_trips, f, ensure_ascii=False, indent=4)
                            
                    except Exception as e:
                        continue

            context.close()
            print(f"\n✅ ĐÃ HOÀN THÀNH QUÉT TOÀN BỘ CÁC BƯU CỤC TỪ FILE all_buu_cuc.json!")
            
        except Exception as main_e:
            print(f"❌ Lỗi vận hành trình duyệt: {main_e}")

if __name__ == "__main__":
    run_isolated_trips()