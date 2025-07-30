# pages/2_Account_Requests.py

import streamlit as st
import pandas as pd

# Import chuẩn từ service (bạn kiểm tra tên function chính xác)
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
try:
    df = load_account_requests()
except Exception as e:
    st.error(f"Lỗi khi load dữ liệu: {e}")
    st.stop()

# Kiểm tra cột cần thiết
required_cols = ["status", "source", "display_name", "phone_number", "user_id"]
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    st.warning(f"Dữ liệu thiếu các cột: {', '.join(missing_cols)}")
    st.stop()

# Apply filters
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

# Render Title
st.markdown("""
    <h1 style='text-align: center; margin-bottom: 20px;'>Dashboard Quản lý Account Requests</h1>
""", unsafe_allow_html=True)

# ✅ METRICS
if not df.empty:
    total = len(df)
    new_count = (df["status"] == "NEW").sum()
    approved_count = (df["status"] == "APPROVED").sum()
    cancelled_count = (df["status"] == "CANCELLED").sum()
else:
    total = new_count = approved_count = cancelled_count = 0

# Layout columns
col_space, col1, col2, col3, col4, col_space2 = st.columns([4.5, 3, 3, 3, 3, 3])

col1.metric("🧑‍💻 Tổng số Account", total)
col2.metric("🟡 Chờ duyệt (NEW)", new_count)
col3.metric("✅ Đã duyệt (APPROVED)", approved_count)
col4.metric("❌ Bị từ chối (CANCELLED)", cancelled_count)

st.markdown("---")

# Render Table
render_account_table(df)

st.markdown("---")

# Chỉ render detail với status NEW
df_new = df[df["status"] == "NEW"]
if not df_new.empty:
    render_account_details(df_new)
else:
    st.info("Không có account nào ở trạng thái NEW.")
