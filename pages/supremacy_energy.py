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
                new_row = pd.DataFrame([{
                    "Date": date.today().strftime("%Y-%m-%d"),
                    "Quote_Number": quote_number.strip(),
                    "Project_Detail": project_detail.strip(),
                    "Status": status
                }])
                projects_df = pd.concat([projects_df, new_row], ignore_index=True)
                conn.update(worksheet="supremacy_projects", data=projects_df)
                st.success(f"已新增專案：{quote_number}")
                # 強制讀最新並刷新
                projects_df = conn.read(worksheet="supremacy_projects", ttl=0)
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
# 卡片式顯示已新增專案（縮小 + Delete 按鈕）
# ==============================================
if len(projects_df) > 0 and "Date" in projects_df.columns:
    sorted_df = projects_df.sort_values(by="Date", ascending=False).reset_index(drop=True)

    st.markdown("### 已新增專案")

    cols = st.columns(4)
    for idx, row in sorted_df.iterrows():
        with cols[idx % 4]:
            status_color = {
                "Quoting": "#ffaa00",
                "Confirmed": "#00aa00",
                "In Production": "#0066ff",
                "Completed": "#66cc66"
            }.get(row["Status"], "#888888")

            st.markdown(f"""
            <div style="background: white; border-left: 5px solid {status_color}; border-radius: 8px; padding: 12px; margin-bottom: 16px; box-shadow: 0 3px 8px rgba(0,0,0,0.1); min-height: 160px;">
                <h5 style="margin:0 0 8px 0; color:#1fb429;">{row["Quote_Number"]}</h5>
                <p style="margin:0 0 10px 0; font-size:0.9rem; color:#333; line-height:1.4;">{row["Project_Detail"]}</p>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top: auto;">
                    <span style="background:{status_color}; color:white; padding:3px 10px; border-radius:15px; font-size:0.8rem; font-weight:bold;">
                        {row["Status"]}
                    </span>
                    <small style="color:#888;">{row["Date"]}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Delete 按鈕
            if st.button("Delete", key=f"delete_{idx}", type="secondary", use_container_width=True):
                quote_to_delete = row["Quote_Number"]
                # 刪除該行
                projects_df = projects_df[projects_df["Quote_Number"] != quote_to_delete].reset_index(drop=True)
                conn.update(worksheet="supremacy_projects", data=projects_df)
                st.success(f"已刪除專案：{quote_to_delete}")

                # 關鍵：強制重新讀取最新資料並刷新頁面
                projects_df = conn.read(worksheet="supremacy_projects", ttl=0)
                st.rerun()

else:
    st.info("尚未新增任何專案，請在左側欄輸入並提交。")

# ==============================================
# 頁腳
# ==============================================
st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")