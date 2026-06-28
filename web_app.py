import streamlit as st
import pandas as pd
import json

# Cấu hình giao diện
st.set_page_config(layout="wide", page_title="Dashboard Tồn Đọng GHN")
st.title("📊 Bảng Chi Tiết Điều Phối Bưu Cục")

def load_data():
    try:
        with open("final_backlog_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Chuyển đổi từ dict sang danh sách để làm bảng
        records = []
        for hub_name, details in data.items():
            records.append({
                "Bưu cục": hub_name,
                "Tồn đọng (Kho)": details.get("total_sum", 0)
            })
        
        df = pd.DataFrame(records)
        return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame()

# Tải dữ liệu
df = load_data()

if not df.empty:
    # Hiển thị bảng full, không cắt bớt
    # Cấu trúc use_container_width giúp bảng trải rộng
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Tồn đọng (Kho)": st.column_config.NumberColumn(format="%d")
        }
    )
else:
    st.warning("Chưa có dữ liệu để hiển thị.")

# Nút cập nhật
if st.button("🔄 Cập nhật/Làm mới dữ liệu tức thì"):
    st.rerun()