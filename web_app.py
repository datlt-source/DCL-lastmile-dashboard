import streamlit as st
import json
import os
import pandas as pd

# 1. Cấu hình trang hiển thị rộng rãi, chuyên nghiệp
st.set_page_config(page_title="GHN Lastmile Analytics", page_icon="📊", layout="wide")

# CSS custom nâng cấp UI giống hệ thống Dashboard chuyên nghiệp
st.markdown("""
    <style>
    /* CSS cho các thẻ KPI phía trên */
    .kpi-card-container {
        display: flex;
        justify-content: space-between;
        gap: 15px;
        margin-bottom: 25px;
    }
    .kpi-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-left: 5px solid #38bdf8;
        flex: 1;
        text-align: center;
    }
    .kpi-card.backlog { border-left-color: #ef4444; }
    .kpi-card.trips { border-left-color: #22c55e; }
    
    .kpi-title { font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; font-weight: 600; }
    .kpi-value { font-size: 28px; font-weight: 700; margin-top: 5px; color: #f8fafc; }
    
    /* Tối ưu thanh tiêu đề phân khu */
    .section-header {
        background-color: #1e1b4b;
        color: #e0e7ff;
        padding: 10px 15px;
        border-radius: 6px;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 15px;
        font-size: 16px;
    }
    </style>
""", unsafe_allow_html=True)

def clean_and_normalize(text):
    if not text: return ""
    return str(text).strip().lower().replace("(", "").replace(")", "").replace("-", "")

def load_data():
    backlog_file = "final_backlog_data.json"
    trips_file = "all_region_trips.json"
    
    if not os.path.exists(backlog_file) or not os.path.exists(trips_file):
        return None

    with open(backlog_file, "r", encoding="utf-8") as f:
        backlog_data = json.load(f)
    with open(trips_file, "r", encoding="utf-8") as f:
        trips_list = json.load(f)

    trip_counts = {}
    trip_productions = {} 
    
    for trip in trips_list:
        h_name = trip.get("hub_name") or trip.get("locationName") or ""
        if h_name:
            clean_trip_hub = clean_and_normalize(h_name)
            trip_counts[clean_trip_hub] = trip_counts.get(clean_trip_hub, 0) + 1
            
            prod = trip.get("delivery_return_sum", 0)
            if prod == 0 and "total_statistics" in trip:
                import re
                match = re.search(r'(\d+)-(\d+)-(\d+)', str(trip["total_statistics"]))
                if match:
                    try: prod = int(match.group(2)) + int(match.group(3))
                    except: prod = 0
            trip_productions[clean_trip_hub] = trip_productions.get(clean_trip_hub, 0) + prod

    summary = []
    for hub_name, backlog_info in backlog_data.items():
        total_backlog = backlog_info.get("total_sum", 0) if isinstance(backlog_info, dict) else 0
        clean_target_hub = clean_and_normalize(hub_name)
        total_trips = 0
        total_trip_production = 0 
        
        for trip_hub_key, count in trip_counts.items():
            if clean_target_hub in trip_hub_key or trip_hub_key in clean_target_hub:
                total_trips = count
                total_trip_production = trip_productions.get(trip_hub_key, 0)
                break
        
        avg_prod_per_trip = round(total_trip_production / total_trips, 1) if total_trips > 0 else 0
        backlog_ratio = (total_backlog / total_trip_production) if total_trip_production > 0 else 0
        
        if backlog_ratio >= 0.50:
            alert_status = "🚨 QUÁ TẢI"
        elif backlog_ratio >= 0.30:
            alert_status = "⚠️ ÁP LỰC"
        else:
            alert_status = "✅ AN TOÀN"
            
        summary.append({
            "Bưu cục": hub_name,
            "Tồn đọng (Kho)": total_backlog,
            "Số chuyến đi": total_trips,
            "Sản lượng (Xe)": total_trip_production,
            "Sản lượng/Chuyến": avg_prod_per_trip,
            "Trạng thái cảnh báo": alert_status
        })
    return pd.DataFrame(summary)

# --- THIẾT KẾ GIAO DIỆN CHÍNH ---
st.markdown("<h2 style='text-align: center; color: #f97316; margin-bottom: 20px;'>📊 HỆ THỐNG THEO DÕI & ĐIỀU PHỐI LASTMILE GHN</h2>", unsafe_allow_html=True)

df = load_data()

if df is None:
    st.error("❌ Không tìm thấy dữ liệu! Hãy chạy bot cào dữ liệu trước để sinh file json.")
else:
    # 1. Khu vực thẻ KPI mẫu mã đẹp (Phần Giao Thường / Tổng quan)
    st.markdown("<div class='section-header'>📌 TỔNG QUAN VẬN HÀNH TRONG NGÀY</div>", unsafe_allow_html=True)
    
    total_hubs = len(df)
    total_backlog_all = df["Tồn đọng (Kho)"].sum()
    total_trips_all = df["Số chuyến đi"].sum()
    total_prod_all = df["Sản lượng (Xe)"].sum()
    
    st.markdown(f"""
        <div class='kpi-card-container'>
            <div class='kpi-card'>
                <div class='kpi-title'>🏢 Tổng Bưu Cục Quét</div>
                <div class='kpi-value'>{total_hubs}</div>
            </div>
            <div class='kpi-card backlog'>
                <div class='kpi-title'>📦 Tổng Đơn Tồn Đọng</div>
                <div class='kpi-value'>{total_backlog_all:,} đơn</div>
            </div>
            <div class='kpi-card trips'>
                <div class='kpi-title'>🚚 Tổng Chuyến Xe Chạy</div>
                <div class='kpi-value'>{total_trips_all} chuyến</div>
            </div>
            <div class='kpi-card'>
                <div class='kpi-title'>✨ Tổng Sản Lượng Đã Giao</div>
                <div class='kpi-value'>{total_prod_all:,} đơn</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. Khu vực Bảng dữ liệu chi tiết có định dạng màu sắc (Datatable)
    st.markdown("<div class='section-header'>📋 CHI TIẾT ĐIỀU PHỐI BƯU CỤC</div>", unsafe_allow_html=True)
    
    # Hàm xử lý đổ màu highlight từng dòng dựa trên Trạng thái cảnh báo
    def style_dataframe(row):
        styles = [''] * len(row)
        status = row['Trạng thái cảnh báo']
        if status == "🚨 QUÁ TẢI":
            # Đỏ nhạt cho dòng quá tải
            styles = ['background-color: rgba(239, 68, 68, 0.15); color: #ef4444; font-weight: 500;'] * len(row)
        elif status == "⚠️ ÁP LỰC":
            # Vàng nhạt cho dòng áp lực
            styles = ['background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; font-weight: 500;'] * len(row)
        else:
            # Xanh lá cho bưu cục an toàn
            styles = ['background-color: rgba(34, 197, 94, 0.15); color: #22c55e; font-weight: 500;'] * len(row)
        return styles
        
    styled_df = df.style.apply(style_dataframe, axis=1)
    
    # Render bảng tương tác độ rộng full màn hình
    st.dataframe(styled_df, use_container_width=True, height=250)
    
    # Nút bấm thủ công để reload nhanh dữ liệu
    if st.button("🔄 Cập nhật/Làm mới dữ liệu tức thì"):
        st.rerun()