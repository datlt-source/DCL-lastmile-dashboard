import streamlit as st
import json
import os
import pandas as pd
import re

# Cấu hình trang
st.set_page_config(page_title="GHN Lastmile Analytics", page_icon="📊", layout="wide")

# CSS custom
st.markdown("""
    <style>
    .kpi-card-container { display: flex; justify-content: space-between; gap: 15px; margin-bottom: 25px; }
    .kpi-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: #ffffff; padding: 20px; border-radius: 12px; flex: 1; text-align: center; border-left: 5px solid #38bdf8; }
    .kpi-card.backlog { border-left-color: #ef4444; }
    .kpi-card.trips { border-left-color: #22c55e; }
    .kpi-title { font-size: 14px; text-transform: uppercase; color: #94a3b8; font-weight: 600; }
    .kpi-value { font-size: 28px; font-weight: 700; margin-top: 5px; color: #f8fafc; }
    .section-header { background-color: #1e1b4b; color: #e0e7ff; padding: 10px 15px; border-radius: 6px; font-weight: bold; margin: 15px 0; font-size: 16px; }
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

# Giao diện chính
st.markdown("<h2 style='text-align: center; color: #f97316;'>📊 HỆ THỐNG ĐIỀU PHỐI GHN</h2>", unsafe_allow_html=True)
df = load_data()

if df is not None:
    st.markdown("<div class='section-header'>📌 TỔNG QUAN VẬN HÀNH</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].markdown(f"<div class='kpi-card'><div class='kpi-title'>🏢 Tổng Bưu Cục</div><div class='kpi-value'>{len(df)}</div></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='kpi-card backlog'><div class='kpi-title'>📦 Tồn Đọng</div><div class='kpi-value'>{df['Tồn đọng (Kho)'].sum():,}</div></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='kpi-card trips'><div class='kpi-title'>🚚 Chuyến Xe</div><div class='kpi-value'>{df['Số chuyến đi'].sum()}</div></div>", unsafe_allow_html=True)
    cols[3].markdown(f"<div class='kpi-card'><div class='kpi-title'>✨ Tổng Sản Lượng</div><div class='kpi-value'>{df['Sản lượng (Xe)'].sum():,}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>📋 CHI TIẾT ĐIỀU PHỐI</div>", unsafe_allow_html=True)
    
    def style_row(row):
        color = "#ef4444" if row["Trạng thái cảnh báo"] == "🚨 QUÁ TẢI" else ("#f59e0b" if row["Trạng thái cảnh báo"] == "⚠️ ÁP LỰC" else "#22c55e")
        return [f'background-color: rgba(255,255,255,0.05); color: {color}; font-weight: bold;'] * len(row)
        
    st.dataframe(df.style.apply(style_row, axis=1), use_container_width=True)
    
    if st.button("🔄 Cập nhật/Làm mới dữ liệu tức thì"):
        st.rerun()
else:
    st.error("❌ Không tìm thấy dữ liệu!")