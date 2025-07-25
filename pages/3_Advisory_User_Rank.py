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

# Chuyển datetime
seasons_df["start_date"] = pd.to_datetime(seasons_df["start_date"])
seasons_df["end_date"] = pd.to_datetime(seasons_df["end_date"])

# Mapping name <-> id
season_name_map = dict(zip(seasons_df["name"], seasons_df["id"]))
season_name_options = list(season_name_map.keys())

# Mặc định: chọn season theo tháng hiện tại
today = datetime.today()
this_month = today.month
this_year = today.year

season_default_row = seasons_df[
    (seasons_df["start_date"].dt.month == this_month) &
    (seasons_df["start_date"].dt.year == this_year)
]
season_default_names = season_default_row["name"].tolist()
default_index = season_name_options.index(season_default_names[0]) if season_default_names else 0

# UI dropdown chọn season
selected_season_name = st.selectbox(
    "Chọn Season:",
    options=season_name_options,
    index=default_index
)
season_ids = [season_name_map[selected_season_name]]

# Load dữ liệu leaderboard
if season_ids:
    with st.spinner("Đang tải dữ liệu..."):
        df = load_season_data_new(season_ids)

    if df.empty:
        st.info("Không có dữ liệu.")
        st.stop()

    # alias_name
    if "visibility" in df.columns:
        df["alias_name"] = df["visibility"].apply(
            lambda x: x.get("alias_name") if isinstance(x, dict) else "-"
        )
    else:
        df["alias_name"] = df["full_name"]

    df["created_at"] = pd.to_datetime(df["created_at"])

    # Tổng quan chung
    kpi_num_seasons = df["leaderboard_id"].nunique()
    kpi_num_users = df["user_id"].nunique()
    kpi_total_lot = df["total_lot"].sum()

    # TÍNH BONUS
    total_lot_current = df["total_lot"].sum()
    reward_pool = round(total_lot_current * 10_000)

    # Thưởng cộng dồn từ tháng trước
    current_season_id = season_ids[0]
    season_index = seasons_df[seasons_df["id"] == current_season_id].index[0]
    previous_season_bonus = 0
    reward_split = [0.5, 0.3, 0.2]
    rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}

    if season_index > 0:
        previous_season_id = seasons_df.iloc[season_index - 1]["id"]
        df_prev = load_season_data([previous_season_id])

        if not df_prev.empty:
            df_prev["realized_pnl"] = df_prev["realized_pnl"].astype("float64")
            df_prev["total_lot"] = df_prev["total_lot"].astype("float64")
            df_prev_top3 = df_prev.sort_values(by="total_lot", ascending=False).head(3)

            for idx, row in enumerate(df_prev_top3.itertuples()):
                if row.realized_pnl <= 0:
                    prev_reward = round(row.total_lot * 10_000 * reward_split[idx])
                    previous_season_bonus += prev_reward

    reward_pool += previous_season_bonus

    # Tính thưởng cho TOP 3
    df_top3 = df.sort_values(by="total_lot", ascending=False).head(3).copy()
    bonus_given = 0
    bonuses = []

    for idx, row in enumerate(df_top3.itertuples()):
        rank = row.rank
        icon = rank_icons.get(rank, "")
        ratio = reward_split[idx]
        bonus_amount = round(reward_pool * ratio)
        condition = "Được nhận" if row.realized_pnl > 0 else "Cộng dồn tháng sau"
        if condition == "Được nhận":
            bonus_given += bonus_amount
        bonuses.append({
            "Hạng": f"{icon} TOP {rank}",
            "User ID": row.user_id,
            "Họ tên": row.full_name,
            "Tên giải thưởng": "Chiến Thần Lot",
            "Tổng Lot": row.total_lot,
            "Tiền thưởng (VNĐ)": bonus_amount,
            "Điều kiện nhận thưởng": condition
        })

    df_top3_final = pd.DataFrame(bonuses)

    # KPIs
    st.markdown("## KPIs Tổng quan")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Số Season", kpi_num_seasons)
    col2.metric("Số User tham gia", kpi_num_users)
    col3.metric("Tổng Lots", f"{kpi_total_lot:,.2f}")
    col4.metric("Tiền thưởng tháng này (VNĐ)", f"{bonus_given:,.0f}")

    if bonus_given < reward_pool:
        st.info(f"💰 {reward_pool - bonus_given:,.0f} VNĐ sẽ được cộng dồn vì có user chưa đạt PnL dương.")

    # Hiển thị bảng TOP 3
    st.markdown("## 🏅 Top 3 User tháng hiện tại")
    st.dataframe(
        df_top3_final,
        use_container_width=True,
        hide_index=True
    )

    # --- Bảng chi tiết toàn bộ ---
    st.markdown("## 📋 Bảng chi tiết tất cả User")

    def format_money(val):
        if pd.isna(val):
            return "-"
        elif abs(val) >= 1e9:
            return f"{val/1e9:.2f} tỷ"
        elif abs(val) >= 1e6:
            return f"{val/1e6:.1f} triệu"
        else:
            return f"{val:,.0f}"

    df["commission_fmt"] = df["total_earned_commission_fee"].astype("float64").apply(format_money)
    df["realized_pnl_fmt"] = df["realized_pnl"].astype("float64").apply(format_money)
    df["aum_fmt"] = df["aum"].astype("float64").apply(format_money)

    all_cols = [
        "leaderboard_id", "rank", "alias_name", "user_id",
        "total_lot", "commission_fmt", "realized_pnl_fmt", "aum_fmt"
    ]

    st.dataframe(
        df[all_cols].rename(columns={
            "leaderboard_id": "Season",
            "rank": "Hạng",
            "alias_name": "Tên",
            "user_id": "User ID",
            "total_lot": "Tổng Lot",
            "commission_fmt": "Hoa hồng",
            "realized_pnl_fmt": "PnL",
            "aum_fmt": "AUM"
        }),
        use_container_width=True,
        hide_index=True
    )

    # Download
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Tải dữ liệu CSV",
        data=csv,
        file_name="advisory_user_ranks.csv",
        mime="text/csv"
    )
else:
    st.info("Chọn season để xem dữ liệu.")
