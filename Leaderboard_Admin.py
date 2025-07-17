# pages/1_Leaderboard_Admin.py

import streamlit as st
from services.bigquery_client import load_kpi_data
import charts
from components.kpis import render_dashboard
from components.partner_detail import render_partner_table

st.set_page_config(
    page_title="Leaderboard Admin",
    page_icon="📊",
    layout="wide"
)

# Sidebar filters
st.sidebar.title("Bộ lọc Dashboard")

partner_type = st.sidebar.selectbox("Loại đối tác", ["Tất cả", "Customer Success", "Collaborator"])
status = st.sidebar.selectbox("Trạng thái", ["Tất cả", "Active", "Inactive"])
time_range = st.sidebar.selectbox("Khoảng thời gian", ["Tùy chọn", "Tháng này", "Quý này"])
time_range_trade = st.sidebar.selectbox("Khoảng thời gian trader", ["Tùy chọn", "Tháng này", "Quý này"])

st.markdown("""
    <h1 style='text-align: center; margin-bottom: 20px;'>Leaderboard Admin Dashboard</h1>
""", unsafe_allow_html=True)
# Load data
kpi_data = load_kpi_data()
st.markdown("---")
# Render dashboards
render_dashboard(kpi_data)
st.markdown("---")
charts.render_insight_dashboard(
    kpi_data,
    partner_type,
    time_range,
    time_range_trade
)
st.markdown("---")
render_partner_table(
    kpi_data,
    partner_type,
    time_range,
    time_range_trade
)
