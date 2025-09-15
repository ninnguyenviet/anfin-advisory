# pages/5_Commission_Share.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

# Dùng service đã đóng gói
from services.bigquery_client import load_commission_dims, load_commission_data

st.set_page_config(page_title="Commission Share", page_icon="💸", layout="wide")
st.markdown("# 💸 Commission Share Dashboard")

# ========== Helpers ==========
def fmt_money(val):
    if pd.isna(val): return "-"
    try: val = float(val)
    except Exception: return "-"
    a = abs(val)
    if a >= 1e9: return f"{val/1e9:,.2f} tỷ"
    if a >= 1e6: return f"{val/1e6:,.1f} triệu"
    if a >= 1e3: return f"{val/1e3:,.0f} nghìn"
    return f"{val:,.0f}"

NUM_COLS = [
    "filled_qty", "standard_filled_qty",
    "profit_first_6m", "profit_after_6m", "profit_all_team",
    "commission_first_6m", "commission_after_6m",
    "commission_amount_first_6m", "commission_amount_after_6m",
    "total_commission", "total_commission_other",
    "total_commission_team", "total_commission_bonus"
]

DISPLAY_ORDER_COLS = [
    "month_order","type","code","name",
    "filled_qty","standard_filled_qty",
    "profit_first_6m","profit_after_6m","profit_all_team",
    "commission_first_6m","commission_after_6m",
    "commission_amount_first_6m","commission_amount_after_6m",
    "total_commission","total_commission_other",
    "total_commission_team","total_commission_bonus",
    "grand_total_commission"
]

def _to_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ========== Build filters ==========
with st.spinner("Đang tải bộ lọc từ BigQuery..."):
    months, types, names, codes = load_commission_dims()

if not months:
    st.info("Không có dữ liệu trong view.")
    st.stop()

default_months = [months[-1]]  # tháng lớn nhất
st.markdown("### Bộ lọc")
c1, c2, c3, c4 = st.columns([2,2,2,2])
with c1:
    sel_months = st.multiselect("Chọn Month", options=months, default=default_months)
with c2:
    sel_types = st.multiselect("Chọn Type", options=types, default=types)
with c3:
    sel_names = st.multiselect("Chọn Name", options=names, default=names)
with c4:
    sel_codes = st.multiselect("Chọn Code", options=codes, default=codes)

with st.spinner("Đang tải dữ liệu..."):
    df = load_commission_data(
        months=sel_months or None,
        types=sel_types or None,
        names=sel_names or None,
        codes=sel_codes or None
    )

if df.empty:
    st.info("Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# Chuẩn hoá kiểu số + tổng grand
df = _to_numeric(df, NUM_COLS).copy()
df["grand_total_commission"] = (
    df.get("total_commission", 0).fillna(0)
    + df.get("total_commission_other", 0).fillna(0)
    + df.get("total_commission_team", 0).fillna(0)
    + df.get("total_commission_bonus", 0).fillna(0)
)

# ========== KPI ==========
tz = pytz.timezone("Asia/Ho_Chi_Minh")
st.caption(f"Hôm nay: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}")

sum_std = float(df.get("standard_filled_qty", 0).sum())
sum_filled = float(df.get("filled_qty", 0).sum())
sum_comm_ind = float(df.get("total_commission", 0).sum())
sum_comm_team = float(df.get("total_commission_team", 0).sum())
sum_comm_bonus = float(df.get("total_commission_bonus", 0).sum())
sum_comm_other = float(df.get("total_commission_other", 0).sum())
sum_comm_grand = float(df.get("grand_total_commission", 0).sum())
sum_profit_6m = float(df.get("profit_first_6m", 0).sum()) + float(df.get("profit_after_6m", 0).sum())
sum_profit_team = float(df.get("profit_all_team", 0).sum())

k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("Entries", f"{len(df):,}")
k2.metric("Tổng Lot", f"{sum_filled:,.2f}")
k3.metric("Tổng Lot chuẩn", f"{sum_std:,.2f}")
k4.metric("HH cá nhân", fmt_money(sum_comm_ind))
k5.metric("HH team / Bonus", f"{fmt_money(sum_comm_team)} / {fmt_money(sum_comm_bonus)}")
k6.metric("Điều chỉnh khác", fmt_money(sum_comm_other))
k7.metric("Tổng HH (Grand)", fmt_money(sum_comm_grand))

st.divider()

# ========== Tổng hợp theo người ==========
st.markdown("## 👤 Tổng hợp theo người (code + name)")
grp_cols = ["month_order", "type", "code", "name"]
agg_map = {
    "filled_qty": "sum",
    "standard_filled_qty": "sum",
    "profit_first_6m": "sum",
    "profit_after_6m": "sum",
    "profit_all_team": "sum",
    "commission_amount_first_6m": "sum",
    "commission_amount_after_6m": "sum",
    "total_commission": "sum",
    "total_commission_other": "sum",
    "total_commission_team": "sum",
    "total_commission_bonus": "sum",
    "grand_total_commission": "sum",
}
sum_by_person_csv = df.groupby(grp_cols, dropna=False).agg(agg_map).reset_index()
sum_by_person = sum_by_person_csv.copy().sort_values(by="grand_total_commission", ascending=False)

for c in [
    "profit_first_6m","profit_after_6m","profit_all_team",
    "commission_amount_first_6m","commission_amount_after_6m",
    "total_commission","total_commission_other","total_commission_team","total_commission_bonus",
    "grand_total_commission"
]:
    if c in sum_by_person.columns:
        sum_by_person[c+"_fmt"] = sum_by_person[c].apply(fmt_money)

cols_show = [
    "month_order","type","code","name",
    "filled_qty","standard_filled_qty",
    "commission_amount_first_6m_fmt" if "commission_amount_first_6m_fmt" in sum_by_person.columns else None,
    "commission_amount_after_6m_fmt"  if "commission_amount_after_6m_fmt"  in sum_by_person.columns else None,
    "total_commission_fmt"            if "total_commission_fmt"            in sum_by_person.columns else None,
    "total_commission_other_fmt"      if "total_commission_other_fmt"      in sum_by_person.columns else None,
    "total_commission_team_fmt"       if "total_commission_team_fmt"       in sum_by_person.columns else None,
    "total_commission_bonus_fmt"      if "total_commission_bonus_fmt"      in sum_by_person.columns else None,
    "grand_total_commission_fmt"      if "grand_total_commission_fmt"      in sum_by_person.columns else None,
]
cols_show = [c for c in cols_show if c]
rename = {
    "month_order":"Month","type":"Type","code":"Code","name":"Name",
    "filled_qty":"Lot","standard_filled_qty":"Lot chuẩn",
    "commission_amount_first_6m_fmt":"HH 6T đầu",
    "commission_amount_after_6m_fmt":"HH sau 6T",
    "total_commission_fmt":"HH cá nhân",
    "total_commission_other_fmt":"Điều chỉnh khác",
    "total_commission_team_fmt":"HH team",
    "total_commission_bonus_fmt":"HH bonus",
    "grand_total_commission_fmt":"Tổng HH"
}
st.dataframe(sum_by_person[cols_show].rename(columns=rename), use_container_width=True, hide_index=True)
st.download_button(
    "Tải CSV - Tổng hợp theo người",
    data=sum_by_person_csv.to_csv(index=False).encode("utf-8-sig"),
    file_name="commission_by_person.csv",
    mime="text/csv",
)

st.divider()

# ========== Tổng hợp Type & Month ==========
st.markdown("## 📦 Tổng hợp theo Type & Month")
grp_tm = ["month_order","type"]
sum_by_type_csv = df.groupby(grp_tm, dropna=False).agg(agg_map).reset_index()
sum_by_type = sum_by_type_csv.copy().sort_values(by=["month_order","type"])

for c in [
    "total_commission","total_commission_team","total_commission_bonus","total_commission_other",
    "grand_total_commission"
]:
    if c in sum_by_type.columns:
        sum_by_type[c+"_fmt"] = sum_by_type[c].apply(fmt_money)

cols_type = [
    "month_order","type",
    "filled_qty","standard_filled_qty",
    "total_commission_fmt" if "total_commission_fmt" in sum_by_type.columns else None,
    "total_commission_team_fmt" if "total_commission_team_fmt" in sum_by_type.columns else None,
    "total_commission_bonus_fmt" if "total_commission_bonus_fmt" in sum_by_type.columns else None,
    "total_commission_other_fmt" if "total_commission_other_fmt" in sum_by_type.columns else None,
    "grand_total_commission_fmt" if "grand_total_commission_fmt" in sum_by_type.columns else None,
]
cols_type = [c for c in cols_type if c]
st.dataframe(
    sum_by_type[cols_type].rename(columns={
        "month_order":"Month","type":"Type",
        "filled_qty":"Lot","standard_filled_qty":"Lot chuẩn",
        "total_commission_fmt":"HH cá nhân",
        "total_commission_team_fmt":"HH team",
        "total_commission_bonus_fmt":"HH bonus",
        "total_commission_other_fmt":"Điều chỉnh khác",
        "grand_total_commission_fmt":"Tổng HH"
    }),
    use_container_width=True, hide_index=True
)
st.download_button(
    "Tải CSV - Tổng hợp theo Type & Month",
    data=sum_by_type_csv.to_csv(index=False).encode("utf-8-sig"),
    file_name="commission_by_type_month.csv",
    mime="text/csv",
)

st.divider()

# ========== Chi tiết ==========
st.markdown("## 🧾 Chi tiết")
detail = df.copy()
for c in ["profit_first_6m","profit_after_6m","profit_all_team",
          "commission_amount_first_6m","commission_amount_after_6m",
          "total_commission","total_commission_other","total_commission_team","total_commission_bonus",
          "grand_total_commission"]:
    if c in detail.columns:
        detail[c + "_fmt"] = detail[c].apply(fmt_money)

detail_cols = [
    "month_order","type","code","name",
    "filled_qty","standard_filled_qty",
    "profit_first_6m_fmt" if "profit_first_6m_fmt" in detail.columns else None,
    "profit_after_6m_fmt" if "profit_after_6m_fmt" in detail.columns else None,
    "profit_all_team_fmt" if "profit_all_team_fmt" in detail.columns else None,
    "commission_amount_first_6m_fmt" if "commission_amount_first_6m_fmt" in detail.columns else None,
    "commission_amount_after_6m_fmt" if "commission_amount_after_6m_fmt" in detail.columns else None,
    "total_commission_fmt" if "total_commission_fmt" in detail.columns else None,
    "total_commission_other_fmt" if "total_commission_other_fmt" in detail.columns else None,
    "total_commission_team_fmt" if "total_commission_team_fmt" in detail.columns else None,
    "total_commission_bonus_fmt" if "total_commission_bonus_fmt" in detail.columns else None,
    "grand_total_commission_fmt" if "grand_total_commission_fmt" in detail.columns else None,
]
detail_cols = [c for c in detail_cols if c]
st.dataframe(
    detail[detail_cols].rename(columns={
        "month_order":"Month","type":"Type","code":"Code","name":"Name",
        "filled_qty":"Lot","standard_filled_qty":"Lot chuẩn",
        "profit_first_6m_fmt":"Lãi 6T đầu","profit_after_6m_fmt":"Lãi sau 6T","profit_all_team_fmt":"Lãi team",
        "commission_amount_first_6m_fmt":"HH 6T đầu","commission_amount_after_6m_fmt":"HH sau 6T",
        "total_commission_fmt":"HH cá nhân","total_commission_other_fmt":"Điều chỉnh khác",
        "total_commission_team_fmt":"HH team","total_commission_bonus_fmt":"HH bonus",
        "grand_total_commission_fmt":"Tổng HH"
    }),
    use_container_width=True, hide_index=True
)

st.download_button(
    "Tải CSV - Chi tiết",
    data=df[DISPLAY_ORDER_COLS[:len(df.columns)] if set(DISPLAY_ORDER_COLS).issubset(df.columns) else df.columns].to_csv(index=False).encode("utf-8-sig"),
    file_name="commission_detail.csv",
    mime="text/csv",
)
