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

type_options = ["Tất cả", "CREATE", "UPDATE"]
type_selected = st.sidebar.selectbox("Type", type_options)

search_text = st.sidebar.text_input("Tìm kiếm (Tên, SĐT, User ID)")

# Load data
df = load_account_requests()

# Apply filters
if status_selected != "Tất cả":
    df = df[df["status"] == status_selected]

if type_selected != "Tất cả":
    df = df[df["type"] == type_selected]

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

# ✅ ADD METRICS CARDS
total = len(df)
new_count = len(df[df["status"] == "NEW"])
approved_count = len(df[df["status"] == "APPROVED"])
cancelled_count = len(df[df["status"] == "CANCELLED"])
# tạo 3 cột cho Lots căn giữa
col_space, col1, col2, col3, col4, col_space2 = st.columns([4.5, 3, 3, 3, 3, 3])

# col1, col2, col3, col4 = st.columns(4)
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
