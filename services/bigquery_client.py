import pandas as pd
import json
from google.cloud import bigquery
from google.oauth2 import service_account

import streamlit as st



def load_account_requests():
   # Lấy thông tin credentials từ streamlit secrets
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )

    # Khởi tạo BigQuery client
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)


    query = """
       SELECT * FROM `anfinx-prod.anfinx_advisory.commodity_advisory_account_request_dashboard_vw`
    """

    df_raw = client.query(query).to_dataframe()

    # Expand JSON
    expanded = df_raw["data"].apply(lambda x: json.loads(x))
    expanded_df = pd.json_normalize(expanded)
    expanded_df.columns = [col.replace(".", "_") for col in expanded_df.columns]
    expanded_df = expanded_df.drop(columns=["user_id", "email", "source"], errors="ignore")
    df = pd.concat([df_raw.drop(columns=["data"]), expanded_df], axis=1)
    df.sort_values(by="created_at", ascending=False, inplace=True)
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


def load_season_data(season_id):
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"]
    )
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)

    query = """
        SELECT user_id,leaderboard_id, full_name, user_type,total_lot,aum,total_earned_commission_fee,realized_pnl, rank, created_at   FROM `anfin-prod.raw_mysql.commodity_advisory_advisory_user_rank` 
        WHERE leaderboard_id in ( @season_id)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("season_id", "STRING", season_id)
        ]
    )

    df = client.query(query, job_config=job_config).to_dataframe()
    return df
