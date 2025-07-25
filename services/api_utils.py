
from services.config import *
import requests
# from google.cloud import bigquery
# from services.bigquery_client import get_bq_client
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd


def get_token():
    token_payload = { "user_id": USER_ID }
    token_headers = { "Content-Type": "application/json" }

    response = requests.post(f"{TOKEN_URL}?api_key={API_KEY}", json=token_payload, headers=token_headers)

    if response.status_code != 200:
        raise Exception(f"❌ Không lấy được token: {response.text}")

    return response.json().get("data")

def fetch_api_data(endpoint_path: str):
    id_token = get_token()

    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    url = f"{API_URL}/{endpoint_path}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"❌ Gọi API thất bại: {response.status_code}, {response.text}")

    return response.json().get("data", {})



# ✅ Hàm load_leaderboard cho app.py dùng
def load_leaderboard(filters=None, endpoint=None):
    data = fetch_api_data(endpoint)
    print(data)
    return data.get("user_ranks", [])  # trả về list để vẽ bảng

def load_season_data(season_ids):
   
    all_data = []
    for season_id in season_ids:
        endpoint = f"{season_id}/ranks"
        data = fetch_api_data(endpoint)
        ranks = data.get("user_ranks", [])
        for row in ranks:
            row["season_id"] = season_id
        all_data.extend(ranks)
    return pd.DataFrame(all_data)

