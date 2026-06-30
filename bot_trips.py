import json, os, time, re
from datetime import datetime
from playwright.sync_api import sync_playwright

OUTPUT_FILE = "all_region_trips.json"
TARGET_DATE = datetime.now().strftime("%d/%m/%Y")

def calculate_trip_delivery_return(stats_str):
    match = re.search(r'(\d+)-(\d+)-(\d+)', str(stats_str))
    return int(match.group(2)) + int(match.group(3)) if match else 0

def run_isolated_trips():
    if not os.path.exists("all_buu_cuc.json"):
        print("❌ Không tìm thấy file all_buu_cuc.json!")
        return
        
    with open("all_buu_cuc.json", "r", encoding="utf-8") as f:
        hubs_list = json.load(f)

    all_trips = []
    captured_ids = set()

    # Reset nếu là ngày mới
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if existing_data and TARGET_DATE not in existing_data[0].get("created_at", ""):
                    print(f"📅 Sang ngày mới, reset dữ liệu...")
                else:
                    all_trips = existing_data
                    for t in all_trips:
                        t_id = t.get("id")
                        if t_id: captured_ids.add(t_id)
        except: all_trips = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir="./bot_profile", headless=False, channel="chrome")
        page = context.pages[0]
        page.set_default_timeout(60000) # Tăng timeout để tránh lỗi crash do mạng chậm
        
        for status_tab in ["ON_TRIP", "FINISHED"]:
            print(f"\n--- ĐANG QUÉT TAB: {status_tab} ---")
            page.goto(f"https://nhanh.ghn.vn/lastmile/trip-list?status={status_tab}", wait_until="networkidle")
            
            # Cấu hình 50 dòng
            try:
                page.locator(".ant-pagination-options-size-changer").first.click()
                page.locator(".ant-select-item-option-content:has-text('50')").first.click()
                time.sleep(2.0)
            except: pass
            
            for index, hub in enumerate(hubs_list):
                hub_id = str(hub.get("locationId") or hub.get("id"))
                hub_name = hub.get("locationName") or hub.get("name") or "Unknown"
                
                print(f"🔄 [{index+1}/{len(hubs_list)}] Duyệt: {hub_name}")
                
                try:
                    # 1. Kiểm tra và xóa bưu cục cũ (tránh lỗi Timeout)
                    remove_btns = page.locator(".ant-select-selection-item-remove")
                    if remove_btns.count() > 0:
                        remove_btns.first.click()
                        time.sleep(0.5)

                    # 2. Nhập bưu cục mới
                    page.locator(".ant-select-selector").first.click()
                    search = page.locator("input.ant-select-selection-search-input").first
                    search.fill(hub_id)
                    time.sleep(0.5)
                    search.press("Enter")
                    time.sleep(2.5)
                    
                    # 3. Quét dữ liệu
                    rows = page.locator(".ant-table-row").all()
                    for row in rows:
                        text = row.inner_text()
                        if TARGET_DATE in text:
                            match = re.search(r'(266\d+[A-Z0-9]+)', text)
                            if match and match.group(1) not in captured_ids:
                                trip_code = match.group(1)
                                stats_match = re.search(r'(\d+-\d+-\d+)', text)
                                all_trips.append({
                                    "id": trip_code, "hub_name": hub_name,
                                    "created_at": TARGET_DATE,
                                    "delivery_return_sum": calculate_trip_delivery_return(stats_match.group(1) if stats_match else "0-0-0"),
                                    "trip_status_group": "Đang chạy" if status_tab == "ON_TRIP" else "Kết thúc"
                                })
                                captured_ids.add(trip_code)
                except Exception as e:
                    print(f"❌ Lỗi tại {hub_name}: {e}")
                    page.reload() # Reload an toàn nếu gặp lỗi mạng
                    page.wait_for_load_state("networkidle")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_trips, f, ensure_ascii=False, indent=4)
        context.close()
        print(f"\n✅ HOÀN THÀNH! Tổng cộng: {len(all_trips)} chuyến.")

if __name__ == "__main__":
    run_isolated_trips()