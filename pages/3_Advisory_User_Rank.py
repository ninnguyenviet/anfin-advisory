# import streamlit as st
# import pandas as pd
# from datetime import datetime
# from services.bigquery_client import load_seasons_from_bq, load_season_data_new

# # =========================
# # Page setup
# # =========================
# st.set_page_config(
#     page_title="Advisory User Rank",
#     page_icon="🏆",
#     layout="wide"
# )
# st.markdown("# 🏆 Advisory User Rank Dashboard")

# # =========================
# # Helpers
# # =========================
# def format_money(val):
#     if pd.isna(val):
#         return "-"
#     try:
#         val = float(val)
#     except Exception:
#         return "-"
#     a = abs(val)
#     if a >= 1e9:
#         return f"{val / 1e9:,.2f} tỷ"
#     if a >= 1e6:
#         return f"{val / 1e6:,.1f} triệu"
#     if a >= 1e3:
#         return f"{val / 1e3:,.0f} nghìn"
#     return f"{val:,.0f}"

# def safe_float(x, default=0.0):
#     try:
#         return float(x)
#     except Exception:
#         return float(default)

# def is_eligible(rec: dict) -> bool:
#     """
#     Điều kiện nhận thưởng một slot:
#     - Đã đăng ký TnC (registered_tnc_at không null)
#     - Mode = PUBLIC
#     - net_pnl > 0
#     """
#     has_tnc = pd.notnull(rec.get("registered_tnc_at"))
#     mode_public = rec.get("mode") == "PUBLIC"
#     net_pnl_pos = pd.notnull(rec.get("net_pnl")) and safe_float(rec.get("net_pnl")) > 0
#     return bool(has_tnc and mode_public and net_pnl_pos)

# def ineligible_reason(rec: dict) -> str | None:
#     if pd.isnull(rec.get("registered_tnc_at")):
#         return "Chưa TnC"
#     if rec.get("mode") == "PRIVATE":
#         return "Đang bật ẩn danh"
#     if pd.isnull(rec.get("net_pnl")) or safe_float(rec.get("net_pnl")) <= 0:
#         return "Khách bị lỗ"
#     return None

# def month_pool_from_df(df_month: pd.DataFrame) -> int:
#     """
#     Pool tháng = total_lot_standard tối đa của tháng * 10_000
#     (trong dữ liệu, total_lot_standard là tổng lot chuẩn toàn season)
#     """
#     if df_month.empty:
#         return 0
#     total_lot_month = df_month["total_lot_standard"].max()
#     total_lot_month = 0 if pd.isna(total_lot_month) else total_lot_month
#     return round(total_lot_month * 10_000)

# # Quy tắc chia thưởng TOP1/2/3
# reward_split = [0.5, 0.3, 0.2]

# # =========================
# # Load danh sách seasons
# # =========================
# seasons_df = load_seasons_from_bq()

# if seasons_df.empty:
#     st.warning("Không tìm thấy season nào từ BigQuery.")
#     st.stop()

# seasons_df["start_date"] = pd.to_datetime(seasons_df["start_date"])
# seasons_df["end_date"] = pd.to_datetime(seasons_df["end_date"])

# # Sắp xếp season theo thời gian để cộng dồn chuẩn
# seasons_df = seasons_df.sort_values(by=["start_date", "id"]).reset_index(drop=True)

# season_name_options = seasons_df["name"].tolist()
# season_name_to_id = dict(zip(seasons_df["name"], seasons_df["id"]))

# # Mặc định chọn season hiện tại (tháng/năm)
# now = datetime.today()
# default_idx_candidates = seasons_df[
#     (seasons_df["start_date"].dt.month == now.month) &
#     (seasons_df["start_date"].dt.year == now.year)
# ].index.tolist()
# default_index = default_idx_candidates[0] if default_idx_candidates else 0

# selected_season_name = st.selectbox("Chọn Season:", options=season_name_options, index=default_index)
# selected_season_id = season_name_to_id[selected_season_name]

# # =========================
# # Main
# # =========================
# with st.spinner("Đang tải dữ liệu..."):
#     df_current = load_season_data_new([selected_season_id])
#     if df_current.empty:
#         st.info("Không có dữ liệu cho season được chọn.")
#         st.stop()
#     df_current.sort_values(by=["leaderboard_id", "rank"], inplace=True)

# # Vị trí season đang chọn trong timeline
# selected_idx_list = seasons_df.index[seasons_df["id"] == selected_season_id].tolist()
# selected_idx = selected_idx_list[0] if selected_idx_list else 0

# # =========================
# # 1) Cộng dồn CHƯA CHI của TẤT CẢ THÁNG TRƯỚC (tính trên POOL SẴN CÓ từng tháng)
# # =========================
# carryover_rows = []             # hiển thị chi tiết
# cumulative_unpaid_before = 0    # cộng dồn CHƯA CHI đến cuối THÁNG TRƯỚC (rolling)

# if selected_idx > 0:
#     for i in range(0, selected_idx):
#         prev_row = seasons_df.iloc[i]
#         prev_id = prev_row["id"]
#         prev_name = prev_row["name"]

#         df_prev = load_season_data_new([prev_id])
#         if df_prev.empty:
#             # Không có data, pool = 0, cộng dồn giữ nguyên
#             carryover_rows.append({
#                 "Season": prev_name,
#                 "Pool tháng (VNĐ)": 0,
#                 "Cộng dồn chưa chi đến cuối THÁNG TRƯỚC (VNĐ)": cumulative_unpaid_before,
#                 "Pool sẵn có trong THÁNG (VNĐ)": cumulative_unpaid_before,
#                 "Đã chi trả trong THÁNG (VNĐ)": 0,
#                 "Tiền chưa chi trả trong THÁNG (VNĐ)": cumulative_unpaid_before,
#                 "Cộng dồn chưa chi đến cuối THÁNG (VNĐ)": cumulative_unpaid_before
#             })
#             continue

#         pool_prev = month_pool_from_df(df_prev)
#         df_prev_top3 = df_prev.sort_values(by="lot_standard", ascending=False).head(3).reset_index(drop=True)

#         # Pool SẴN CÓ cho THÁNG TRƯỚC = pool tháng + cộng dồn trước đó
#         available_before_this_month = cumulative_unpaid_before
#         available_pool_this_month = pool_prev + available_before_this_month

#         used_ratio = 0.0
#         paid_this_month = 0
#         unpaid_this_month = 0

#         # Phân bổ theo reward_split trên "pool sẵn có của tháng"
#         for slot, row_prev in enumerate(df_prev_top3.itertuples()):
#             if slot >= len(reward_split):
#                 break
#             ratio = reward_split[slot]
#             used_ratio += ratio

#             rprev = row_prev._asdict()
#             portion = round(available_pool_this_month * ratio)
#             if is_eligible(rprev):
#                 paid_this_month += portion
#             else:
#                 unpaid_this_month += portion

#         # Nếu thiếu TOP (ít hơn 3 người), phần split còn lại cũng là "không chi được" trong tháng
#         missing_ratio = max(0.0, 1.0 - used_ratio)
#         if missing_ratio > 1e-9:
#             unpaid_this_month += round(available_pool_this_month * missing_ratio)

#         # Cộng dồn chưa chi mới = phần chưa chi của THÁNG này
#         cumulative_unpaid_before = unpaid_this_month

#         carryover_rows.append({
#             "Season": prev_name,
#             "Pool tháng (VNĐ)": pool_prev,
#             "Cộng dồn chưa chi đến cuối THÁNG TRƯỚC (VNĐ)": available_before_this_month,
#             "Pool sẵn có trong THÁNG (VNĐ)": available_pool_this_month,
#             "Đã chi trả trong THÁNG (VNĐ)": paid_this_month,
#             "Tiền chưa chi trả trong THÁNG (VNĐ)": unpaid_this_month,
#             "Cộng dồn chưa chi đến cuối THÁNG (VNĐ)": cumulative_unpaid_before
#         })

# # =========================
# # 2) Tháng đang chọn: Pool hiện tại & Pool SẴN CÓ (đúng công thức)
# # =========================
# current_pool = month_pool_from_df(df_current)

# # ✅ Pool sẵn có tới THÁNG NÀY = Pool tháng hiện tại + Cộng dồn chưa chi đến cuối THÁNG TRƯỚC
# available_pool_upto_current = current_pool + cumulative_unpaid_before

# # =========================
# # 3) Phân bổ trả thưởng tháng đang chọn TRÊN POOL SẴN CÓ
# # =========================
# df_top3_current = df_current.sort_values(by="lot_standard", ascending=False).head(3).reset_index(drop=True)

# bonus_given_from_available = 0       # Số tiền CHI trong tháng đang chọn (ăn vào pool sẵn có)
# unpaid_in_current_month = 0          # Phần không chi được trong THÁNG NÀY → sẽ cộng dồn về sau
# bonuses_rows = []
# used_ratio_current = 0.0

# for slot, row in enumerate(df_top3_current.itertuples()):
#     if slot >= len(reward_split):
#         break
#     r = row._asdict()
#     rank = slot + 1
#     ratio = reward_split[slot]
#     used_ratio_current += ratio

#     amount_this_slot = round(available_pool_upto_current * ratio)
#     eligible = is_eligible(r)
#     status = "Được nhận" if eligible else "Cộng dồn tháng sau"
#     reason = None if eligible else ineligible_reason(r)

#     if eligible:
#         bonus_given_from_available += amount_this_slot
#     else:
#         unpaid_in_current_month += amount_this_slot

#     medals = {1: "🥇", 2: "🥈", 3: "🥉"}
#     bonuses_rows.append({
#         "Hạng": f"{medals.get(rank, '')} TOP {rank}",
#         "User ID": r.get("user_id"),
#         "Họ tên": r.get("full_name"),
#         "Tên giải thưởng": "Chiến Thần Lot",
#         "Tổng Lot": r.get("lot_standard"),
#         "Tiền thưởng (VNĐ)": f"{amount_this_slot:,.0f}",
#         "Điều kiện nhận thưởng": status,
#         "Lý do": reason
#     })

# # Nếu thiếu TOP (ít hơn 3 người), phần split còn lại tiếp tục cộng dồn
# missing_ratio_current = max(0.0, 1.0 - used_ratio_current)
# if missing_ratio_current > 1e-9:
#     unpaid_in_current_month += round(available_pool_upto_current * missing_ratio_current)

# df_top3_final = pd.DataFrame(bonuses_rows)

# # =========================
# # KPIs
# # =========================
# kpi_num_seasons = df_current["leaderboard_id"].nunique()
# kpi_num_users = df_current["user_id"].nunique()
# total_lot_month = df_current["total_lot_standard"].max()
# total_lot_month = 0 if pd.isna(total_lot_month) else total_lot_month

# st.markdown("## KPIs Tổng quan")
# col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
# col1.metric("Số Season (đang xem)", kpi_num_seasons)
# col2.metric("Số User tham gia (tháng)", kpi_num_users)
# col3.metric("Tổng Lot của tháng", f"{total_lot_month:,.2f}")
# col4.metric("Pool tháng hiện tại (VNĐ)", f"{current_pool:,.0f}")

# # ✅ ĐÚNG YÊU CẦU
# col5.metric("Pool sẵn có tới tháng này (VNĐ)", f"{available_pool_upto_current:,.0f}")

# col6.metric("Tiền thưởng đã chi trong tháng này (VNĐ)", f"{bonus_given_from_available:,.0f}")
# col7.metric("Tiền chưa chi trả THÁNG NÀY (VNĐ)", f"{unpaid_in_current_month:,.0f}")

# # =========================
# # Top 3 tháng đang chọn
# # =========================
# st.markdown("## 🏅 Top 3 User tháng hiện tại")
# st.dataframe(df_top3_final, use_container_width=True, hide_index=True)

# # =========================
# # Chi tiết cộng dồn theo từng tháng trước (đÃ sửa theo logic pool sẵn có)
# # =========================
# with st.expander("Chi tiết cộng dồn theo từng tháng trước"):
#     if len(carryover_rows) == 0:
#         st.info("Không có khoản cộng dồn nào từ các tháng trước.")
#     else:
#         df_carry = pd.DataFrame(carryover_rows)
#         # Sắp xếp cột để dễ đọc
#         display_cols = [
#             "Season",
#             "Pool tháng (VNĐ)",
#             "Cộng dồn chưa chi đến cuối THÁNG TRƯỚC (VNĐ)",
#             "Pool sẵn có trong THÁNG (VNĐ)",
#             "Đã chi trả trong THÁNG (VNĐ)",
#             "Tiền chưa chi trả trong THÁNG (VNĐ)",
#             "Cộng dồn chưa chi đến cuối THÁNG (VNĐ)"
#         ]
#         df_carry = df_carry[display_cols]
#         st.dataframe(df_carry, use_container_width=True, hide_index=True)
#         st.caption(f"**Cộng dồn chưa chi đến cuối THÁNG TRƯỚC:** {format_money(cumulative_unpaid_before)}")

# # =========================
# # Bảng chi tiết tất cả User (tháng đang chọn)
# # =========================
# st.markdown("## 📋 Bảng chi tiết tất cả User (tháng đang chọn)")

# # Chuẩn hóa số trước khi format (an toàn nếu cột không tồn tại)
# for col in ["gross_pnl", "net_pnl", "transaction_fee"]:
#     if col in df_current.columns:
#         df_current[col] = pd.to_numeric(df_current[col], errors="coerce")

# df_current["gross_pnl_fmt"] = df_current["gross_pnl"].apply(format_money) if "gross_pnl" in df_current.columns else "-"
# df_current["net_pnl_fmt"] = df_current["net_pnl"].apply(format_money) if "net_pnl" in df_current.columns else "-"
# df_current["transaction_fee_fmt"] = df_current["transaction_fee"].apply(format_money) if "transaction_fee" in df_current.columns else "-"

# # Các cột cần hiển thị
# columns_to_show = [
#     "leaderboard_id", "rank", "full_name", "user_id", "tkcv", "alias_name",
#     "hidden_mode_activated_at", "mode", "registered_tnc_at", "lot", "lot_standard",
#     "transaction_fee_fmt", "gross_pnl_fmt", "net_pnl_fmt"
# ]

# # Lọc ra các cột thực sự tồn tại trong df_current
# available_cols = [c for c in columns_to_show if c in df_current.columns]

# # Mapping tên cột sang tiếng Việt
# col_mapping = {
#     "leaderboard_id": "Season",
#     "rank": "Hạng",
#     "full_name": "Tên",
#     "user_id": "User ID",
#     "tkcv": "Tài khoản CV",
#     "alias_name": "Tên hiển thị",
#     "hidden_mode_activated_at": "Ngày bật ẩn danh",
#     "mode": "Chế độ",
#     "registered_tnc_at": "Ngày đăng ký",
#     "transaction_fee_fmt": "Phí giao dịch",
#     "lot_standard": "Lot chuẩn",
#     "lot": "Lot",
#     "gross_pnl_fmt": "Gross PnL",
#     "net_pnl_fmt": "Net PnL"
# }

# st.dataframe(
#     df_current[available_cols].rename(columns=col_mapping),
#     use_container_width=True,
#     hide_index=True
# )

# # =========================
# # Xuất CSV (tháng đang chọn)
# # =========================
# csv = df_current.to_csv(index=False).encode("utf-8-sig")
# st.download_button(
#     label="Tải dữ liệu CSV (tháng đang chọn)",
#     data=csv,
#     file_name=f"advisory_user_ranks_{selected_season_name}.csv",
#     mime="text/csv"
# )


import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+
from services.bigquery_client import load_seasons_from_bq, load_season_data_new, load_latest_update_times  # <= THÊM IMPORT

# =========================
# Page setup
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

def month_pool_from_df(df_month: pd.DataFrame) -> int:
    if df_month.empty:
        return 0
    total_lot_month = df_month["total_lot_standard"].max()
    total_lot_month = 0 if pd.isna(total_lot_month) else total_lot_month
    return round(total_lot_month * 10_000)

# Quy tắc chia thưởng TOP1/2/3
reward_split = [0.5, 0.3, 0.2]

# =========================
# Load seasons
# =========================
seasons_df = load_seasons_from_bq()
if seasons_df.empty:
    st.warning("Không tìm thấy season nào từ BigQuery.")
    st.stop()

seasons_df["start_date"] = pd.to_datetime(seasons_df["start_date"])
seasons_df["end_date"] = pd.to_datetime(seasons_df["end_date"])
seasons_df = seasons_df.sort_values(by=["start_date", "id"]).reset_index(drop=True)

season_name_options = seasons_df["name"].tolist()
season_name_to_id = dict(zip(seasons_df["name"], seasons_df["id"]))

now_local = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))  # <= dùng VN time cho "Dashboard cập nhật lúc"
default_idx_candidates = seasons_df[
    (seasons_df["start_date"].dt.month == now_local.month) &
    (seasons_df["start_date"].dt.year == now_local.year)
].index.tolist()
default_index = default_idx_candidates[0] if default_idx_candidates else 0

selected_season_name = st.selectbox("Chọn Season:", options=season_name_options, index=default_index)
selected_season_id = season_name_to_id[selected_season_name]

# =========================
# Lấy mốc thời gian cập nhật 2 nguồn & tính "data update đến"
# =========================
with st.spinner("Đang kiểm tra mốc cập nhật dữ liệu..."):
    _df_updates = load_latest_update_times()
    if _df_updates.empty or _df_updates.isna().all(axis=None):
        order_last_update = None
        pnl_last_update = None
    else:
        order_last_update = pd.to_datetime(_df_updates.loc[0, "order_last_update"]) if "order_last_update" in _df_updates.columns else None
        pnl_last_update   = pd.to_datetime(_df_updates.loc[0, "pnl_last_update"]) if "pnl_last_update" in _df_updates.columns else None

    # “Data update đến” = MIN(order_last_update, pnl_last_update) (bảo thủ)
    candidates = [ts for ts in [order_last_update, pnl_last_update] if pd.notnull(ts)]
    data_update_to = min(candidates) if candidates else None

# =========================
# Main data
# =========================
with st.spinner("Đang tải dữ liệu season..."):
    df_current = load_season_data_new([selected_season_id])
    if df_current.empty:
        st.info("Không có dữ liệu cho season được chọn.")
        st.stop()
    df_current.sort_values(by=["leaderboard_id", "rank"], inplace=True)

selected_idx_list = seasons_df.index[seasons_df["id"] == selected_season_id].tolist()
selected_idx = selected_idx_list[0] if selected_idx_list else 0

# =========================
# 1) Cộng dồn CHƯA CHI các THÁNG TRƯỚC (tính trên POOL SẴN CÓ từng tháng)
# =========================
carryover_rows = []
cumulative_unpaid_before = 0  # cộng dồn CHƯA CHI đến cuối THÁNG TRƯỚC (rolling)

if selected_idx > 0:
    for i in range(0, selected_idx):
        prev_row = seasons_df.iloc[i]
        prev_id = prev_row["id"]
        prev_name = prev_row["name"]

        df_prev = load_season_data_new([prev_id])
        if df_prev.empty:
            carryover_rows.append({
                "Season": prev_name,
                "Pool tháng (VNĐ)": 0,
                "Cộng dồn chưa chi đến cuối THÁNG TRƯỚC (VNĐ)": cumulative_unpaid_before,
                "Pool sẵn có trong THÁNG (VNĐ)": cumulative_unpaid_before,
                "Đã chi trả trong THÁNG (VNĐ)": 0,
                "Tiền chưa chi trả trong THÁNG (VNĐ)": cumulative_unpaid_before,
                "Cộng dồn chưa chi đến cuối THÁNG (VNĐ)": cumulative_unpaid_before
            })
            continue

        pool_prev = month_pool_from_df(df_prev)
        df_prev_top3 = df_prev.sort_values(by="lot_standard", ascending=False).head(3).reset_index(drop=True)

        available_before_this_month = cumulative_unpaid_before
        available_pool_this_month = pool_prev + available_before_this_month

        used_ratio = 0.0
        paid_this_month = 0
        unpaid_this_month = 0

        for slot, row_prev in enumerate(df_prev_top3.itertuples()):
            if slot >= len(reward_split):
                break
            ratio = reward_split[slot]
            used_ratio += ratio
            rprev = row_prev._asdict()
            portion = round(available_pool_this_month * ratio)
            if is_eligible(rprev):
                paid_this_month += portion
            else:
                unpaid_this_month += portion

        missing_ratio = max(0.0, 1.0 - used_ratio)
        if missing_ratio > 1e-9:
            unpaid_this_month += round(available_pool_this_month * missing_ratio)

        cumulative_unpaid_before = unpaid_this_month

        carryover_rows.append({
            "Season": prev_name,
            "Pool tháng (VNĐ)": pool_prev,
            "Cộng dồn chưa chi đến cuối THÁNG TRƯỚC (VNĐ)": available_before_this_month,
            "Pool sẵn có trong THÁNG (VNĐ)": available_pool_this_month,
            "Đã chi trả trong THÁNG (VNĐ)": paid_this_month,
            "Tiền chưa chi trả trong THÁNG (VNĐ)": unpaid_this_month,
            "Cộng dồn chưa chi đến cuối THÁNG (VNĐ)": cumulative_unpaid_before
        })

# =========================
# 2) Tháng đang chọn: Pool hiện tại & Pool SẴN CÓ (đúng công thức)
# =========================
current_pool = month_pool_from_df(df_current)
available_pool_upto_current = current_pool + cumulative_unpaid_before  # ✅

# =========================
# 3) Phân bổ tháng hiện tại
# =========================
df_top3_current = df_current.sort_values(by="lot_standard", ascending=False).head(3).reset_index(drop=True)
bonus_given_from_available = 0
unpaid_in_current_month = 0
bonuses_rows = []
used_ratio_current = 0.0

for slot, row in enumerate(df_top3_current.itertuples()):
    if slot >= len(reward_split):
        break
    r = row._asdict()
    rank = slot + 1
    ratio = reward_split[slot]
    used_ratio_current += ratio

    amount_this_slot = round(available_pool_upto_current * ratio)
    eligible = is_eligible(r)
    status = "Được nhận" if eligible else "Cộng dồn tháng sau"
    reason = None if eligible else ineligible_reason(r)

    if eligible:
        bonus_given_from_available += amount_this_slot
    else:
        unpaid_in_current_month += amount_this_slot

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    bonuses_rows.append({
        "Hạng": f"{medals.get(rank, '')} TOP {rank}",
        "User ID": r.get("user_id"),
        "Họ tên": r.get("full_name"),
        "Tên giải thưởng": "Chiến Thần Lot",
        "Tổng Lot": r.get("lot_standard"),
        "Tiền thưởng (VNĐ)": f"{amount_this_slot:,.0f}",
        "Điều kiện nhận thưởng": status,
        "Lý do": reason
    })

missing_ratio_current = max(0.0, 1.0 - used_ratio_current)
if missing_ratio_current > 1e-9:
    unpaid_in_current_month += round(available_pool_upto_current * missing_ratio_current)

df_top3_final = pd.DataFrame(bonuses_rows)

# =========================
# KPIs (thêm khu vực "Cập nhật dữ liệu")
# =========================
kpi_num_seasons = df_current["leaderboard_id"].nunique()
kpi_num_users = df_current["user_id"].nunique()
total_lot_month = df_current["total_lot_standard"].max()
total_lot_month = 0 if pd.isna(total_lot_month) else total_lot_month

st.markdown("## KPIs Tổng quan")
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
col1.metric("Số Season (đang xem)", kpi_num_seasons)
col2.metric("Số User tham gia (tháng)", kpi_num_users)
col3.metric("Tổng Lot của tháng", f"{total_lot_month:,.2f}")
col4.metric("Pool tháng hiện tại (VNĐ)", f"{current_pool:,.0f}")
col5.metric("Pool sẵn có tới tháng này (VNĐ)", f"{available_pool_upto_current:,.0f}")
col6.metric("Tiền thưởng đã chi trong tháng này (VNĐ)", f"{bonus_given_from_available:,.0f}")
col7.metric("Tiền chưa chi trả THÁNG NÀY (VNĐ)", f"{unpaid_in_current_month:,.0f}")

# --- Khu vực cập nhật dữ liệu ---
st.markdown("### ⏱️ Cập nhật dữ liệu")
u1, u2, u3 = st.columns(3)

def fmt_ts(ts):
    if ts is None or pd.isna(ts):
        return "—"
    # ép về Asia/Ho_Chi_Minh để hiển thị nhất quán
    if pd.api.types.is_datetime64_any_dtype(pd.Series([ts])):
        # pandas Timestamp có tz hoặc không; chuẩn hóa:
        ts = pd.to_datetime(ts, utc=False)
    try:
        # Nếu ts là naive, coi như đã cộng +7 ở SQL → gán tz cho VN
        ts = ts.tz_localize(ZoneInfo("Asia/Ho_Chi_Minh"))
    except Exception:
        # Nếu đã có tz, convert sang VN
        ts = ts.tz_convert(ZoneInfo("Asia/Ho_Chi_Minh"))
    return ts.strftime("%Y-%m-%d %H:%M")

u1.metric("Order cập nhật đến", fmt_ts(order_last_update))
u2.metric("PnL cập nhật đến", fmt_ts(pnl_last_update))
u3.metric("Dashboard cập nhật lúc", now_local.strftime("%Y-%m-%d %H:%M"))

# Bảng chi tiết 2 nguồn
if any(v is not None for v in [order_last_update, pnl_last_update]):
    st.dataframe(
        pd.DataFrame([
            {"Nguồn": "commodity.order", "Cập nhật đến (VN)": fmt_ts(order_last_update)},
            {"Nguồn": "pnl_close_status", "Cập nhật đến (VN)": fmt_ts(pnl_last_update)},
            {"Nguồn": "→ Data update đến (min)", "Cập nhật đến (VN)": fmt_ts(data_update_to)},
        ]),
        use_container_width=True, hide_index=True
    )

# =========================
# Top 3 tháng đang chọn
# =========================
st.markdown("## 🏅 Top 3 User tháng hiện tại")
st.dataframe(df_top3_final, use_container_width=True, hide_index=True)

# =========================
# Chi tiết cộng dồn theo từng tháng trước
# =========================
with st.expander("Chi tiết cộng dồn theo từng tháng trước"):
    if len(carryover_rows) == 0:
        st.info("Không có khoản cộng dồn nào từ các tháng trước.")
    else:
        df_carry = pd.DataFrame(carryover_rows)
        display_cols = [
            "Season",
            "Pool tháng (VNĐ)",
            "Cộng dồn chưa chi đến cuối THÁNG TRƯỚC (VNĐ)",
            "Pool sẵn có trong THÁNG (VNĐ)",
            "Đã chi trả trong THÁNG (VNĐ)",
            "Tiền chưa chi trả trong THÁNG (VNĐ)",
            "Cộng dồn chưa chi đến cuối THÁNG (VNĐ)"
        ]
        st.dataframe(df_carry[display_cols], use_container_width=True, hide_index=True)
        st.caption(f"**Cộng dồn chưa chi đến cuối THÁNG TRƯỚC:** {format_money(cumulative_unpaid_before)}")

# =========================
# Bảng chi tiết tất cả User (tháng đang chọn)
# =========================
st.markdown("## 📋 Bảng chi tiết tất cả User (tháng đang chọn)")
for col in ["gross_pnl", "net_pnl", "transaction_fee"]:
    if col in df_current.columns:
        df_current[col] = pd.to_numeric(df_current[col], errors="coerce")

df_current["gross_pnl_fmt"] = df_current["gross_pnl"].apply(format_money) if "gross_pnl" in df_current.columns else "-"
df_current["net_pnl_fmt"] = df_current["net_pnl"].apply(format_money) if "net_pnl" in df_current.columns else "-"
df_current["transaction_fee_fmt"] = df_current["transaction_fee"].apply(format_money) if "transaction_fee" in df_current.columns else "-"

columns_to_show = [
    "leaderboard_id", "rank", "full_name", "user_id", "tkcv", "alias_name",
    "hidden_mode_activated_at", "mode", "registered_tnc_at", "lot", "lot_standard",
    "transaction_fee_fmt", "gross_pnl_fmt", "net_pnl_fmt"
]
available_cols = [c for c in columns_to_show if c in df_current.columns]
col_mapping = {
    "leaderboard_id": "Season",
    "rank": "Hạng",
    "full_name": "Tên",
    "user_id": "User ID",
    "tkcv": "Tài khoản CV",
    "alias_name": "Tên hiển thị",
    "hidden_mode_activated_at": "Ngày bật ẩn danh",
    "mode": "Chế độ",
    "registered_tnc_at": "Ngày đăng ký",
    "transaction_fee_fmt": "Phí giao dịch",
    "lot_standard": "Lot chuẩn",
    "lot": "Lot",
    "gross_pnl_fmt": "Gross PnL",
    "net_pnl_fmt": "Net PnL"
}
st.dataframe(
    df_current[available_cols].rename(columns=col_mapping),
    use_container_width=True,
    hide_index=True
)

# =========================
# Xuất CSV
# =========================
csv = df_current.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="Tải dữ liệu CSV (tháng đang chọn)",
    data=csv,
    file_name=f"advisory_user_ranks_{selected_season_name}.csv",
    mime="text/csv"
)
