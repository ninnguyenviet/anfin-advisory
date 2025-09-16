# pages/5_Commission_Simple.py
import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime
import pytz

st.set_page_config(page_title="Commission", page_icon="💸", layout="wide")
st.markdown("# 💸 Commission Dashboard")

# ===== Helpers =====
SCOPES = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive.readonly",  # phòng khi view đọc từ Sheets/Drive
]

NUMERIC_COLS = [
    "filled_qty", "standard_filled_qty",
    "profit_first_6m", "profit_after_6m", "profit_all_team",
    "commission_first_6m", "commission_after_6m",
    "commission_amount_first_6m", "commission_amount_after_6m",
    "total_commission", "total_commission_other",
    "total_commission_team", "total_commission_bonus",
]

QUERY = """
SELECT
  month_order, type, code, name,
  filled_qty, standard_filled_qty,
  profit_first_6m, profit_after_6m,
  commission_first_6m, commission_after_6m,
  commission_amount_first_6m, commission_amount_after_6m,
  total_commission, total_commission_other,
  profit_all_team, total_commission_team, total_commission_bonus
FROM `anfinx-prod.anfinx_advisory.anfinx_advisory_commission_dashboard_vw`
"""

def fmt_money(val):
    if pd.isna(val): return "-"
    try:
        val = float(val)
    except Exception:
        return "-"
    a = abs(val)
    if a >= 1e9: return f"{val/1e9:,.2f} tỷ"
    if a >= 1e6: return f"{val/1e6:,.1f} triệu"
    if a >= 1e3: return f"{val/1e3:,.0f} nghìn"
    return f"{val:,.0f}"

@st.cache_data(ttl=600, show_spinner=False)
def load_data() -> pd.DataFrame:
    # Credentials từ Streamlit secrets
    base = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )
    creds = base.with_scopes(SCOPES)
    client = bigquery.Client(credentials=creds, project=creds.project_id)

    df = client.query(QUERY).result().to_dataframe()

    # Chuẩn hóa kiểu dữ liệu
    if "month_order" in df.columns:
        df["month_order"] = df["month_order"].astype(str)
    for c in NUMERIC_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["code", "name", "type"]:
        if c in df.columns:
            df[c] = df[c].astype(str)

    return df

# ===== Load data =====
with st.spinner("Đang tải dữ liệu..."):
    df = load_data()

if df.empty:
    st.info("Không có dữ liệu.")
    st.stop()

# ===== Filters =====
st.markdown("### Bộ lọc")
months = sorted(df["month_order"].dropna().unique().tolist())
types  = sorted(df["type"].dropna().unique().tolist())

c1, c2, c3 = st.columns([2, 2, 3])
with c1:
    sel_month = st.selectbox("Month", options=months, index=len(months)-1 if months else 0)
with c2:
    sel_types = st.multiselect("Type", options=types, default=types)
with c3:
    broker_query = st.text_input("Code hoặc name chứa…", "")

flt = df.copy()
if sel_month:
    flt = flt[flt["month_order"] == str(sel_month)]
if sel_types:
    flt = flt[flt["type"].isin(sel_types)]
q = broker_query.strip()
if q:
    q_lower = q.lower()
    flt = flt[
        flt["code"].str.lower().str.contains(q_lower, na=False)
        | flt["name"].str.lower().str.contains(q_lower, na=False)
    ]

if flt.empty:
    st.info("Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# ===== KPIs =====
num_members = flt["code"].nunique()  # Số member theo code
sum_commission = float(flt["total_commission"].sum()) if "total_commission" in flt.columns else 0.0
sum_bonus = float(flt["total_commission_bonus"].sum()) if "total_commission_bonus" in flt.columns else 0.0

tz = pytz.timezone("Asia/Ho_Chi_Minh")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Số Member", f"{num_members:,}")
k2.metric("Tổng commission", fmt_money(sum_commission))
k3.metric("Tổng commission bonus", fmt_money(sum_bonus))
k4.caption(f"Hôm nay: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}")

st.divider()

# ===== Detail table (tất cả cột) =====# ===== Detail table (tất cả cột, số/tiền căn phải) =====
# ===== Detail table (format , for thousands and . for decimals) =====
st.markdown("## 🧾 Chi tiết")

disp = flt.copy()

# Đổi tên cột để hiển thị
rename = {
    "month_order": "Month",
    "type": "Type",
    "code": "Code",
    "name": "Name",
    "filled_qty": "Lot",
    "standard_filled_qty": "Lot chuẩn",
    "profit_first_6m": "Doanh thu 6T đầu",
    "profit_after_6m": "Doanh thu sau 6T",
    "profit_all_team": "Doanh thu team",
    "commission_first_6m": "Tỷ lệ HH 6T đầu",
    "commission_after_6m": "Tỷ lệ HH sau 6T",
    "commission_amount_first_6m": "HH 6T đầu",
    "commission_amount_after_6m": "HH sau 6T",
    "total_commission": "HH cá nhân",
    "total_commission_other": "Điều chỉnh khác",
    "total_commission_team": "HH team",
    "total_commission_bonus": "HH bonus",
}
disp = disp.rename(columns=rename)

# Các cột số cần format nhóm nghìn bằng dấu , và thập phân bằng .
cols_2dec = ["Lot", "Lot chuẩn", "Tỷ lệ HH 6T đầu", "Tỷ lệ HH sau 6T"]
cols_0dec_money = [
    "Doanh thu 6T đầu", "Doanh thu sau 6T", "Doanh thu team",
    "HH 6T đầu", "HH sau 6T", "HH cá nhân", "Điều chỉnh khác", "HH team", "HH bonus"
]

fmt0 = (lambda x: f"{x:,.0f}" if pd.notna(x) else "-")   # 1,234,567
fmt2 = (lambda x: f"{x:,.2f}" if pd.notna(x) else "-")   # 1,234,567.89

fmt_map = {c: fmt2 for c in cols_2dec}
fmt_map.update({c: fmt0 for c in cols_0dec_money})

# Căn phải cho các cột số
right_align_cols = cols_2dec + cols_0dec_money

styled = (
    disp.style
        .format(fmt_map)
        .set_properties(subset=right_align_cols, **{"text-align": "right"})
)

st.dataframe(styled, use_container_width=True, hide_index=True)
csv_out = flt.copy()
csv_out["code"] = csv_out["code"].apply(lambda x: f'="{x}"') 
st.download_button(
    "Tải CSV (dữ liệu đã lọc)",
    data=csv_out.to_csv(index=False).encode("utf-8-sig"),
    file_name="commission_filtered.csv",
    mime="text/csv",
)

