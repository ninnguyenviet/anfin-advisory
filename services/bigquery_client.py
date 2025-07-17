import pandas as pd
import json

from google.cloud import bigquery
from google.oauth2 import service_account


import streamlit as st
from google.oauth2 import service_account
from google.cloud import bigquery


def load_account_requests():
   # Lấy thông tin credentials từ streamlit secrets
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )

    # Khởi tạo BigQuery client
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)


    query = """
        SELECT *
        FROM `anfin-prod.raw_mysql.commodity_advisory_account_request`
    """

    df_raw = client.query(query).to_dataframe()

    # Expand JSON
    expanded = df_raw["data"].apply(lambda x: json.loads(x))
    expanded_df = pd.json_normalize(expanded)
    expanded_df.columns = [col.replace(".", "_") for col in expanded_df.columns]
    df = pd.concat([df_raw.drop(columns=["data"]), expanded_df], axis=1)

    # Convert created_at
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["created_at_vn"] = (
        df["created_at"]
        .dt.tz_localize("UTC")
        .dt.tz_convert("Asia/Ho_Chi_Minh")
    )
    df["created_at_vn_str"] = df["created_at_vn"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Remove duplicates
    df = df.sort_values(by="created_at_vn", ascending=False)
    df = df.drop_duplicates(subset="user_id", keep="first")

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
