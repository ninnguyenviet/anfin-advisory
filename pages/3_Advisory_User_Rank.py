import streamlit as st
import pandas as pd
from datetime import datetime
from services.bigquery_client import load_seasons_from_bq, load_season_data_new

st.set_page_config(
    page_title="Advisory User Rank",
    page_icon="🏆",
    layout="wide"
)

st.markdown("# 🏆 Advisory User Rank Dashboard")

# Load danh sách seasons
seasons_df = load_seasons_from_bq()

if seasons_df.empty:
    st.warning("Không tìm thấy season nào từ BigQuery.")
    st.stop()

seasons_df["start_date"] = pd.to_datetime(seasons_df["start_date"])
seasons_df["end_date"] = pd.to_datetime(seasons_df["end_date"])

season_name_map = dict(zip(seasons_df["name"], seasons_df["id"]))
season_name_options = list(season_name_map.keys())

# Mặc định chọn season hiện tại
now = datetime.today()
default_season = seasons_df[
    (seasons_df["start_date"].dt.month == now.month) &
    (seasons_df["start_date"].dt.year == now.year)
]
default_index = season_name_options.index(default_season["name"].iloc[0]) if not default_season.empty else 0

selected_season_name = st.selectbox("Chọn Season:", options=season_name_options, index=default_index)
season_ids = [season_name_map[selected_season_name]]

if season_ids:
    with st.spinner("Đang tải dữ liệu..."):
        df = load_season_data_new(season_ids)
        df.sort_values(by=["leaderboard_id", "rank"], inplace=True)

    if df.empty:
        st.info("Không có dữ liệu.")
        st.stop()

    df["alias_name"] = df["full_name"]

    current_season_id = season_ids[0]
    season_index = seasons_df[seasons_df["id"] == current_season_id].index[0]
    previous_bonus_pool = 0
    reward_split = [0.5, 0.3, 0.2]

    # Cộng dồn thưởng từ các season trước
    if season_index > 0:
        for idx in range(1, season_index + 1):
            season_id = seasons_df.iloc[season_index - idx]["id"]
            df_prev = load_season_data_new([season_id])
            if not df_prev.empty:
                df_prev = df_prev.sort_values(by="lot_standard", ascending=False).head(3)
                total_lot_prev = df_prev["total_lot_standard"].max()
                pool = total_lot_prev * 10000
                for i, row_prev in enumerate(df_prev.itertuples()):
                    if row_prev.net_pnl <= 0:
                        previous_bonus_pool += round(pool * reward_split[i])

    total_lot_month = df["total_lot_standard"].max()
    current_reward_pool = round(total_lot_month * 10000)
    reward_pool = current_reward_pool + previous_bonus_pool

    # Tính thưởng cho top 3
    df_top3 = df.sort_values(by="lot_standard", ascending=False).head(3)

    bonuses = []
    bonus_given = 0
    for idx, row in enumerate(df_top3.itertuples()):
        r = row._asdict()  # convert sang dict để tránh lỗi thuộc tính
        rank = idx + 1
        ratio = reward_split[idx]
        amount = round(reward_pool * ratio)

        status = (
            "Được nhận"
            if r.get("net_pnl", 0) > 0
            and pd.notnull(r.get("registered_tnc_at"))
            and pd.notnull(r.get("hidden_mode_activated_at"))
            else "Cộng dồn tháng sau"
        )

        reason = (
            "Khách bị lỗ" if r.get("net_pnl", 0) < 0
            else "Chưa TnC" if pd.isnull(r.get("registered_tnc_at"))
            else "Đang bật ẩn danh" if pd.isnull(r.get("hidden_mode_activated_at")) 
            else None
        )

        if r.get("net_pnl", 0) > 0 and status == "Được nhận":
            bonus_given += amount

        bonuses.append({
            "Hạng": f"🥇 TOP {rank}" if rank == 1 else f"🥈 TOP {rank}" if rank == 2 else f"🥉 TOP {rank}",
            "User ID": r.get("user_id"),
            "Họ tên": r.get("full_name"),
            "Tên giải thưởng": "Chiến Thần Lot",
            "Tổng Lot": r.get("lot_standard"),
            "Tiền thưởng (VNĐ)": f"{amount:,.0f}",
            "Điều kiện nhận thưởng": status,
            "Lý do": reason
        })

    df_top3_final = pd.DataFrame(bonuses)

    # KPIs
    kpi_num_seasons = df["leaderboard_id"].nunique()
    kpi_num_users = df["user_id"].nunique()

    st.markdown("## KPIs Tổng quan")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Số Season", kpi_num_seasons)
    col2.metric("Số User tham gia", kpi_num_users)
    col3.metric("Tổng Lot của tháng", f"{total_lot_month:,.2f}")
    col4.metric("Tiền thưởng có thể nhận (VNĐ)", f"{bonus_given:,.0f}")
    col5.metric("Tiền chưa chi trả (VNĐ)", f"{reward_pool - bonus_given:,.0f}")

    st.markdown("## 🏅 Top 3 User tháng hiện tại")
    st.dataframe(df_top3_final, use_container_width=True, hide_index=True)

    # Chi tiết toàn bộ user
    st.markdown("## 📋 Bảng chi tiết tất cả User")

    def format_money(val):
        if pd.isna(val):
            return "-"
        abs_val = abs(val)
        if abs_val >= 1e9:
            return f"{val / 1e9:,.2f} tỷ"
        elif abs_val >= 1e6:
            return f"{val / 1e6:,.1f} triệu"
        elif abs_val >= 1e3:
            return f"{val / 1e3:,.0f} nghìn"
        else:
            return f"{val:,.0f}"

    df["gross_pnl_fmt"] = df["gross_pnl"].astype("float64").apply(format_money)
    df["net_pnl_fmt"] = df["net_pnl"].astype("float64").apply(format_money)
    df["transaction_fee_fmt"] = df["transaction_fee"].astype("float64").apply(format_money)

    st.dataframe(
        df[[
            "leaderboard_id", "rank", "alias_name", "user_id","hidden_mode_activated_at",
            "registered_tnc_at", "lot", "lot_standard",
            "transaction_fee_fmt", "gross_pnl_fmt", "net_pnl_fmt"
        ]].rename(columns={
            "leaderboard_id": "Season",
            "rank": "Hạng",
            "alias_name": "Tên",
            "user_id": "User ID",
            "hidden_mode_activated_at": "Ngày tắt ẩn danh",
            "registered_tnc_at": "Ngày đăng ký",
            "transaction_fee_fmt": "Phí giao dịch",
            "lot_standard": "Lot chuẩn",
            "lot": "Lot",
            "gross_pnl_fmt": "Gross PnL",
            "net_pnl_fmt": "Net PnL"
        }),
        use_container_width=True,
        hide_index=True
    )

    # Xuất CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Tải dữ liệu CSV",
        data=csv,
        file_name="advisory_user_ranks.csv",
        mime="text/csv"
    )
