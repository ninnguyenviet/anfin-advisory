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

# Apply filters
if status_selected != "Tất cả":
    df = df[df.get("status") == status_selected]

if source_selected != "Tất cả":
    df = df[df.get("source") == source_selected]

if search_text:
    df = df[
        df.get("display_name", pd.Series(dtype=str)).fillna("").str.contains(search_text, case=False) |
        df.get("phone_number", pd.Series(dtype=str)).fillna("").str.contains(search_text) |
        df.get("user_id", pd.Series(dtype=str)).fillna("").str.contains(search_text)
    ]

# Render Title
st.markdown("""
    <h1 style='text-align: center; margin-bottom: 20px;'>Dashboard Quản lý Account Requests</h1>
""", unsafe_allow_html=True)

# ✅ Metrics cards
total = len(df)
new_count = (df.get("status") == "NEW").sum()
approved_count = (df.get("status") == "APPROVED").sum()
cancelled_count = (df.get("status") == "CANCELLED").sum()

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
render_account_details(df[df.get("status") == "NEW"])