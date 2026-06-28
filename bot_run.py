import json
import os
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

OUTPUT_FILE = "all_region_trips.json"

# 🔥 TỰ ĐỘNG LẤY NGÀY HÔM NAY THEO ĐỊNH DẠNG HỆ THỐNG GHN (DD/MM/YYYY)
TODAY_STR = datetime.now().strftime("%d/%m/%Y")

def clean_and_check_date(date_raw):
    if not date_raw:
        return False
    d_str = str(date_raw).strip().lower()
    d_clean = d_str.replace("/", "-")
    
    # Tạo chuỗi ngày hôm nay dạng gạch ngang để check map dữ liệu ngầm
    today_dash = TODAY_STR.replace("/", "-")
    today_reverse = datetime.now().strftime("%Y-%m-%d")
    
    if today_dash in d_clean or today_reverse in d_clean:
        return True
    return False

def run_click_and_intercept():
    file_buu_cuc = "all_buu_cuc.json"
    if not os.path.exists(file_buu_cuc):
        print("❌ Không tìm thấy file all_buu_cuc.json")
        return
        
    with open(file_buu_cuc, "r", encoding="utf-8") as f:
        hubs_list = json.load(f)
        
    print(f"🚀 Tiến hành quét dữ liệu vận hành & tồn đọng TỰ ĐỘNG ngày hôm nay: {TODAY_STR}")

    all_trips = []
    backlog_data = {}  
    captured_ids = set()

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            
            tab_captured_count = [0]

            # --- KÊNH INTERCEPT API (CHUYẾN ĐI) ---
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
            
            # ================= GIAI ĐOẠN 1: QUÉT CHUYẾN ĐI VÀ NHÂN SỰ =================
            for index, hub in enumerate(hubs_list):
                hub_id = hub.get("locationId")
                hub_name = hub.get("locationName")
                if not hub_id: continue
                
                for status_tab in ["ON_TRIP", "FINISHED"]:
                    tab_captured_count[0] = 0
                    print(f"🔄 [Chuyến đi {index+1}/{len(hubs_list)}] {hub_name} | Tab: {status_tab}")
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
                        time.sleep(2.5)
                        
                        # Quét DOM dự phòng ngày Today
                        rows = page.locator(".ant-table-row").all()
                        if rows:
                            for row in rows:
                                try:
                                    row_text = row.inner_text()
                                    if TODAY_STR in row_text:
                                        match_id = re.search(r'(266\d+[A-Z0-9]+)', row_text)
                                        if match_id and match_id.group(1) not in captured_ids:
                                            trip_code = match_id.group(1)
                                            driver_find = "Chưa gán tài xế"
                                            match_driver_code = re.search(r'(\d{5,})', row_text)
                                            if match_driver_code:
                                                lines = [l.strip() for l in row_text.split("\n") if l.strip()]
                                                for line in lines:
                                                    if match_driver_code.group(1) in line and "Người tạo" not in line:
                                                        driver_find = line
                                                        break
                                            
                                            mock_trip = {
                                                "id": trip_code,
                                                "trip_code": trip_code,
                                                "hub_name": hub_name,
                                                "hub_id": hub_id,
                                                "created_at": f"{TODAY_STR} - UI",
                                                "driver_name": driver_find,
                                                "total_statistics": "0-0-0",
                                                "trip_status_group": "Đang chạy" if status_tab == "ON_TRIP" else "Kết thúc"
                                            }
                                            stats_match = re.search(r'(\d+-\d+-\d+)', row_text)
                                            if stats_match: mock_trip["total_statistics"] = stats_match.group(1)
                                            
                                            all_trips.append(mock_trip)
                                            captured_ids.add(trip_code)
                                except: pass
                    except Exception as e:
                        print(f"⚠️ Lỗi quét chuyến đi tại {hub_name}: {e}")

            # ================= GIAI ĐOẠN 2: QUÉT BÁO CÁO TỒN ĐỌNG =================
            print("\n--------------------------------------------------")
            print("📊 BẮT ĐẦU CHUYỂN QUA GIAI ĐOẠN CÀO SỐ LIỆU TỒN ĐỌNG...")
            print("--------------------------------------------------")
            
            page.goto("https://nhanh.ghn.vn/lastmile/report/backlog-lgt")
            page.wait_for_load_state("networkidle")
            time.sleep(1.5)

            for index, hub in enumerate(hubs_list):
                hub_id = hub.get("locationId")
                hub_name = hub.get("locationName")
                if not hub_id: continue
                
                print(f"🔍 [Tồn đọng {index+1}/{len(hubs_list)}] Đang lọc lấy tồn đọng bưu cục: {hub_name}")
                
                try:
                    page.wait_for_selector(".ant-select-selection-overflow", timeout=6000)
                    
                    clear_buttons = page.locator(".ant-select-selection-item-remove").all()
                    for btn in clear_buttons:
                        try: btn.click()
                        except: pass
                    time.sleep(0.3)
                    
                    page.locator(".ant-select-selection-overflow").first.click()
                    time.sleep(0.3)
                    
                    search_backlog = page.locator("input.ant-select-selection-search-input").first
                    search_backlog.fill(str(hub_id))
                    time.sleep(0.5)
                    search_backlog.press("Enter")
                    
                    page.locator("button:has-text('Cập nhật dữ liệu')").click()
                    time.sleep(3.0)
                    
                    table_text = page.locator(".ant-table-tbody").inner_text()
                    
                    giao_ton = 0
                    uu_tien_ton = 0
                    tra_ton = 0
                    
                    giao_match = re.search(r'Giao\s*\(\s*(\d+)\s*\)', table_text)
                    uu_tien_match = re.search(r'Ưu\s*tiên\s*giao\s*\(\s*(\d+)\s*\)', table_text)
                    tra_match = re.search(r'Trả\s*\(\s*(\d+)\s*\)', table_text)
                    
                    if giao_match: giao_ton = int(giao_match.group(1))
                    if uu_tien_match: uu_tien_ton = int(uu_tien_match.group(1))
                    if tra_match: tra_ton = int(tra_match.group(1))
                    
                    tong_ton_goc = giao_ton + uu_tien_ton + tra_ton
                    print(f"   📊 Kết quả cào: Giao: {giao_ton} | Ưu tiên: {uu_tien_ton} | Trả: {tra_ton} => Tổng Tồn: {tong_ton_goc}")
                    
                    backlog_data[str(hub_id)] = {
                        "Giao_Ton": giao_ton,
                        "Uu_Tien_Ton": uu_tien_ton,
                        "Tra_Ton": tra_ton,
                        "Tong_Ton_Goc": tong_ton_goc
                    }
                except Exception as ex:
                    print(f"   ⚠️ Lỗi bảng tồn đọng bưu cục {hub_name}: {ex}")
                    backlog_data[str(hub_id)] = {"Giao_Ton": 0, "Uu_Tien_Ton": 0, "Tra_Ton": 0, "Tong_Ton_Goc": 0}

            # Lưu lại tệp tin JSON cấu trúc mới
            final_output = {
                "date_collected": TODAY_STR,
                "trips": all_trips,
                "backlogs": backlog_data
            }
            
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(final_output, f, ensure_ascii=False, indent=4)
                
            print(f"\n✅ ĐÃ HOÀN THÀNH TẤT CẢ! Dữ liệu ngày {TODAY_STR} đã ghi nhận thành công.")
            
        except Exception as main_e:
            print(f"❌ Lỗi kết nối: {main_e}")

if __name__ == "__main__":
    run_click_and_intercept()