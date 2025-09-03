import streamlit as st
import pandas as pd
from datetime import datetime
from services.bigquery_client import load_seasons_from_bq, load_season_data_new

# =========================
# Streamlit page config
# =========================
st.set_page_config(
    page_title="Advisory User Rank",
    page_icon="🏆",
    layout="wide"
)
st.markdown("# 🏆 Advisory User Rank Dashboard")

# =========================
# Helpers
# =========================
def format_money(val):
    if pd.isna(val):
        return "-"
    try:
        val = float(val)
    except Exception:
        return "-"
    a = abs(val)
    if a >= 1e9:
        return f"{val / 1e9:,.2f} tỷ"
    if a >= 1e6:
        return f"{val / 1e6:,.1f} triệu"
    if a >= 1e3:
        return f"{val / 1e3:,.0f} nghìn"
    return f"{val:,.0f}"

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)

def is_eligible(rec: dict) -> bool:
    """
    Điều kiện nhận thưởng:
    - Đã đăng ký TnC (registered_tnc_at không null)
    - Mode = PUBLIC
    - net_pnl > 0
    """
    has_tnc = pd.notnull(rec.get("registered_tnc_at"))
    mode_public = rec.get("mode") == "PUBLIC"
    net_pnl_pos = pd.notnull(rec.get("net_pnl")) and safe_float(rec.get("net_pnl")) > 0
    return bool(has_tnc and mode_public and net_pnl_pos)

def ineligible_reason(rec: dict) -> str | None:
    if pd.isnull(rec.get("registered_tnc_at")):
        return "Chưa TnC"
    if rec.get("mode") == "PRIVATE":
        return "Đang bật ẩn danh"
    if pd.isnull(rec.get("net_pnl")) or safe_float(rec.get("net_pnl")) <= 0:
        return "Khách bị lỗ"
    return None

# =========================
# Load danh sách seasons
# =========================
seasons_df = load_seasons_from_bq()

if seasons_df.empty:
    st.warning("Không tìm thấy season nào từ BigQuery.")
    st.stop()

seasons_df["start_date"] = pd.to_datetime(seasons_df["start_date"])
seasons_df["end_date"] = pd.to_datetime(seasons_df["end_date"])

season_name_map = dict(zip(seasons_df["name"], seasons_df["id"]))
season_name_options = list(season_name_map.keys())

# Mặc định chọn season hiện tại theo tháng/năm hôm nay
now = datetime.today()
default_season = seasons_df[
    (seasons_df["start_date"].dt.month == now.month) &
    (seasons_df["start_date"].dt.year == now.year)
]
default_index = season_name_options.index(default_season["name"].iloc[0]) if not default_season.empty else 0

selected_season_name = st.selectbox("Chọn Season:", options=season_name_options, index=default_index)
season_ids = [season_name_map[selected_season_name]]

# =========================
# Main
# =========================
if season_ids:
    with st.spinner("Đang tải dữ liệu..."):
        df = load_season_data_new(season_ids)
        df.sort_values(by=["leaderboard_id", "rank"], inplace=True)

    if df.empty:
        st.info("Không có dữ liệu.")
        st.stop()

    current_season_id = season_ids[0]
    season_index = seasons_df[seasons_df["id"] == current_season_id].index[0]

    reward_split = [0.5, 0.3, 0.2]  # TOP1, TOP2, TOP3
    previous_bonus_pool = 0
    carryover_rows = []  # để debug/hiển thị chi tiết cộng dồn (optional UI)

    # =========================
    # Cộng dồn thưởng từ các season trước
    # Quy tắc: mọi TOP 3 không đạt điều kiện (lỗ / chưa TnC / PRIVATE)
    # ở season trước sẽ cộng dồn vào tháng hiện tại theo tỷ lệ reward_split
    # =========================
    if season_index > 0:
        for idx in range(1, season_index + 1):
            prev_season_row = seasons_df.iloc[season_index - idx]
            prev_season_id = prev_season_row["id"]
            prev_season_name = prev_season_row["name"]

            df_prev_all = load_season_data_new([prev_season_id])
            if df_prev_all.empty:
                continue

            # Tổng lot chuẩn của toàn season trước đó
            season_total_lot = df_prev_all["total_lot_standard"].max()
            season_total_lot = 0 if pd.isna(season_total_lot) else season_total_lot
            pool = round(season_total_lot * 10000)

            # Lấy TOP 3 theo lot_standard
            df_prev_top3 = df_prev_all.sort_values(by="lot_standard", ascending=False).head(3).reset_index(drop=True)

            for i, row_prev in df_prev_top3.iterrows():
                if i >= len(reward_split):
                    break  # an toàn nếu top < 3
                rprev = row_prev.to_dict()
                eligible = is_eligible(rprev)
                portion = round(pool * reward_split[i])

                if not eligible:
                    previous_bonus_pool += portion
                    carryover_rows.append({
                        "Season trước": prev_season_name,
                        "Hạng": f"TOP {i+1}",
                        "User ID": rprev.get("user_id"),
                        "Tên": rprev.get("full_name"),
                        "Lý do không đủ ĐK": ineligible_reason(rprev),
                        "Phần cộng dồn (VNĐ)": portion
                    })

    # =========================
    # Pool hiện tại
    # =========================
    total_lot_month = df["total_lot_standard"].max()
    total_lot_month = 0 if pd.isna(total_lot_month) else total_lot_month
    current_reward_pool = round(total_lot_month * 10000)

    reward_pool = current_reward_pool + previous_bonus_pool

    # =========================
    # Tính thưởng top 3 tháng hiện tại
    # =========================
    df_top3 = df.sort_values(by="lot_standard", ascending=False).head(3).reset_index(drop=True)

    bonuses = []
    bonus_given = 0
    for idx, row in df_top3.iterrows():
        r = row.to_dict()
        rank = idx + 1
        ratio = reward_split[idx] if idx < len(reward_split) else 0
        amount = round(reward_pool * ratio)

        eligible = is_eligible(r)
        status = "Được nhận" if eligible else "Cộng dồn tháng sau"
        reason = None if eligible else ineligible_reason(r)

        if eligible:
            bonus_given += amount

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        bonuses.append({
            "Hạng": f"{medals.get(rank, '')} TOP {rank}",
            "User ID": r.get("user_id"),
            "Họ tên": r.get("full_name"),
            "Tên giải thưởng": "Chiến Thần Lot",
            "Tổng Lot": r.get("lot_standard"),
            "Tiền thưởng (VNĐ)": f"{amount:,.0f}",
            "Điều kiện nhận thưởng": status,
            "Lý do": reason
        })

    df_top3_final = pd.DataFrame(bonuses)

    # =========================
    # KPIs
    # =========================
    kpi_num_seasons = df["leaderboard_id"].nunique()
    kpi_num_users = df["user_id"].nunique()

    st.markdown("## KPIs Tổng quan")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Số Season", kpi_num_seasons)
    col2.metric("Số User tham gia", kpi_num_users)
    col3.metric("Tổng Lot của tháng", f"{total_lot_month:,.2f}")
    col4.metric("Tiền thưởng có thể nhận (VNĐ)", f"{bonus_given:,.0f}")
    col5.metric("Tiền chưa chi trả (VNĐ)", f"{reward_pool - bonus_given:,.0f}")

    # =========================
    # Top 3 tháng hiện tại
    # =========================
    st.markdown("## 🏅 Top 3 User tháng hiện tại")
    st.dataframe(df_top3_final, use_container_width=True, hide_index=True)

    # (Tùy chọn) Hiển thị chi tiết cộng dồn từ các season trước
    with st.expander("Chi tiết cộng dồn từ các season trước"):
        if len(carryover_rows) == 0:
            st.info("Không có khoản cộng dồn nào từ các season trước.")
        else:
            df_carry = pd.DataFrame(carryover_rows)
            st.dataframe(df_carry, use_container_width=True, hide_index=True)
            st.caption(f"**Tổng tiền cộng dồn:** {format_money(previous_bonus_pool)}")

    # =========================
    # Bảng chi tiết tất cả User
    # =========================
    st.markdown("## 📋 Bảng chi tiết tất cả User")

    # Format tiền
    df["gross_pnl_fmt"] = df["gross_pnl"].astype("float64").apply(format_money)
    df["net_pnl_fmt"] = df["net_pnl"].astype("float64").apply(format_money)
    df["transaction_fee_fmt"] = df["transaction_fee"].astype("float64").apply(format_money)

    st.dataframe(
        df[[
            "leaderboard_id", "rank", "full_name", "user_id", "alias_name", "hidden_mode_activated_at", "mode",
            "registered_tnc_at", "lot", "lot_standard",
            "transaction_fee_fmt", "gross_pnl_fmt", "net_pnl_fmt"
        ]].rename(columns={
            "leaderboard_id": "Season",
            "rank": "Hạng",
            "full_name": "Tên",
            "user_id": "User ID",
            "alias_name": "Tên hiển thị",
            "hidden_mode_activated_at": "Ngày bật ẩn danh",
            "mode": "Chế độ",
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

    # =========================
    # Xuất CSV
    # =========================
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Tải dữ liệu CSV",
        data=csv,
        file_name="advisory_user_ranks.csv",
        mime="text/csv"
    )
