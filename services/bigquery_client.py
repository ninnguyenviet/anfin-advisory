import pandas as pd
import json
from google.cloud import bigquery
from google.oauth2 import service_account

import streamlit as st


def load_account_requests():
    # Lấy credentials từ streamlit secrets
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)

    query = """
       SELECT * 
       FROM `anfinx-prod.anfinx_advisory.commodity_advisory_account_request_dashboard_vw`
    """
    df_raw = client.query(query).to_dataframe()

    # Expand JSON từ cột "data"
    expanded = df_raw["data"].apply(lambda x: json.loads(x) if pd.notna(x) else {})
    expanded_df = pd.json_normalize(expanded)
    expanded_df.columns = [col.replace(".", "_") for col in expanded_df.columns]

    # Chỉ lấy các field cần
    need_cols = ["avatar_url", "bio", "display_name", "group_name", "highlights","service_info", "phone_number"]
    expanded_df = expanded_df.reindex(columns=need_cols, fill_value=pd.NA)

    # Kết hợp lại
    df = pd.concat([df_raw.drop(columns=["data"]), expanded_df], axis=1)

    # Đảm bảo không có cột trùng
    df = df.loc[:, ~df.columns.duplicated()]

    # Reset index & sort
    df = df.reset_index(drop=True)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df = df.sort_values(by="created_at", ascending=False, na_position="last")

    return df
# -------------------------------------------------
def load_seasons_from_bq():
    
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )

    # Khởi tạo BigQuery client
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)
    query = """
         SELECT 
            id, 
            CONCAT(
                FORMAT_DATE('%m/%Y', DATE(end_date)),
                " Cuộc thi vinh danh các broker xuất sắc nhất"
            ) AS name, 
            start_date, 
            end_date
        FROM `anfin-prod.raw_mysql.commodity_advisory_advisory_leaderboard_season`
        where id != "season_1_id"
    """
    df = client.query(query).to_dataframe()
    return df

def load_kpi_data():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )

    # Khởi tạo BigQuery client
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)

    query = """
         SELECT * FROM `anfinx-prod.anfinx_advisory.anfinx_advisory_overview_dashboard_vw` 
    """

    df = client.query(query).to_dataframe()
    return df


def load_season_data_new(season_id):
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)

    query = """
        SELECT user_id,leaderboard_id, full_name,registered_tnc_at, lot,lot_standard, transaction_fee,gross_pnl, net_pnl, total_lot_standard, rank, hidden_mode_activated_at, mode, alias_name    FROM `anfinx-prod.anfinx_advisory.anfinx_advisory_user_rank_by_data_vw` 
        WHERE leaderboard_id in ( @season_id)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("season_id", "STRING", season_id)
        ]
    )

    df = client.query(query, job_config=job_config).to_dataframe()
    return df


def load_all_kpi_view(month) -> pd.DataFrame:
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)

    query = """
        SELECT * FROM `anfinx-prod.anfinx_advisory.anfinx_advisory_all_kpi_data_vw`
        WHERE month in ( @month)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("month", "Date", month)
        ]
    )
    df = client.query(query).to_dataframe()
    return df




VIEW_FQN = "anfinx-prod.anfinx_advisory.anfinx_advisory_all_kpi_data_vw"

def _bq_client():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )
    return bigquery.Client(credentials=credentials, project=credentials.project_id)

def load_advisory_dims():
    """
    Lấy danh sách month, type (nhẹ) để build filter & nhận diện kiểu dữ liệu của month.
    """
    client = _bq_client()
    q = f"SELECT DISTINCT month, type FROM `anfinx-prod.anfinx_advisory.anfinx_advisory_all_kpi_data_vw`"
    return client.query(q).to_dataframe()

def load_advisory_commission_data(months=None, types=None, month_is_date: bool | None = None) -> pd.DataFrame:
    """
    Tải dữ liệu chính theo bộ lọc.
    - months: list[date] nếu month_is_date=True, ngược lại list[str]
    - types:  list[str]
    - month_is_date: None -> bỏ WHERE month (load all); True/False -> filter theo đúng kiểu
    """
    client = _bq_client()

    where = []
    params = []

    if month_is_date is not None and months:
        where.append("month IN UNNEST(@months)")
        if month_is_date:
            params.append(bigquery.ArrayQueryParameter("months", "DATE", months))
        else:
            params.append(bigquery.ArrayQueryParameter("months", "STRING", months))

    if types:
        where.append("type IN UNNEST(@types)")
        params.append(bigquery.ArrayQueryParameter("types", "STRING", types))

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    q = f"SELECT * FROM `{VIEW_FQN}` {where_sql}"

    job_config = bigquery.QueryJobConfig(query_parameters=params or None)
    return client.query(q, job_config=job_config).to_dataframe()
