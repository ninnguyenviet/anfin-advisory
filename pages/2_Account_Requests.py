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

# Reset index tuyệt đối để loại bỏ duplicate index
df = df.reset_index(drop=True)
df.index = range(len(df))

# Đảm bảo các cột cần thiết tồn tại
required_cols = ["status", "source", "display_name", "phone_number", "user_id"]
for col in required_cols:
    if col not in df.columns:
        df[col] = None

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

# Reset lại index sau khi lọc để đảm bảo an toàn khi lọc bằng mask
df = df.reset_index(drop=True)
df.index = range(len(df))

# Render Title
st.markdown("""
    <h1 style='text-align: center; margin-bottom: 20px;'>Dashboard Quản lý Account Requests</h1>
""", unsafe_allow_html=True)

# ✅ METRICS CARDS - xử lý an toàn 100%
total = len(df)

if not df.empty and "status" in df.columns:
    mask_new = (df["status"] == "NEW")
    mask_new.index = df.index
    new_count = len(df[mask_new])

    mask_approved = (df["status"] == "APPROVED")
    mask_approved.index = df.index
    approved_count = len(df[mask_approved])

    mask_cancelled = (df["status"] == "CANCELLED")
    mask_cancelled.index = df.index
    cancelled_count = len(df[mask_cancelled])
else:
    new_count = approved_count = cancelled_count = 0

# Tạo 3 cột cho Lots căn giữa
col_space, col1, col2, col3, col4, col_space2 = st.columns([4.5, 3, 3, 3, 3, 3])
col1.metric("🧑‍💻 Tổng số Account", total)
col2.metric("🟡 Chờ duyệt (NEW)", new_count)
col3.metric("✅ Đã duyệt (APPROVED)", approved_count)
col4.metric("❌ Bị từ chối (CANCELLED)", cancelled_count)

st.markdown("---")

# Render Table
render_account_table(df)

st.markdown("---")

# Render Detail Viewer chỉ show NEW
render_account_details(df)
