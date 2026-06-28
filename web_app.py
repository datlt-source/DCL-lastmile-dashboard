import streamlit as st
import json
import os
import pandas as pd
import re
from datetime import datetime

# Cấu hình trang
st.set_page_config(page_title="GHN Lastmile Analytics", page_icon="📊", layout="wide")

# CSS cải tiến
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; color: #f97316; }
    .update-time { color: #94a3b8; font-style: italic; margin-bottom: 20px; }
    .logic-box { background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid #38bdf8; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

def load_data():
    if not os.path.exists("final_backlog_data.json") or not os.path.exists("all_region_trips.json"):
        return None, None
    
    mtime = os.path.getmtime("final_backlog_data.json")
    update_time = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M:%S')
    
    with open("final_backlog_data.json", "r", encoding="utf-8") as f:
        backlog_data = json.load(f)
    with open("all_region_trips.json", "r", encoding="utf-8") as f:
        trips_list = json.load(f)

    trip_counts, trip_productions = {}, {}
    for trip in trips_list:
        h_name = trip.get("hub_name") or trip.get("locationName") or ""
        if h_name:
            clean_name = h_name.strip().lower()
            trip_counts[clean_name] = trip_counts.get(clean_name, 0) + 1
            prod = trip.get("delivery_return_sum", 0)
            if prod == 0 and "total_statistics" in trip:
                match = re.search(r'(\d+)-(\d+)-(\d+)', str(trip["total_statistics"]))
                if match: prod = int(match.group(2)) + int(match.group(3))
            trip_productions[clean_name] = trip_productions.get(clean_name, 0) + prod

    summary = []
    for hub, count in trip_counts.items():
        prod = trip_productions.get(hub, 0)
        backlog = 0
        for b_hub, b_info in backlog_data.items():
            if b_hub.lower() in hub or hub in b_hub.lower():
                backlog = b_info.get("total_sum", 0)
                break
        
        # LOGIC MỚI CỦA BẠN
        ratio = (backlog / prod) if prod > 0 else 0
        if ratio > 2.0: status = "🚨 QUÁ TẢI"
        elif 1.6 <= ratio <= 2.0: status = "⚠️ CẢNH BÁO"
        else: status = "✅ BÌNH THƯỜNG"
            
        summary.append({
            "Bưu cục": hub.upper(),
            "Tồn đọng (Kho)": backlog,
            "Số chuyến đi": count,
            "Sản lượng (Xe)": prod,
            "Tỉ lệ": round(ratio, 2),
            "Trạng thái": status
        })
    return pd.DataFrame(summary), update_time

# Giao diện chính
st.title("📊 GHN Lastmile Dashboard")
df, last_update = load_data()

if df is not None:
    st.markdown(f"<p class='update-time'>🕒 Dữ liệu cập nhật gần nhất: {last_update}</p>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Bưu Cục", len(df))
    c2.metric("Tổng Tồn Đọng", f"{df['Tồn đọng (Kho)'].sum():,}")
    c3.metric("Tổng Chuyến Xe", df['Số chuyến đi'].sum())
    c4.metric("Tổng Sản Lượng", f"{df['Sản lượng (Xe)'].sum():,}")

    st.markdown("### ℹ️ Logic xác định trạng thái cảnh báo (Mới)")
    st.markdown("""
    <div class='logic-box'>
    Trạng thái được tính dựa trên <b>Tỉ lệ</b> (Tồn đọng / Sản lượng xe):
    <br>• <b>🚨 QUÁ TẢI</b>: Tỉ lệ > 2.0
    <br>• <b>⚠️ CẢNH BÁO</b>: 1.6 ≤ Tỉ lệ ≤ 2.0
    <br>• <b>✅ BÌNH THƯỜNG</b>: Tỉ lệ < 1.6
    </div>
    """, unsafe_allow_html=True)

    st.subheader("📋 Chi tiết điều phối bưu cục")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    if st.button("🔄 Làm mới dữ liệu"):
        st.rerun()
else:
    st.error("❌ Không tìm thấy dữ liệu!")