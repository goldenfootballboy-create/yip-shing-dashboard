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
    header_df = pd.DataFrame([["Date", "Quote_Number", "Project_Detail", "Status"]])
    conn.update(worksheet="supremacy_projects", data=header_df)
    projects_df = pd.DataFrame(columns=["Date", "Quote_Number", "Project_Detail", "Status"])

# ==============================================
# Sidebar
# ==============================================
with st.sidebar:
    st.header("SUPREMACY ENERGY")

    # Calendar 按鈕 - 跳轉到主頁的 calendar 模式
    if st.button("📅 Calendar", use_container_width=True, type="primary"):
        # 設定主頁的 session_state 為 calendar 模式
        st.session_state.view_mode = "calendar"
        # 切換到主頁
        st.switch_page("streamlit_app.py")  # 改成你的主檔案名，例如 timeline_test.py 或 streamlit_app.py

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

st.markdown("""
### 專案管理系統

此頁面專門用於 SUPREMACY ENERGY 系列專案報價與追蹤。
""")

# ==============================================
# 顯示已新增的專案列表
# ==============================================
if len(projects_df) > 0 and "Date" in projects_df.columns:
    display_df = projects_df.sort_values(by="Date", ascending=False).reset_index(drop=True)
    display_df.index += 1

    st.markdown("### 已新增專案")
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=False,
        column_config={
            "Date": st.column_config.DateColumn("日期", format="YYYY-MM-DD"),
            "Quote_Number": "報價編號",
            "Project_Detail": st.column_config.TextColumn("專案內容", width="large"),
            "Status": "狀態"
        }
    )
else:
    st.info("尚未新增任何專案，請在左側欄輸入並提交。")

# ==============================================
# 頁腳
# ==============================================
st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")