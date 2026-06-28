import streamlit as st
import json
import os
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="GHN Lastmile Analytics", page_icon="📊", layout="wide")

# CSS cải tiến
st.markdown("""
    <style>
    .metric-card { background: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid #f97316; }
    .update-time { color: #94a3b8; font-style: italic; font-size: 0.9em; }
    </style>
""", unsafe_allow_html=True)

def load_data():
    if not os.path.exists("final_backlog_data.json") or not os.path.exists("all_region_trips.json"):
        return None
    
    # Lấy thời gian sửa file mới nhất làm mốc cập nhật
    mtime = os.path.getmtime("final_backlog_data.json")
    update_time = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M:%S')
    
    with open("final_backlog_data.json", "r", encoding="utf-8") as f:
        backlog_data = json.load(f)
    with open("all_region_trips.json", "r", encoding="utf-8") as f:
        trips_list = json.load(f)

    # ... [Giữ nguyên logic xử lý dữ liệu như cũ] ...
    trip_counts, trip_productions = {}, {}
    for trip in trips_list:
        h_name = trip.get("hub_name") or trip.get("locationName") or ""
        if h_name:
            clean_trip_hub = h_name.strip().lower()
            trip_counts[clean_trip_hub] = trip_counts.get(clean_trip_hub, 0) + 1
            prod = trip.get("delivery_return_sum", 0)
            if prod == 0 and "total_statistics" in trip:
                match = re.search(r'(\d+)-(\d+)-(\d+)', str(trip["total_statistics"]))
                if match: prod = int(match.group(2)) + int(match.group(3))
            trip_productions[clean_trip_hub] = trip_productions.get(clean_trip_hub, 0) + prod

    summary = []
    for hub, count in trip_counts.items():
        prod = trip_productions.get(hub, 0)
        backlog = 0
        for b_hub, b_info in backlog_data.items():
            if b_hub.lower() in hub or hub in b_hub.lower():
                backlog = b_info.get("total_sum", 0)
                break
        
        # LOGIC CẢNH BÁO
        ratio = (backlog / prod) if prod > 0 else 0
        if ratio >= 0.50: status = "🚨 QUÁ TẢI"
        elif ratio >= 0.30: status = "⚠️ ÁP LỰC"
        else: status = "✅ AN TOÀN"
            
        summary.append({
            "Bưu cục": hub.upper(), "Tồn đọng": backlog, "Sản lượng": prod,
            "Trạng thái": status, "Tỉ lệ (%)": round(ratio * 100, 1)
        })
    return pd.DataFrame(summary), update_time

# Giao diện
st.title("📊 GHN Lastmile Dashboard")
df, last_update = load_data()

if df is not None:
    st.markdown(f"<p class='update-time'>🕒 Dữ liệu cập nhật gần nhất: {last_update}</p>", unsafe_allow_html=True)
    
    # Giải thích logic
    with st.expander("ℹ️ Logic xác định trạng thái cảnh báo"):
        st.write("""
        Hệ thống xác định trạng thái dựa trên **Tỉ lệ tồn đọng** (Tồn đọng / Sản lượng xe):
        - **🚨 QUÁ TẢI**: Tỉ lệ tồn đọng >= **50%**. Bưu cục đang bị ùn ứ đơn hàng nghiêm trọng.
        - **⚠️ ÁP LỰC**: Tỉ lệ tồn đọng từ **30% đến dưới 50%**. Bưu cục cần theo dõi kỹ để tránh quá tải.
        - **✅ AN TOÀN**: Tỉ lệ tồn đọng < **30%**. Vận hành ổn định.
        """)
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    if st.button("🔄 Làm mới"): st.rerun()