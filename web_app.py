import streamlit as st
import pandas as pd
import json

# Cấu hình trang Dashboard
st.set_page_config(layout="wide", page_title="Dashboard Tồn Đọng GHN")

st.title("📊 Bảng Chi Tiết Điều Phối Bưu Cục")

# 1. Tải và đọc dữ liệu từ file
try:
    with open("final_backlog_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Chuyển đổi dữ liệu từ JSON sang DataFrame
    records = []
    for hub_name, details in data.items():
        records.append({
            "Bưu cục": hub_name,
            "Tồn đọng (Kho)": details.get("total_sum", 0),
            # Thêm các cột khác nếu có trong cấu trúc dữ liệu của bạn
        })
    
    df = pd.DataFrame(records)

    # 2. Xử lý dữ liệu hiển thị (Làm tròn số và hiển thị toàn bộ)
    if 'Sản lượng/Chuyến' in df.columns:
        df['Sản lượng/Chuyến'] = df['Sản lượng/Chuyến'].round().astype(int)

    # 3. Hiển thị bảng (use_container_width=True giúp bảng rộng tràn màn hình)
    # Không dùng .head() để đảm bảo hiển thị hết 69 bưu cục
    st.dataframe(df, use_container_width=True, hide_index=True)

except FileNotFoundError:
    st.error("Không tìm thấy file 'final_backlog_data.json'. Hãy chạy bot cào dữ liệu trước.")
except Exception as e:
    st.error(f"Có lỗi xảy ra: {e}")

# Nút cập nhật thủ công (để trigger lại luồng dữ liệu)
if st.button("🔄 Cập nhật/Làm mới dữ liệu tức thì"):
    st.rerun()