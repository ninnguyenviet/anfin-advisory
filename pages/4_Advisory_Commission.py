# pages/4_Commission.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
from datetime import datetime, date
import pytz
import pandas.api.types as ptypes

from services.bigquery_client  import  load_advisory_dims,load_advisory_commission_data

st.set_page_config(page_title="Advisory Commission", page_icon="💸", layout="wide")
st.markdown("# 💸 Advisory Commission Dashboard")

# ---------- Helpers ----------
def fmt_money(val):
    if pd.isna(val): return "-"
    try: val = float(val)
    except Exception: return "-"
    a = abs(val)
    if a >= 1e9: return f"{val/1e9:,.2f} tỷ"
    if a >= 1e6: return f"{val/1e6:,.1f} triệu"
    if a >= 1e3: return f"{val/1e3:,.0f} nghìn"
    return f"{val:,.0f}"

# @st.cache_data(ttl=600)
def _load_dims_cached():
    return load_advisory_dims()

@st.cache_data(ttl=600)
def _load_data_cached(months, types, month_is_date):
    return load_advisory_commission_data(months=months, types=types, month_is_date=month_is_date)

# ---------- Build filters ----------
with st.spinner("Đang tải bộ lọc..."):
    dims = load_advisory_dims()

if dims.empty:
    st.info("Không có dữ liệu trong view.")
    st.stop()

# Nhận diện kiểu month (DATE hay STRING)
month_is_date = False
if "month" in dims.columns:
    if ptypes.is_datetime64_any_dtype(dims["month"]):
        month_is_date = True
    else:
        sample = dims["month"].dropna()
        if not sample.empty and isinstance(sample.iloc[0], (date, pd.Timestamp)):
            month_is_date = True

# Chuẩn hoá options month + mặc định = THÁNG HIỆN TẠI
if "month" in dims.columns:
    raw_month_vals = dims["month"].dropna().unique().tolist()
    if month_is_date:
        raw_month_vals = [(m.date() if isinstance(m, pd.Timestamp) else m) for m in raw_month_vals]
        month_labels = sorted({m.strftime("%Y-%m") for m in raw_month_vals})
        current_label = date.today().replace(day=1).strftime("%Y-%m")
        default_month_labels = [current_label] if current_label in month_labels else [month_labels[-1]]
        label_to_values = {}
        for m in raw_month_vals:
            lbl = m.strftime("%Y-%m")
            label_to_values.setdefault(lbl, []).append(m)
    else:
        raw_month_vals = [str(m) for m in raw_month_vals]
        month_labels = sorted(set(raw_month_vals))
        current_label = datetime.now().strftime("%Y-%m")
        default_month_labels = [current_label] if current_label in month_labels else [month_labels[-1]]
        label_to_values = {lbl: [lbl] for lbl in month_labels}
else:
    month_labels, default_month_labels, label_to_values = [], [], {}

# Options type — mặc định: ALL (chọn hết)
type_options = sorted(dims["type"].dropna().astype(str).unique()) if "type" in dims.columns else []
default_types = type_options.copy()  # ALL

st.markdown("### Bộ lọc")
c1, c2, c3 = st.columns([2, 2, 2])
with c1:
    selected_month_labels = st.multiselect("Chọn Month", options=month_labels, default=default_month_labels)
with c2:
    selected_types = st.multiselect("Chọn Type", options=type_options, default=default_types)
with c3:
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    st.caption(f"Hôm nay: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}")

# Chuẩn bị tham số query
selected_month_values = []
for lbl in selected_month_labels:
    selected_month_values.extend(label_to_values.get(lbl, []))

with st.spinner("Đang tải dữ liệu..."):
    df = load_advisory_commission_data(selected_month_values if selected_month_values else None,
                           selected_types if selected_types else None,
                           month_is_date if selected_month_values else None)

if df.empty:
    st.info("Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# ---------- Compute commissions ----------
df = df.copy()
for c in ["lot_standard", "lot", "transaction_fee", "actual_profit_VND", "total_lot_standard"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# commission theo rule
df["type"] = df.get("type", "").astype(str).str.lower()
df["commission_tkcv"]  = df["lot_standard"] * 150000
df["commission_tknlk"] = df["lot_standard"] * 5000
df["commission_total"] = df["commission_tkcv"] + df["commission_tknlk"]

# ---------- KPI cards ----------
num_investors  = df["investor_code"].nunique() if "investor_code" in df.columns else 0
num_cv         = df["tkcv"].nunique() if "tkcv" in df.columns else 0
num_nlk        = df["tknlk"].nunique() if "tknlk" in df.columns else 0
sum_lot_std    = float(df["lot_standard"].sum()) if "lot_standard" in df.columns else 0.0
sum_txn_fee    = float(df["transaction_fee"].sum()) if "transaction_fee" in df.columns else 0.0
sum_commission = float(df["commission_total"].sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Số Investor", num_investors)
k2.metric("Số Chuyên viên", num_cv)
k3.metric("Số Người liên kết", num_nlk)
k4.metric("Tổng Lot chuẩn", f"{sum_lot_std:,.2f}")
k5.metric("Tổng Phí giao dịch", fmt_money(sum_txn_fee))
k6.metric("Tổng Hoa hồng", fmt_money(sum_commission))

st.divider()

# ---------- Bảng 1: Chi tiết hoa hồng Chuyên viên (TKCV) ----------
st.markdown("## 👤 Chi tiết hoa hồng của Chuyên viên (TKCV)")
if {"tkcv", "tkcv_name"}.issubset(df.columns):
    cv_df = df[df["tkcv"].notna() & (df["tkcv"] != "")]
    grp_cols = ["tkcv", "tkcv_name", "tknlk", "tknlk_name"] + (["month"] if "month" in cv_df.columns else [])
    cv_sum_csv = cv_df.groupby(grp_cols, dropna=False).agg({
        "lot_standard": "sum",
        "commission_tkcv": "sum",
        "actual_profit_VND": "sum",
        **({"transaction_fee": "sum"} if "transaction_fee" in cv_df.columns else {}),
    }).reset_index().sort_values(by="lot_standard", ascending=False)

    cv_sum = cv_df.groupby(grp_cols, dropna=False).agg({
        "lot_standard": "sum",
        "commission_tkcv": "sum",
        "actual_profit_VND": "sum",
        **({"transaction_fee": "sum"} if "transaction_fee" in cv_df.columns else {}),
    }).reset_index().sort_values(by="lot_standard", ascending=False)
    if "transaction_fee" in cv_sum.columns:
        cv_sum["transaction_fee_fmt"] = cv_sum["transaction_fee"].apply(fmt_money)
    cv_sum["commission_fmt"] = cv_sum["commission_tkcv"].apply(fmt_money)
    cv_sum["actual_profit_VND_fmt"] = cv_sum["actual_profit_VND"].apply(fmt_money)

    cols = [c for c in ["month", "tkcv", "tkcv_name", "tknlk", "tknlk_name" , "lot_standard", "transaction_fee_fmt", "actual_profit_VND_fmt", "commission_fmt"] if c in cv_sum.columns]
    rename = {" month": "Month", "tkcv": "Mã TKCV", "tkcv_name": "Chuyên viên", "tknlk": "Mã TKNLK", "tknlk_name": "Người liên kết",
              "lot_standard": "Tổng Lot chuẩn", "transaction_fee_fmt": "Tổng Phí GD", "actual_profit_VND_fmt": "Lãi/lỗ thực tế",  "commission_fmt": "Hoa hồng TKCV"}
    st.dataframe(cv_sum[cols].rename(columns=rename), use_container_width=True, hide_index=True)
    st.download_button("Tải CSV - Hoa hồng Chuyên viên", data=cv_sum_csv.to_csv(index=False).encode("utf-8"),
                       file_name="commission_tkcv.csv", mime="text/csv")
else:
    st.caption("⚠️ Không thấy cột tkcv/tkcv_name trong dữ liệu.")

st.divider()

# ---------- Bảng 2: Chi tiết hoa hồng Người liên kết (TKNLK) ----------
st.markdown("## 🤝 Chi tiết hoa hồng của Người liên kết (TKNLK)")
if {"tknlk", "tknlk_name"}.issubset(df.columns):
    nlk_df = df[df["tknlk"].notna() & (df["tknlk"] != "")]
    grp_cols = ["tknlk", "tknlk_name"] + (["month"] if "month" in nlk_df.columns else [])
    nlk_sum_csv= nlk_df.groupby(grp_cols, dropna=False).agg({
        "lot_standard": "sum",
        "commission_tknlk": "sum",
        **({"transaction_fee": "sum"} if "transaction_fee" in nlk_df.columns else {}),
    }).reset_index().sort_values(by="lot_standard", ascending=False)
    nlk_sum = nlk_df.groupby(grp_cols, dropna=False).agg({
        "lot_standard": "sum",
        "commission_tknlk": "sum",
        **({"transaction_fee": "sum"} if "transaction_fee" in nlk_df.columns else {}),
    }).reset_index().sort_values(by="lot_standard", ascending=False)
    if "transaction_fee" in nlk_sum.columns:
        nlk_sum["transaction_fee_fmt"] = nlk_sum["transaction_fee"].apply(fmt_money)
    nlk_sum["commission_fmt"] = nlk_sum["commission_tknlk"].apply(fmt_money)

    cols = [c for c in ["tknlk", "tknlk_name", "month", "lot_standard", "transaction_fee_fmt", "commission_fmt"] if c in nlk_sum.columns]
    rename = {"tknlk": "Mã TKNLK", "tknlk_name": "Người liên kết", "month": "Month",
              "lot_standard": "Tổng Lot chuẩn", "transaction_fee_fmt": "Tổng Phí GD", "commission_fmt": "Hoa hồng TKNLK"}
    st.dataframe(nlk_sum[cols].rename(columns=rename), use_container_width=True, hide_index=True)
    st.download_button("Tải CSV - Hoa hồng Người liên kết", data=nlk_sum_csv.to_csv(index=False).encode("utf-8"),
                       file_name="commission_tknlk.csv", mime="text/csv")
else:
    st.caption("⚠️ Không thấy cột tknlk/tknlk_name trong dữ liệu.")

st.divider()

# ---------- Bảng 3: Chi tiết theo Investor ----------
st.markdown("## 🧾 Chi tiết theo Investor")
if {"investor_code", "investor_name"}.issubset(df.columns):
    inv_sum = df.copy().reset_index().sort_values(by="lot_standard", ascending=True)

    if "transaction_fee" in inv_sum.columns:
        inv_sum["transaction_fee_fmt"] = inv_sum["transaction_fee"].apply(fmt_money)
    if "actual_profit_VND" in inv_sum.columns:
        inv_sum["actual_profit_fmt"] = inv_sum["actual_profit_VND"].apply(fmt_money)
    inv_sum["commission_fmt"] = inv_sum["commission_total"].apply(fmt_money)

    cols = [c for c in [
       "month", "investor_code", "investor_name", "tkcv",
       "tkcv_name",	"tknlk",	"tknlk_name",
        "lot_standard",
        "lot" if "lot" in inv_sum.columns else None,
        "transaction_fee_fmt" if "transaction_fee_fmt" in inv_sum.columns else None,
        "actual_profit_fmt" if "actual_profit_fmt" in inv_sum.columns else None,
        "commission_fmt"
    ] if c]
    rename = { "month": "Month", "investor_code": "Mã NĐT", "investor_name": "Tên NĐT",
              "tkcv": "Mã TKCV", "tkcv_name": "Chuyên viên", "tknlk": "Mã TKNLK", "tknlk_name": "Người liên kết",
              "lot_standard": "Tổng Lot chuẩn", "lot": "Tổng Lot",
              "transaction_fee_fmt": "Tổng Phí GD", "actual_profit_fmt": "Lãi/Lỗ thực tế",
              "commission_fmt": "Tổng Hoa hồng"}
    inv_sum = inv_sum.sort_values(by="commission_total", ascending=False)
    st.dataframe(inv_sum[cols].rename(columns=rename), use_container_width=True, hide_index=True)
    st.download_button("Tải CSV - Chi tiết theo Investor", data=df.to_csv(index=False).encode("utf-8"),
                       file_name="investor_summary.csv", mime="text/csv")
else:
    st.caption("⚠️ Không thấy cột investor_code/investor_name trong dữ liệu.")
