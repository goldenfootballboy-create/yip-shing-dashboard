import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ==============================================
# 頁面設定
# ==============================================
st.set_page_config(
    page_title="SUPREMACY ENERGY - YIP SHING",
    page_icon="https://i.imgur.com/Q8ehtk3.jpeg",
    layout="wide"
)

# ==============================================
# Google Sheets 連接
# ==============================================
conn = st.connection("gsheets", type=GSheetsConnection)

# ==============================================
# 讀取或建立 supremacy_projects worksheet
# ==============================================
try:
    projects_df = conn.read(worksheet="supremacy_projects", ttl=300)
    if projects_df.empty:
        projects_df = pd.DataFrame(columns=["Date", "Quote_Number", "Project_Detail", "Status"])
except:
    # 自動建立新分頁並加標題列
    header_df = pd.DataFrame([["Date", "Quote_Number", "Project_Detail", "Status"]])
    conn.update(worksheet="supremacy_projects", data=header_df)
    projects_df = pd.DataFrame(columns=["Date", "Quote_Number", "Project_Detail", "Status"])

# ==============================================
# Sidebar - New Project 輸入區
# ==============================================
with st.sidebar:
    st.header("SUPREMACY ENERGY")

    st.markdown("### New Project")

    with st.form(key="supremacy_new_project", clear_on_submit=True):
        quote_number = st.text_input("Quote Number *")
        project_detail = st.text_area("Project Detail *", height=150, placeholder="描述專案內容、客戶需求、規格等")
        status_options = ["Quoting", "Confirmed", "In Production", "Completed"]
        status = st.selectbox("Status", status_options, index=0)

        submitted = st.form_submit_button("Add Project", type="primary", use_container_width=True)

        if submitted:
            if not quote_number.strip() or not project_detail.strip():
                st.error("Quote Number 和 Project Detail 不能為空！")
            else:
                # 新增一列
                new_row = pd.DataFrame([{
                    "Date": date.today().strftime("%Y-%m-%d"),
                    "Quote_Number": quote_number.strip(),
                    "Project_Detail": project_detail.strip(),
                    "Status": status
                }])
                projects_df = pd.concat([projects_df, new_row], ignore_index=True)
                conn.update(worksheet="supremacy_projects", data=projects_df)
                st.success(f"已新增專案：{quote_number}")
                st.rerun()

# ==============================================
# 主頁面內容
# ==============================================
st.title("SUPREMACY ENERGY")



# ==============================================
# 顯示已新增的專案列表
# ==============================================
if len(projects_df) > 0 and "Date" in projects_df.columns:
    # 排序：最新日期在上
    display_df = projects_df.sort_values(by="Date", ascending=False).reset_index(drop=True)
    display_df.index += 1  # 從 1 開始編號

    st.markdown("### 已新增專案")
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=False,
        column_config={
            "Date": st.column_config.DateColumn("日期", format="YYYY-MM-DD"),
            "Quote_Number": "報價編號",
            "Project_Detail": st.column_config.TextColumn("專案內容", width="large"),
            "Status": st.column_config.SelectboxColumn(
                "狀態",
                options=status_options,
                width="medium"
            )
        }
    )
else:
    st.info("尚未新增任何專案，請在左側欄輸入並提交。")

# ==============================================
# 頁腳
# ==============================================
st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")