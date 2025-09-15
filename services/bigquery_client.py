# services/bigquery_client.py
from __future__ import annotations
import json
import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig, ArrayQueryParameter, ScalarQueryParameter
from google.oauth2 import service_account

# =========================
# BigQuery client & helpers
# =========================

def _bq_client() -> bigquery.Client:
    """
    Tạo BigQuery client từ Streamlit secrets.
    Yêu cầu st.secrets["google_service_account"] là JSON service account.
    """
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )
    return bigquery.Client(credentials=credentials, project=credentials.project_id)

@st.cache_data(ttl=600, show_spinner=False)
def run_query_df(sql: str, params: list | None = None) -> pd.DataFrame:
    """
    Chạy query với optional parameters và trả về DataFrame.
    Tự cache 10 phút.
    """
    client = _bq_client()
    job_cfg = QueryJobConfig(query_parameters=params) if params else None
    return client.query(sql, job_config=job_cfg).result().to_dataframe()

def _arr_param(name: str, typ: str, values: list | None):
    return ArrayQueryParameter(name, typ, values or [])

def _scalar_bool(name: str, val: bool):
    return ScalarQueryParameter(name, "BOOL", bool(val))

def _scalar_str(name: str, val: str):
    return ScalarQueryParameter(name, "STRING", val)

def _scalar_date(name: str, val):
    # val có thể là datetime.date hoặc string 'YYYY-MM-DD' (BQ tự cast hợp lệ)
    return ScalarQueryParameter(name, "DATE", val)

# =========================
# View FQNs (đổi 1 chỗ là đủ)
# =========================
V_ACCOUNT_REQUESTS = "`anfinx-prod.anfinx_advisory.commodity_advisory_account_request_dashboard_vw`"
V_OVERVIEW_KPI     = "`anfinx-prod.anfinx_advisory.anfinx_advisory_overview_dashboard_vw`"
V_ALL_KPI          = "`anfinx-prod.anfinx_advisory.anfinx_advisory_all_kpi_data_vw`"
T_LEADERBOARD_SEASON = "`anfin-prod.raw_mysql.commodity_advisory_advisory_leaderboard_season`"
V_USER_RANK        = "`anfinx-prod.anfinx_advisory.anfinx_advisory_user_rank_by_data_vw`"
V_COMMISSION       = "`anfinx-prod.anfinx_advisory.anfinx_advisory_commission_dashboard_vw`"

# ==================================================
# 1) Account Requests (mở rộng JSON ở cột data)
# ==================================================
@st.cache_data(ttl=600, show_spinner=False)
def load_account_requests() -> pd.DataFrame:
    sql = f"SELECT * FROM {V_ACCOUNT_REQUESTS}"
    df_raw = run_query_df(sql)

    # Expand JSON từ cột "data"
    if "data" in df_raw.columns:
        expanded = df_raw["data"].apply(lambda x: json.loads(x) if pd.notna(x) else {})
        expanded_df = pd.json_normalize(expanded)
        expanded_df.columns = [c.replace(".", "_") for c in expanded_df.columns]
        # Chỉ giữ các field cần (thiếu thì tự fill NA)
        need_cols = ["avatar_url", "bio", "display_name", "group_name", "highlights", "service_info", "phone_number"]
        for c in need_cols:
            if c not in expanded_df.columns:
                expanded_df[c] = pd.NA
        df = pd.concat([df_raw.drop(columns=["data"]), expanded_df[need_cols]], axis=1)
    else:
        df = df_raw.copy()

    # Dedup columns & sort by created_at nếu có
    df = df.loc[:, ~df.columns.duplicated()].reset_index(drop=True)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df = df.sort_values(by="created_at", ascending=False, na_position="last")
    return df

# ==================================================
# 2) Seasons (leaderboard season)
# ==================================================
@st.cache_data(ttl=600, show_spinner=False)
def load_seasons_from_bq() -> pd.DataFrame:
    sql = f"""
        SELECT 
            id,
            CONCAT(FORMAT_DATE('%m/%Y', DATE(end_date)),
                   ' Cuộc thi vinh danh các broker xuất sắc nhất') AS name,
            start_date,
            end_date
        FROM {T_LEADERBOARD_SEASON}
        WHERE id != 'season_1_id'
    """
    return run_query_df(sql)

# ==================================================
# 3) KPI tổng quan
# ==================================================
@st.cache_data(ttl=600, show_spinner=False)
def load_kpi_data() -> pd.DataFrame:
    sql = f"SELECT * FROM {V_OVERVIEW_KPI}"
    return run_query_df(sql)

# ==================================================
# 4) User Rank by Season
# ==================================================
@st.cache_data(ttl=600, show_spinner=False)
def load_season_data_new(season_id: str) -> pd.DataFrame:
    sql = f"""
        SELECT user_id, tkcv, leaderboard_id, full_name, registered_tnc_at,
               lot, lot_standard, transaction_fee, gross_pnl, net_pnl, total_lot_standard,
               rank, hidden_mode_activated_at, mode, alias_name
        FROM {V_USER_RANK}
        WHERE leaderboard_id = @season_id
    """
    params = [
        _scalar_str("season_id", season_id),
    ]
    return run_query_df(sql, params)

# ==================================================
# 5) All KPI view (filter theo month)
# ==================================================
@st.cache_data(ttl=600, show_spinner=False)
def load_all_kpi_view(month) -> pd.DataFrame:
    """
    month: date hoặc string 'YYYY-MM-DD'. BQ type DATE.
    """
    sql = f"""
        SELECT * FROM {V_ALL_KPI}
        WHERE month IN UNNEST(@month)  -- cho phép truyền list hoặc 1 phần tử
    """
    # Cho phép truyền 1 giá trị => convert thành list
    month_list = month if isinstance(month, (list, tuple, set)) else [month]
    params = [
        _arr_param("month", "DATE", list(month_list)),
    ]
    return run_query_df(sql, params)

# ==================================================
# 6) Dims & Data cho trang Commission (theo yêu cầu)
# ==================================================
@st.cache_data(ttl=600, show_spinner=False)
def load_commission_dims():
    """
    Trả về 4 danh sách để build filter: months (string), types, names, codes.
    month_order cast về STRING để UI dễ xài và so sánh.
    """
    sql = f"""
    WITH base AS (
      SELECT
        CAST(month_order AS STRING) AS month_order,
        CAST(type AS STRING) AS type,
        CAST(code AS STRING) AS code,
        CAST(name AS STRING) AS name
      FROM {V_COMMISSION}
    )
    SELECT
      ARRAY_AGG(DISTINCT month_order IGNORE NULLS) AS months,
      ARRAY_AGG(DISTINCT type IGNORE NULLS)        AS types,
      ARRAY_AGG(DISTINCT name IGNORE NULLS)        AS names,
      ARRAY_AGG(DISTINCT code IGNORE NULLS)        AS codes
    FROM base
    """
    df = run_query_df(sql)
    if df.empty:
        return [], [], [], []
    months = sorted([m for m in (df.at[0, "months"] or []) if m is not None])
    types  = sorted([t for t in (df.at[0, "types"]  or []) if t is not None])
    names  = sorted([n for n in (df.at[0, "names"]  or []) if n is not None])
    codes  = sorted([c for c in (df.at[0, "codes"]  or []) if c is not None])
    return months, types, names, codes

@st.cache_data(ttl=600, show_spinner=False)
def load_commission_data(
    months: list[str] | None = None,
    types: list[str]  | None = None,
    names: list[str]  | None = None,
    codes: list[str]  | None = None,
) -> pd.DataFrame:
    """
    Đọc dữ liệu commission đã lọc.
    So sánh dựa trên CAST(.. AS STRING) để tránh lệch kiểu.
    """
    sql = f"""
    SELECT
      CAST(month_order AS STRING) AS month_order,
      CAST(type AS STRING) AS type,
      CAST(code AS STRING) AS code,
      CAST(name AS STRING) AS name,
      filled_qty, standard_filled_qty,
      profit_first_6m, profit_after_6m,
      commission_first_6m, commission_after_6m,
      commission_amount_first_6m, commission_amount_after_6m,
      total_commission, total_commission_other,
      profit_all_team, total_commission_team, total_commission_bonus
    FROM {V_COMMISSION}
    WHERE (@has_months = FALSE OR CAST(month_order AS STRING) IN UNNEST(@months))
      AND (@has_types  = FALSE OR CAST(type        AS STRING) IN UNNEST(@types))
      AND (@has_names  = FALSE OR CAST(name        AS STRING) IN UNNEST(@names))
      AND (@has_codes  = FALSE OR CAST(code        AS STRING) IN UNNEST(@codes))
    """
    params = [
        _scalar_bool("has_months", bool(months)),
        _scalar_bool("has_types",  bool(types)),
        _scalar_bool("has_names",  bool(names)),
        _scalar_bool("has_codes",  bool(codes)),
        _arr_param("months", "STRING", months),
        _arr_param("types",  "STRING", types),
        _arr_param("names",  "STRING", names),
        _arr_param("codes",  "STRING", codes),
    ]
    return run_query_df(sql, params)

# ==================================================
# 7) Back-compat cho trang KPI cũ (nếu vẫn dùng)
# ==================================================
@st.cache_data(ttl=600, show_spinner=False)
def load_advisory_dims() -> pd.DataFrame:
    """
    Lấy danh sách month, type (nhẹ) để build filter & nhận diện kiểu dữ liệu của month
    cho các trang KPI cũ.
    """
    sql = f"SELECT DISTINCT month, type FROM {V_ALL_KPI}"
    return run_query_df(sql)

@st.cache_data(ttl=600, show_spinner=False)
def load_advisory_commission_data(
    months: list | None = None,
    types: list[str] | None = None,
    month_is_date: bool | None = None
) -> pd.DataFrame:
    """
    Dữ liệu KPI tổng hợp (ALL KPI) cho trang cũ — giữ nguyên API cũ của bạn.
    - months: list[date] nếu month_is_date=True, ngược lại list[str]
    - types:  list[str]
    - month_is_date: None -> bỏ WHERE month (load all); True/False -> filter theo đúng kiểu
    """
    where = []
    params = []
    if month_is_date is not None and months:
        where.append("month IN UNNEST(@months)")
        if month_is_date:
            params.append(_arr_param("months", "DATE", months))
        else:
            params.append(_arr_param("months", "STRING", months))
    if types:
        where.append("type IN UNNEST(@types)")
        params.append(_arr_param("types", "STRING", types))

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    sql = f"SELECT * FROM {V_ALL_KPI} {where_sql}"
    return run_query_df(sql, params if params else None)
