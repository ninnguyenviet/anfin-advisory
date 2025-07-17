import streamlit as st
import pandas as pd

def render_kpi_card(title, value, color, sub1_label, sub1_value, sub2_label, sub2_value):
    """
    Render a single KPI card as HTML inside a column.
    """
    card_html = f"""
    <div style="
        background-color: #e6fcf5;
        border-radius: 16px;
        padding: 16px 20px;
        margin: 10px 0;
        height: 180px;
        text-align: left;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        font-family: Arial, sans-serif;
    ">
        <div style="font-size: 20px; font-weight: bold; color: #222; margin-bottom: 8px;">
            {title}
        </div>
        <div style="font-size: 28px; font-weight: bold; color: {color}; margin-bottom: 12px;">
            {value}
        </div>
        <div style="font-size: 18px; display: flex; justify-content: space-between;">
            <div>
                <div style="font-weight: bold;">{sub1_label}</div>
                <div>{sub1_value}</div>
            </div>
            <div>
                <div style="font-weight: bold;">{sub2_label}</div>
                <div>{sub2_value}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def render_dashboard(df):
    # Chuyển cột thời gian
    df['created_date'] = pd.to_datetime(df['created_date'], errors='coerce')
    df['request_date'] = pd.to_datetime(df['request_date'], errors='coerce')
    df['trade_date'] = pd.to_datetime(df['trade_date'], errors='coerce')

    df_valid_created_date = df[df['created_date'].notna()]
    df_valid_request_date = df[df['request_date'].notna()]
    df_valid_trade_date= df[df['trade_date'].notna()]

    now = pd.Timestamp.now().replace(tzinfo=None)
    df_valid_created_l30d = df_valid_created_date[df_valid_created_date['created_date'] >= now - pd.Timedelta(days=30)]
    df_valid_created_l1d = df_valid_created_date[df_valid_created_date['created_date'] >= now - pd.Timedelta(days=1)]

    df_valid_request_l30d = df_valid_request_date[df_valid_request_date['request_date'] >= now - pd.Timedelta(days=30)]
    df_valid_request_l1d = df_valid_request_date[df_valid_request_date['request_date'] >= now - pd.Timedelta(days=1)]
    
    df_valid_trade_l30d = df_valid_trade_date[df_valid_trade_date['request_date'] >= now - pd.Timedelta(days=30)]
    df_valid_trade_l1d = df_valid_trade_date[df_valid_trade_date['request_date'] >= now - pd.Timedelta(days=1)]

    # Tổng đối tác
    total_advisors = df['user_id'].nunique()
    advisors_30d = df_valid_created_l30d['user_id'].nunique()
    advisors_1d = df_valid_created_l1d['user_id'].nunique()

    # Tổng đối tác CS
    cs_advisors = df[df['user_type'] == 'ANFIN_SALESPERSON']['user_id'].nunique()
    cs_30d = df_valid_created_l30d[df_valid_created_l30d['user_type'] == 'ANFIN_SALESPERSON']['user_id'].nunique()
    cs_1d = df_valid_created_l1d[df_valid_created_l1d['user_type'] == 'ANFIN_SALESPERSON']['user_id'].nunique()


    # Tổng đối tác CTV
    ctv_advisors = df[df['user_type'] == 'NORMAL']['user_id'].nunique()
    ctv_30d = df_valid_created_l30d[df_valid_created_l30d['user_type'] == 'NORMAL']['user_id'].nunique()
    ctv_1d = df_valid_created_l1d[df_valid_created_l1d['user_type'] == 'NORMAL']['user_id'].nunique()


    # Tổng yêu cầu
    total_requests = df_valid_request_date['member_user_id'].nunique()
    total_requests_30d = df_valid_request_l30d['member_user_id'].nunique()
    total_requests_1d = df_valid_request_l1d['member_user_id'].nunique()

    # Yêu cầu CS
    total_requests_CS = df_valid_request_date[df_valid_request_date['user_type'] == 'ANFIN_SALESPERSON']['member_user_id'].nunique()
    total_requests_CS_30d = df_valid_request_l30d[df_valid_request_l30d['user_type'] == 'ANFIN_SALESPERSON']['member_user_id'].nunique()
    total_requests_CS_1d = df_valid_request_l1d[df_valid_request_l1d['user_type'] == 'ANFIN_SALESPERSON']['member_user_id'].nunique()

    # Yêu cầu CTV
    total_requests_CTV = df_valid_request_date[df_valid_request_date['user_type'] == 'NORMAL']['member_user_id'].nunique()
    total_requests_CTV_30d = df_valid_request_l30d[df_valid_request_l30d['user_type'] == 'NORMAL']['member_user_id'].nunique()
    total_requests_CTV_1d = df_valid_request_l1d[df_valid_request_l1d['user_type'] == 'NORMAL']['member_user_id'].nunique()


    # Tổng lots
    total_lots = df_valid_trade_date['daily_lot'].sum()
    total_lots_30d = df_valid_trade_l30d['daily_lot'].sum()
    total_lots_1d = df_valid_trade_l1d['daily_lot'].sum()


    # Tổng lots CS
    total_lots_CS = df_valid_trade_date[df_valid_trade_date['user_type'] == 'ANFIN_SALESPERSON']['daily_lot'].sum()
    total_lots_CS_30d = df_valid_trade_l30d[df_valid_trade_l30d['user_type'] == 'ANFIN_SALESPERSON']['daily_lot'].sum()
    total_lots_CS_1d = df_valid_trade_l1d[df_valid_trade_l1d['user_type'] == 'ANFIN_SALESPERSON']['daily_lot'].sum()

    # Tổng lots CTV
    total_lots_CTV = df_valid_trade_date[df_valid_trade_date['user_type'] == 'NORMAL']['daily_lot'].sum()
    total_lots_CTV_30d = df_valid_trade_l30d[df_valid_trade_l30d['user_type'] == 'NORMAL']['daily_lot'].sum()
    total_lots_CTV_1d = df_valid_trade_l1d[df_valid_trade_l1d['user_type'] == 'NORMAL']['daily_lot'].sum()


   

    st.markdown("#### KPIs Tổng Quan")
    # tạo 6 cột cho Đối tác + Yêu cầu tư vấn
    cols_top = st.columns(6)

    # Đối tác
    with cols_top[0]:
        render_kpi_card("Tổng đối tác", total_advisors, "#228B22",
                        "L30D", advisors_30d,
                        "L1D", advisors_1d)
    with cols_top[1]:
        render_kpi_card("Đối tác CS", cs_advisors, "#0077cc",
                        "L30D", cs_30d,
                        "L1D", cs_1d)
    with cols_top[2]:
        render_kpi_card("Đối tác CTV", ctv_advisors, "#880088",
                        "L30D", ctv_30d,
                        "L1D", ctv_1d)

    # Yêu cầu tư vấn
    with cols_top[3]:
        render_kpi_card("Tổng yêu cầu",total_requests, "#d11a2a",
                        "L30D", total_requests_30d,
                        "L1D", total_requests_1d)
    with cols_top[4]:
        render_kpi_card("Yêu cầu CS",total_requests_CS, "#0077cc",
                        "L30D", total_requests_CS_30d,
                        "L1D", total_requests_CS_1d)
    with cols_top[5]:
        render_kpi_card("Yêu cầu CTV", total_requests_CTV, "#880088",
                        "L30D", total_requests_CTV_30d,
                        "L1D", total_requests_CTV_1d)

    # tạo 3 cột cho Lots căn giữa
    col_space, col1, col2, col3, col_space2 = st.columns([4.5, 3, 3, 3, 4.5])

    with col1:
        render_kpi_card("Tổng Lots", round(total_lots,2), "#228B22",
                        "L30D", round(total_lots_30d,2),
                        "L1D", round(total_lots_1d,2))

    with col2:
        render_kpi_card("CS Lots", round(total_lots_CS,2), "#0077cc",
                        "L30D", round(total_lots_CS_30d,2),
                        "L1D", round(total_lots_CS_1d,2))

    with col3:
        render_kpi_card("CTV Lots", round(total_lots_CTV,2), "#880088",
                        "L30D", round(total_lots_CTV_30d,2),
                        "L1D", round(total_lots_CTV_1d,2))
