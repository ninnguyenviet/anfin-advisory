import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from services.bigquery_client import load_account_request_data

st.set_page_config(
    page_title="Account Requests",
    layout="wide"
)

st.title("📥 Account Requests")

# --- Load data
with st.spinner("Loading data..."):
    df = load_account_request_data()

if df is None or df.empty:
    st.warning("⚠️ No data available.")
    st.stop()

# --- Kiểm tra cột bắt buộc
required_cols = ["status", "created_at", "full_name", "group_name", "note", "id"]
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    st.error(f"Missing columns in data: {missing_cols}")
    st.stop()

# --- Tiền xử lý dữ liệu
df = df.drop_duplicates(subset="id")
df["created_at"] = pd.to_datetime(df["created_at"])

# --- Lọc theo thời gian
today = datetime.now()
start_time = today.replace(hour=0, minute=0, second=0, microsecond=0)
last_24h = today - timedelta(hours=24)

mask_new = (df["status"] == "new") & (df["created_at"] >= start_time)
mask_processed = df["status"] != "new"

new_requests = df[mask_new]
processed_requests = df[mask_processed]

# --- Thống kê
st.subheader("📊 Tổng quan")

col1, col2 = st.columns(2)
col1.metric("Yêu cầu mới hôm nay", len(new_requests))
col2.metric("Yêu cầu đã xử lý", len(processed_requests))

# --- Biểu đồ trạng thái
if "status" in df.columns and df["status"].ndim == 1:
    status_counts = df["status"].value_counts()
    st.bar_chart(status_counts)
else:
    st.warning("Không thể vẽ biểu đồ trạng thái: dữ liệu không hợp lệ.")

# --- Hiển thị bảng yêu cầu mới
st.subheader("🆕 Yêu cầu mới hôm nay")
if not new_requests.empty:
    st.dataframe(new_requests[["created_at", "full_name", "group_name", "note"]].sort_values("created_at", ascending=False), use_container_width=True)
else:
    st.info("Không có yêu cầu mới hôm nay.")

# --- Hiển thị bảng yêu cầu đã xử lý
st.subheader("✅ Yêu cầu đã xử lý")
if not processed_requests.empty:
    st.dataframe(processed_requests[["created_at", "full_name", "group_name", "status", "note"]].sort_values("created_at", ascending=False), use_container_width=True)
else:
    st.info("Không có yêu cầu đã xử lý.")
