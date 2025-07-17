import streamlit as st
import pandas as pd
import io

def render_partner_table(df, partner_type, time_range, time_range_trade):
    st.markdown("## Bảng Chi Tiết Đối Tác")

    # ====== Tiền xử lý ngày và lọc ======
    df['created_date'] = pd.to_datetime(df['created_date'], errors='coerce')
    df['trade_date'] = pd.to_datetime(df['trade_date'], errors='coerce')

    now = pd.Timestamp.now().normalize()

    # Lọc theo thời gian tạo
    if time_range == "Tháng này":
        df = df[df['created_date'] >= now.replace(day=1)]
    elif time_range == "Quý này":
        start_month = ((now.month - 1) // 3) * 3 + 1
        df = df[df['created_date'] >= now.replace(month=start_month, day=1)]

    # Lọc theo thời gian giao dịch
    if time_range_trade == "Trade Tháng này":
        df = df[df['trade_date'] >= now.replace(day=1)]
    elif time_range_trade == "Trade Quý này":
        start_month = ((now.month - 1) // 3) * 3 + 1
        df = df[df['trade_date'] >= now.replace(month=start_month, day=1)]

    if partner_type != "Tất cả":
        df = df[df["user_type"] == partner_type]

    if df.empty:
        st.info("Không có dữ liệu để hiển thị.")
        return

    # ====== Group dữ liệu ======
    df_grouped = (
        df.groupby(['user_name', 'user_type', 'created_date', 'status'], as_index=False)
        .agg({
            'member_user_id': lambda x: x.nunique(),
            'daily_lot': 'sum'
        })
        .rename(columns={
            'user_name': 'Tên đối tác',
            'user_type': 'Loại đối tác',
            'created_date': 'Ngày tham gia',
            'status': 'Trạng thái',
            'member_user_id': 'SL Người được giới thiệu',
            'daily_lot': 'Tổng Lots'
        })
    )
    df_grouped['Tổng Lots'] = df_grouped['Tổng Lots'].round(2)

    # ====== Phân trang ======
    rows_per_page = 10
    total_rows = len(df_grouped)
    total_pages = (total_rows + rows_per_page - 1) // rows_per_page

    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0

    # ====== Thanh điều khiển phân trang + download ======
    left_col, right_col = st.columns([6, 4])
    with right_col:
        col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1.5, 1, 1])

        with col1:
            if st.button("⬅️ Previous", key="prev_btn", use_container_width=True,
                         disabled=st.session_state.page_number <= 0):
                st.session_state.page_number -= 1

        with col2:
            if st.button("➡️ Next", key="next_btn", use_container_width=True,
                         disabled=st.session_state.page_number >= total_pages - 1):
                st.session_state.page_number += 1

        with col3:
            if st.button("📄 Show all", key="show_all_btn", use_container_width=True):
                st.session_state.page_number = -1

        with col4:
            csv = df_grouped.to_csv(index=False).encode("utf-8")
            st.download_button("📥 CSV", data=csv, file_name="partner_detail.csv",
                               mime="text/csv", key="csv_btn", use_container_width=True)

        with col5:
            excel_buffer = io.BytesIO()
            df_grouped.to_excel(excel_buffer, index=False, engine="openpyxl")
            excel_data = excel_buffer.getvalue()
            st.download_button("📥 Excel", data=excel_data, file_name="partner_detail.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="excel_btn", use_container_width=True)

    # ====== Hiển thị bảng ======
    if st.session_state.page_number == -1:
        display_df = df_grouped
    else:
        start = st.session_state.page_number * rows_per_page
        end = start + rows_per_page
        display_df = df_grouped.iloc[start:end]

    st.dataframe(display_df, use_container_width=True)
    st.caption(f"Hiển thị {len(display_df)} đối tác trên tổng {total_rows} entries.")
    st.caption(f"Trang {st.session_state.page_number + 1} / {total_pages} (tổng số trang)")