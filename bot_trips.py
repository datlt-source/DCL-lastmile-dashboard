import json, os, time, re
from datetime import datetime
from playwright.sync_api import sync_playwright

OUTPUT_FILE = "all_region_trips.json"
TARGET_DATE = datetime.now().strftime("%d/%m/%Y")
USER_DATA_DIR = os.getenv("GHN_PROFILE_DIR", "./bot_profile_test")
GHN_BASE_URL = os.getenv("GHN_BASE_URL", "https://nhanh.ghn.vn")

# Nếu bạn có web test riêng, chỉ cần export GHN_BASE_URL trước khi chạy
# ví dụ: export GHN_BASE_URL=https://test.nhanh.ghn.vn

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

    # Reset nếu là ngày mới (không cộng dồn dữ liệu qua các ngày)
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if existing_data and TARGET_DATE not in existing_data[0].get("created_at", ""):
                    print(f"📅 Sang ngày mới, reset dữ liệu...")
                else:
                    # Load dữ liệu hiện tại (cùng ngày) và đánh dấu id đã ghi
                    all_trips = existing_data
                    for t in all_trips:
                        t_id = t.get("id") or t.get("trip_code")
                        if t_id:
                            captured_ids.add(t_id)
        except Exception:
            all_trips = []
            captured_ids = set()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False, channel="chrome")
        page = context.pages[0]
        page.set_default_timeout(90000)
        
        for status_tab in ["ON_TRIP", "FINISHED"]:
            print(f"\n--- ĐANG QUÉT TAB: {status_tab} ---")
            page.goto(f"{GHN_BASE_URL}/lastmile/trip-list?status={status_tab}", wait_until="networkidle")
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(1200)

            # CẤU HÌNH 50 DÒNG AN TOÀN
            try:
                if page.locator('.ant-pagination-options-size-changer .ant-select-selector').count() > 0:
                    page.locator('.ant-pagination-options-size-changer .ant-select-selector').first.click()
                    page.wait_for_selector(".ant-select-item-option-content:has-text('50')", timeout=5000)
                    page.locator(".ant-select-item-option-content:has-text('50')").first.click()
                    page.wait_for_timeout(2000)
                else:
                    print("⚠️ Không tìm thấy popup chọn số dòng, bỏ qua bước đổi 50.")
            except Exception as e:
                print(f"⚠️ Không đổi được số dòng (có thể đã chọn 50 rồi): {e}")
            
            for index, hub in enumerate(hubs_list):
                hub_id = str(hub.get("locationId") or hub.get("id"))
                hub_name = hub.get("locationName") or hub.get("name") or "Unknown"
                
                print(f"🔄 [{index+1}/{len(hubs_list)}] Duyệt: {hub_name}")
                
                try:
                    # 1. Nhập bưu cục
                    remove_btns = page.locator(".ant-select-selection-item-remove")
                    for i in range(remove_btns.count()):
                        try:
                            remove_btns.nth(i).click()
                            time.sleep(0.3)
                        except:
                            pass

                    page.wait_for_selector(".ant-select-selector", timeout=10000)
                    page.locator(".ant-select-selector").first.click()
                    page.wait_for_selector("input.ant-select-selection-search-input", timeout=5000)
                    search = page.locator("input.ant-select-selection-search-input").first
                    search.fill(hub_id)
                    page.wait_for_timeout(1200)

                    option = page.locator(f".ant-select-item-option-content:has-text('{hub_id}')")
                    if option.count() > 0:
                        option.first.click()
                        page.wait_for_timeout(2000)
                    else:
                        search.press("Enter")
                        page.wait_for_timeout(2000)
                    
                    # 2. LÀM SẠCH DỮ LIỆU CŨ CỦA BƯU CỤC ĐANG QUÉT
                    # Giúp Dashboard cập nhật đúng số lượng thực tế tại thời điểm quét
                    # Đồng thời loại bỏ id cũ khỏi captured_ids để cho phép cập nhật lại
                    to_remove = [t for t in all_trips if t.get('hub_name') == hub_name]
                    for t in to_remove:
                        tid = t.get('id') or t.get('trip_code')
                        if tid and tid in captured_ids:
                            captured_ids.discard(tid)
                    all_trips = [trip for trip in all_trips if trip.get('hub_name') != hub_name]

                    # 3. QUÉT DỮ LIỆU TRONG BẢNG (CHỈ LẤY CHUYẾN CÓ NGÀY HÔM NAY)
                    try:
                        page.wait_for_selector(".ant-table-tbody .ant-table-row", timeout=15000)
                    except:
                        pass
                    page.wait_for_timeout(1000)

                    rows = page.locator(".ant-table-tbody .ant-table-row").all()
                    if not rows:
                        print(f"   ⚠️ Không tìm thấy dòng dữ liệu cho bưu cục {hub_name}")
                    for row in rows:
                        try:
                            text = row.inner_text()
                        except:
                            continue

                        # Chỉ lấy chuyến có ngày hôm nay (trong giao diện)
                        if TARGET_DATE not in text:
                            continue

                        match = re.search(r'(266\d+[A-Z0-9]+)', text)
                        if not match:
                            # fallback: tìm bất kỳ mã bắt đầu bằng 2 và chứa chữ số/hoa
                            match = re.search(r'(2\d{6,}[A-Z0-9]+)', text)

                        if match:
                            trip_code = match.group(1)
                            if trip_code in captured_ids:
                                continue
                            stats_match = re.search(r'(\d+-\d+-\d+)', text)
                            all_trips.append({
                                "id": trip_code,
                                "hub_name": hub_name,
                                "created_at": TARGET_DATE,
                                "delivery_return_sum": calculate_trip_delivery_return(stats_match.group(1) if stats_match else "0-0-0"),
                                "trip_status_group": "Đang chạy" if status_tab == "ON_TRIP" else "Kết thúc"
                            })
                            captured_ids.add(trip_code)
                
                except Exception as e:
                    print(f"❌ Lỗi tại {hub_name}: {e}")
                    page.reload()
                    page.wait_for_load_state("networkidle")

        # Lưu kết quả
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_trips, f, ensure_ascii=False, indent=4)
            
        context.close()
        print(f"\n✅ HOÀN THÀNH! Tổng cộng đã ghi nhận: {len(all_trips)} chuyến.")

if __name__ == "__main__":
    run_isolated_trips()