import streamlit as st

def render_account_table(df):
    st.subheader("Danh sách Account Requests")

    display_cols = [
        "id",
        "display_name",
        "group_name",
        "phone_number",
        "status",
        "type",
        "created_at_vn_str"
    ]

    STATUS_COLORS = {
        "APPROVED": "green",
        "NEW": "orange",
        "CANCELLED": "red"
    }

    def color_status(val):
        color = STATUS_COLORS.get(val, "black")
        return f"color: {color}"

    if not df.empty:
        styled_df = df[display_cols].style.applymap(color_status, subset=["status"])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("Không có dữ liệu phù hợp với bộ lọc.")


def render_account_details(df):
    df_new = df[df["status"] == "NEW"]
    st.subheader("Chi tiết các Account Chờ duyệt (NEW)")

    if df_new.empty:
        st.success("Hiện không có account nào ở trạng thái NEW.")
    else:
        for _, row in df_new.iterrows():
            with st.expander(f"👁 {row['display_name']} ({row['created_at_vn_str']})"):
                left, right = st.columns([1, 3])

                with left:
                    st.image(row["avatar_url"] or "https://via.placeholder.com/150", width=150)

                with right:
                    st.markdown(f"**👤 Tên:** {row['display_name']}")
                    st.markdown(f"**👥 Group:** {row['group_name']}")
                    st.markdown(f"**📞 SĐT:** {row['phone_number']}")
                    st.markdown(f"**🕑 Thời gian tạo (VN):** {row['created_at_vn_str']}")
                    st.markdown(f"**📋 Trạng thái:** {row['status']}")
                    st.markdown(f"**🔖 Type:** {row['type']}")
                    st.markdown(f"**📝 Bio:** {row['bio'] or '-'}")
                    st.markdown(f"**🎯 Service Info:** {row['service_info'] or '-'}")

                    if row["highlights"]:
                        st.markdown("**🏅 Highlights:**")
                        for item in row["highlights"]:
                            st.markdown(f"- **{item.get('name')}**: {item.get('value')}")
