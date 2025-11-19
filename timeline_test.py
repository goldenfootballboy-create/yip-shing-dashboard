# -------------------------------------------------
# 右側側邊欄：Checklist Panel（自動寫回 CSV）
# -------------------------------------------------
with st.sidebar:
    st.title("Checklist Panel")

    # 每次都讀最新 CSV
    df_latest = pd.read_csv("projects.csv", encoding='utf-8')

    for row in filtered_df.itertuples(index=False):
        project_name = row.Project_Name

        with st.expander(f"{project_name}", expanded=False):
            # 安全讀取（防 NaN）
            current_order = str(getattr(row, 'Order_List', '')) if pd.notna(getattr(row, 'Order_List', '')) else ''
            current_submit = str(getattr(row, 'Submit_List', '')) if pd.notna(getattr(row, 'Submit_List', '')) else ''

            new_order = st.text_area(
                "需要訂購（逗號分隔）",
                value=current_order,
                height=100,
                key=f"order_edit_{project_name}"
            )
            new_submit = st.text_area(
                "需要提交（逗號分隔）",
                value=current_submit,
                height=100,
                key=f"submit_edit_{project_name}"
            )

            # 自動保存
            if new_order.strip() != current_order.strip() or new_submit.strip() != current_submit.strip():
                df_latest.loc[df_latest['Project_Name'] == project_name, 'Order_List'] = new_order.strip()
                df_latest.loc[df_latest['Project_Name'] == project_name, 'Submit_List'] = new_submit.strip()
                df_latest.to_csv("projects.csv", index=False, encoding='utf-8')
                st.success(f"{project_name} 已自動保存！", icon="✅")
                st.rerun()