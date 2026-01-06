# Man Power expander（參考 YIP SHING 風格）
with st.expander(f"🧑‍🔧 Man Power 派工管理 • {row['Quote_Number']}", expanded=False):
    quote_num = row["Quote_Number"]

    # 關鍵修正：展開時強制讀取最新 Man Power 資料
    try:
        latest_manpower = conn.read(worksheet="supremacy_manpower", ttl=0)  # ttl=0 強制無快取
        if not latest_manpower.empty:
            if str(latest_manpower.iloc[0, 0]).strip() == "Quote_Number":
                latest_manpower = latest_manpower.iloc[1:].reset_index(drop=True)
            current_records = latest_manpower[latest_manpower["Quote_Number"] == quote_num]
        else:
            current_records = pd.DataFrame()
    except Exception:
        current_records = pd.DataFrame()

    # 顯示已有記錄
    if len(current_records) > 0:
        st.markdown("**現有人手派工記錄**")
        for _, rec in current_records.iterrows():
            end = rec["End_Date"] if rec["End_Date"] else "進行中"
            st.markdown(f"• **{rec['Staff']}**：{rec['Start_Date']} ~ {end}")
    else:
        st.info("尚未派工人手")

    # 新增派工表單
    st.markdown("**新增派工**")
    with st.form(key=f"manpower_form_sup_{quote_num}", clear_on_submit=True):
        staff_name = st.text_input("員工姓名")
        col_s, col_e = st.columns(2)
        with col_s:
            start_date = st.date_input("開始日期", value=date.today())
        with col_e:
            end_date = st.date_input("結束日期", value=None, help="留空表示進行中")

        if st.form_submit_button("新增並關閉", type="primary", use_container_width=True):
            if not staff_name.strip():
                st.error("員工姓名不能為空！")
            else:
                # 讀最新資料追加
                latest_all = conn.read(worksheet="supremacy_manpower", ttl=0)
                if not latest_all.empty and str(latest_all.iloc[0, 0]).strip() == "Quote_Number":
                    latest_all = latest_all.iloc[1:].reset_index(drop=True)

                new_rec = pd.DataFrame([{
                    "Quote_Number": quote_num,
                    "Staff": staff_name.strip(),
                    "Start_Date": start_date.strftime("%Y-%m-%d"),
                    "End_Date": end_date.strftime("%Y-%m-%d") if end_date else ""
                }])
                updated = pd.concat([latest_all, new_rec], ignore_index=True)
                conn.update(worksheet="supremacy_manpower", data=updated)

                st.success(f"已新增派工：{staff_name}")
                st.rerun()