import json
import os
import pandas as pd

def clean_and_normalize(text):
    if not text:
        return ""
    return str(text).strip().lower().replace("(", "").replace(")", "").replace("-", "")

def generate_dashboard():
    backlog_file = "final_backlog_data.json"
    if not os.path.exists(backlog_file):
        print(f"❌ Không tìm thấy file dữ liệu tồn đọng: {backlog_file}.")
        return
        
    with open(backlog_file, "r", encoding="utf-8") as f:
        backlog_data = json.load(f)

    trips_file = "all_region_trips.json"
    if not os.path.exists(trips_file):
        print(f"⚠️ Không tìm thấy file '{trips_file}'.")
        trips_list = []
    else:
        with open(trips_file, "r", encoding="utf-8") as f:
            trips_list = json.load(f)

    # Gom nhóm số chuyến đi VÀ cộng dồn sản lượng giao trả của từng bưu cục
    trip_counts = {}
    trip_productions = {} 
    
    for trip in trips_list:
        h_name = trip.get("hub_name") or trip.get("locationName") or ""
        if h_name:
            clean_trip_hub = clean_and_normalize(h_name)
            
            # 1. Đếm số chuyến đi
            trip_counts[clean_trip_hub] = trip_counts.get(clean_trip_hub, 0) + 1
            
            # 2. Lấy sản lượng Giao + Trả
            prod = trip.get("delivery_return_sum", 0)
            if prod == 0 and "total_statistics" in trip:
                stats_str = trip["total_statistics"]
                import re
                match = re.search(r'(\d+)-(\d+)-(\d+)', str(stats_str))
                if match:
                    try:
                        prod = int(match.group(2)) + int(match.group(3))
                    except:
                        prod = 0
                        
            trip_productions[clean_trip_hub] = trip_productions.get(clean_trip_hub, 0) + prod

    summary = []
    for hub_name, backlog_info in backlog_data.items():
        total_backlog = backlog_info.get("total_sum", 0) if isinstance(backlog_info, dict) else 0
        
        clean_target_hub = clean_and_normalize(hub_name)
        total_trips = 0
        total_trip_production = 0 
        
        # So khớp bưu cục thông minh
        for trip_hub_key, count in trip_counts.items():
            if clean_target_hub in trip_hub_key or trip_hub_key in clean_target_hub:
                total_trips = count
                total_trip_production = trip_productions.get(trip_hub_key, 0)
                break
        
        # --- LOGIC TÍNH TOÁN CÁC CỘT MỚI ---
        # 1. Tính sản lượng trung bình trên mỗi chuyến
        avg_prod_per_trip = round(total_trip_production / total_trips, 1) if total_trips > 0 else 0
        
        # 2. Tính tỷ lệ áp lực kho để đưa ra cảnh báo chính xác
        backlog_ratio = (total_backlog / total_trip_production) if total_trip_production > 0 else 0
        
        if backlog_ratio >= 0.50:
            alert_status = "🚨 QUÁ TẢI (Dừng nhận đơn)"
        elif backlog_ratio >= 0.30:
            alert_status = "⚠️ Áp lực (Theo dõi sát)"
        else:
            alert_status = "✅ An toàn"
            
        summary.append({
            "Bưu cục": hub_name,
            "Tồn đọng (Tổng Giao/Ưu tiên/Trả)": total_backlog,
            "Số chuyến đi": total_trips,
            "Sản lượng chuyến đi (Giao+Trả)": total_trip_production,
            "Sản lượng/Chuyến": avg_prod_per_trip,
            "Cảnh báo tồn đọng": alert_status
        })

    df = pd.DataFrame(summary)
    print("\n=================================== BẢNG DASHBOARD PHÂN TÍCH ÁP LỰC KHO ===================================")
    print(df.to_string(index=False))
    print("===========================================================================================================")
    
    output_excel = "Final_Dashboard_GHN.xlsx"
    df.to_excel(output_excel, index=False)
    print(f"\n✅ Đã cập nhật ma trận cảnh báo! File Excel lưu tại: '{output_excel}'")

if __name__ == "__main__":
    generate_dashboard()