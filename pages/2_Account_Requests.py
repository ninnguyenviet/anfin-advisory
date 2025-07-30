# pages/2_Account_Requests.py

import streamlit as st
import pandas as pd
from services.bigquery_client import load_account_requests
from components.leaderboard_table import render_account_table, render_account_details

st.set_page_config(
    page_title="Dashboard Quản lý Account Requests",
    layout="wide"
)

# Sidebar filters
st.sidebar.title("🔎 Bộ lọc")

status_options = ["Tất cả", "NEW", "APPROVED", "CANCELLED"]
status_selected = st.sidebar.selectbox("Trạng thái", status_options)

source_options = ["Tất cả", "AnfinXMobile", "AnfinXWebsite"]
source_selected = st.sidebar.selectbox("Source", source_options)

search_text = st.sidebar.text_input("Tìm kiếm (Tên, SĐT, User ID)")

# Load data
df = load_account_requests()

# Làm sạch index để tránh lỗi reindex
df = df.reset_index(drop=True)
df.index = range(len(df))

# Đảm bảo các cột cần thiết tồn tại
required_cols = ["status", "source", "display_name", "phone_number", "user_id"]
for col in required_cols:
    if col not in df.columns:
        df[col] = None

# Áp dụng bộ lọc
if status_selected != "Tất cả":
    df = df[df["status"] == status_selected]

if source_selected != "Tất cả":
    df = df[df["source"] == source_selected]

if search_text:
    df = df[
        df["display_name"].fillna("").str.contains(search_text, case=False) |
        df["phone_number"].fillna("").str.contains(search_text) |
        df["user_id"].fillna("").str.contains(search_text)
    ]

# Reset lại index sau khi lọc
df = df.reset_index(drop=True)
df.index = range(len(df))

# Render tiêu đề trang
st.markdown("""
    <h1 style='text-align: center; margin-bottom: 20px;'>Dashboard Quản lý Account Requests</h1>
""", unsafe_allow_html=True)

# ✅ Thống kê số lượng trạng thái (AN TOÀN tuyệt đối)
total = len(df)

if not df.empty and "status" in df.columns:
    status_counts = df["status"].value_counts()
    new_count = status_counts.get("NEW", 0)
    approved_count = status_counts.get("APPROVED", 0)
    cancelled_count = status_counts.get("CANCELLED", 0)
else:
    new_count = approved_count = cancelled_count = 0

# Hiển thị metric
col_space, col1, col2, col3, col4, col_space2 = st.columns([4.5, 3, 3, 3, 3, 3])
col1.metric("🧑‍💻 Tổng số Account", total)
col2.metric("🟡 Chờ duyệt (NEW)", new_count)
col3.metric("✅ Đã duyệt (APPROVED)", approved_count)
col4.metric("❌ Bị từ chối (CANCELLED)", cancelled_count)

st.markdown("---")

# Hiển thị bảng
render_account_table(df)

st.markdown("---")

# Hiển thị chi tiết account (nếu có logic cho NEW)
render_account_details(df)
