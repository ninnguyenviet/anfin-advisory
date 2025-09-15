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
st.markdown("## 🧾 Chi tiết")

# giữ dữ liệu dạng số để dataframe căn phải
disp = flt.copy()

# cấu hình tên cột + định dạng hiển thị (giữ số -> tự căn phải)
colcfg = {
    "month_order": st.column_config.TextColumn("Month"),
    "type":        st.column_config.TextColumn("Type"),
    "code":        st.column_config.TextColumn("Code"),
    "name":        st.column_config.TextColumn("Name"),

    "filled_qty":            st.column_config.NumberColumn("Lot", format="%.2f"),
    "standard_filled_qty":   st.column_config.NumberColumn("Lot chuẩn", format="%.2f"),

    "profit_first_6m":       st.column_config.NumberColumn("Doanh thu 6T đầu", format="%.0f"),
    "profit_after_6m":       st.column_config.NumberColumn("Doanh thu sau 6T", format="%.0f"),
    "profit_all_team":       st.column_config.NumberColumn("Doanh thu team", format="%.0f"),

    "commission_first_6m":   st.column_config.NumberColumn("Tỷ lệ HH 6T đầu", format="%.2f"),
    "commission_after_6m":   st.column_config.NumberColumn("Tỷ lệ HH sau 6T", format="%.2f"),

    "commission_amount_first_6m": st.column_config.NumberColumn("HH 6T đầu", format="%.0f"),
    "commission_amount_after_6m": st.column_config.NumberColumn("HH sau 6T", format="%.0f"),

    "total_commission":       st.column_config.NumberColumn("HH cá nhân", format="%.0f"),
    "total_commission_other": st.column_config.NumberColumn("Điều chỉnh khác", format="%.0f"),
    "total_commission_team":  st.column_config.NumberColumn("HH team", format="%.0f"),
    "total_commission_bonus": st.column_config.NumberColumn("HH bonus", format="%.0f"),
}

st.dataframe(
    disp,
    use_container_width=True,
    hide_index=True,
    column_config=colcfg
)

st.download_button(
    "Tải CSV (dữ liệu đã lọc)",
    data=flt.to_csv(index=False).encode("utf-8-sig"),
    file_name="commission_filtered.csv",
    mime="text/csv",
)

