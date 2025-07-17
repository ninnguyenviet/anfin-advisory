import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_insight_dashboard(df, partner_type, time_range, time_range_trade):
    """
    Dashboard hiển thị insight tổng quan về partner - tư vấn - giao dịch theo thời gian.
    """

    if df.empty:
        st.info("Không có dữ liệu.")
        return

    # Chuẩn hóa ngày
    for col in ['created_date', 'request_date', 'trade_date']:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # === Filter thời gian ===
    now = pd.Timestamp.now().normalize()

    def get_start_date(option):
        if option == "Tháng này":
            return now.replace(day=1)
        elif option == "Quý này":
            start_month = ((now.month - 1) // 3) * 3 + 1
            return now.replace(month=start_month, day=1)
        return None

    if partner_type != "Tất cả":
        df = df[df['role'] == partner_type]

    start_date = get_start_date(time_range)
    if start_date is not None:
        df = df[df['created_date'] >= start_date]

    start_date_trade = get_start_date(time_range_trade)
    if start_date_trade is not None:
        df = df[df['trade_date'] >= start_date_trade]

    if df.empty:
        st.info("Không có dữ liệu sau khi lọc")
        return

    # === Drill-down lựa chọn ===
    granularity = st.radio("Drill-down theo", options=["Ngày", "Tuần", "Tháng"], index=0, horizontal=True)
    freq = {
        "Ngày": "D",
        "Tuần": "W-MON",
        "Tháng": "MS"
    }[granularity]

    # === 1. Biểu đồ tổng quan theo thời gian ===
    daily_stats = (
        df.groupby(pd.Grouper(key='created_date', freq=freq))['user_id'].nunique().reset_index(name='Đối tác mới')
        .merge(
            df.groupby(pd.Grouper(key='request_date', freq=freq))['member_user_id'].nunique().reset_index(name='Yêu cầu TV'),
            left_on='created_date', right_on='request_date', how='outer'
        )
    )

    daily_stats['date'] = daily_stats['created_date'].combine_first(daily_stats['request_date'])
    daily_stats = daily_stats.sort_values('date').fillna(0)
    daily_stats['date_str'] = daily_stats['date'].dt.strftime('%b %d')

    # ✅ ĐÃ UPDATE: vẽ chung 1 y-axis
    fig_daily = go.Figure()

    fig_daily.add_trace(go.Bar(
        x=daily_stats['date_str'],
        y=daily_stats['Đối tác mới'],
        name='Đối tác mới',
        marker_color='orange'
    ))

    fig_daily.add_trace(go.Scatter(
        x=daily_stats['date_str'],
        y=daily_stats['Yêu cầu TV'],
        name='Yêu cầu tư vấn',
        mode='lines+markers',
        line=dict(color='royalblue')
    ))

    fig_daily.update_layout(
        title='<b>Tổng quan theo thời gian</b>',
        height=450,
        xaxis=dict(title='Thời gian', tickangle=-45),
        yaxis=dict(title='Số lượng'),
        legend=dict(orientation='h', y=1.15, x=0.5, xanchor='center'),
        template='plotly_white',
        hovermode='x unified'  
    )
    # === 2. Tỷ lệ partner theo loại ===
    pie_data = (
        df[df['user_id'].notna()]
        .groupby('user_type')['user_id']
        .nunique()
        .reset_index(name='count')
    )

    fig_pie = px.pie(
        pie_data,
        names='user_type',
        values='count',
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )

    fig_pie.update_traces(
        textinfo='percent+label',
        textfont_size=14
    )

    fig_pie.update_layout(
        title='<b>Tỷ lệ CS / CTV</b>',
        height=350,
        margin=dict(t=50, b=50, l=10, r=10),
        legend=dict(
            orientation='h',
            y=1.15,
            x=0.5,
            xanchor='center'
        )
    )

    # === 3. Biểu đồ lots theo loại ===
    lots_by_type = df[df['trade_date'].notna()]\
        .groupby([pd.Grouper(key='trade_date', freq=freq), 'user_type'])['daily_lot']\
        .sum().reset_index()

    lots_by_type['date_str'] = lots_by_type['trade_date'].dt.strftime('%b %d')

    fig_bar = px.bar(
        lots_by_type,
        x='date_str',
        y='daily_lot',
        color='user_type',
        barmode='stack',
        title='<b>Lots theo loại CS / CTV</b>',
        color_discrete_sequence=px.colors.qualitative.Plotly
    )

    fig_bar.update_layout(
        xaxis=dict(tickangle=-45),
        height=400,
        legend=dict(
            orientation='h',
            y=1.1,
            yanchor='bottom',
            x=0.5,
            xanchor='center'
        )
    )


    # === Hiển thị charts ===
    st.plotly_chart(fig_daily, use_container_width=True)
    st.markdown("---")
    # ✅ FIXED LAYOUT
    col_pie, col_bar = st.columns([1, 3])

    with col_pie:
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_bar:
        st.plotly_chart(fig_bar, use_container_width=True)
