import streamlit as st
import json
import os
import pandas as pd
import re

# Cấu hình trang - Phải đặt đầu tiên
st.set_page_config(page_title="GHN Lastmile Analytics", page_icon="📊", layout="wide")

# CSS - Chỉ dùng để tạo style, không can thiệp chiều cao bảng để tránh lỗi
st.markdown("""
    <style>
    .kpi-card { background: #1e293b; color: #ffffff; padding: 20px; border-radius: 10px; text-align: center; }
    .section-header { color: #f97316; font-size: 20px; font-weight: bold; margin-top: 20px; }
    </style>
""", unsafe_allow_html=True)

def clean_and_normalize(text):
    if not text: return ""
    return str(text).strip().lower().replace("(", "").replace(")", "").replace("-", "")

def load_data():
    if not os.path.exists("final_backlog_data.json") or not os.path.exists("all_region_trips.json"):
        return None
    with open("final_backlog_data.json", "r", encoding="utf-8") as f:
        backlog_data = json.load(f)
    with open("all_region_trips.json", "r", encoding="utf-8") as f:
        trips_list = json.load(f)

    trip_counts, trip_productions = {}, {}
    for trip in trips_list:
        h_name = trip.get("hub_name") or trip.get("locationName") or ""
        if h_name:
            clean_trip_hub = clean_and_normalize(h_name)
            trip_counts[clean_trip_hub] = trip_counts.get(clean_trip_hub, 0) + 1
            prod = trip.get("delivery_return_sum", 0)
            if prod == 0 and "total_statistics" in trip:
                match = re.search(r'(\d+)-(\d+)-(\d+)', str(trip["total_statistics"]))
                if match: prod = int(match.group(2)) + int(match.group(3))
            trip_productions[clean_trip_hub] = trip_productions.get(clean_trip_hub, 0) + prod

    summary = []
    for trip_hub_key, count in trip_counts.items():
        total_trips = count
        total_trip_production = trip_productions.get(trip_hub_key, 0)
        total_backlog = 0
        original_hub_name = trip_hub_key.upper()
        for backlog_hub, backlog_info in backlog_data.items():
            clean_backlog_hub = clean_and_normalize(backlog_hub)
            if clean_backlog_hub in trip_hub_key or trip_hub_key in clean_backlog_hub:
                total_backlog = backlog_info.get("total_sum", 0) if isinstance(backlog_info, dict) else 0
                original_hub_name = backlog_hub
                break
        avg_prod_per_trip = int(round(total_trip_production / total_trips, 0)) if total_trips > 0 else 0
        backlog_ratio = (total_backlog / total_trip_production) if total_trip_production > 0 else 0
        alert_status = "🚨 QUÁ TẢI" if backlog_ratio >= 0.50 else ("⚠️ ÁP LỰC" if backlog_ratio >= 0.30 else "✅ AN TOÀN")
        summary.append({
            "Bưu cục": original_hub_name,
            "Tồn đọng (Kho)": total_backlog,
            "Số chuyến đi": total_trips,
            "Sản lượng (Xe)": total_trip_production,
            "Sản lượng/Chuyến": avg_prod_per_trip,
            "Trạng thái cảnh báo": alert_status
        })
    return pd.DataFrame(summary)

# Main layout
st.title("📊 HỆ THỐNG ĐIỀU PHỐI GHN")
df = load_data()

if df is not None:
    # KPI section
    cols = st.columns(4)
    cols[0].metric("Tổng Bưu Cục", len(df))
    cols[1].metric("Tồn Đọng", f"{df['Tồn đọng (Kho)'].sum():,}")
    cols[2].metric("Chuyến Xe", df['Số chuyến đi'].sum())
    cols[3].metric("Tổng Sản Lượng", f"{df['Sản lượng (Xe)'].sum():,}")

    st.markdown("<div class='section-header'>📋 CHI TIẾT ĐIỀU PHỐI BƯU CỤC</div>", unsafe_allow_html=True)
    
    # Bảng dữ liệu chuẩn (không truyền tham số height để tránh lỗi)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    if st.button("🔄 Cập nhật dữ liệu"):
        st.rerun()
else:
    st.error("❌ Dữ liệu không sẵn sàng!")