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
# 讀取或建立 supremacy_projects worksheet（安全版）
# ==============================================
try:
    raw_df = conn.read(worksheet="supremacy_projects", ttl=300)
    if raw_df.empty or len(raw_df.columns) < 4:
        header_df = pd.DataFrame(columns=["Date", "Quote_Number", "Project_Detail", "Status"])
        conn.update(worksheet="supremacy_projects", data=header_df)
        projects_df = pd.DataFrame(columns=["Date", "Quote_Number", "Project_Detail", "Status"])
    else:
        projects_df = raw_df.iloc[:, :4].copy()
        projects_df.columns = ["Date", "Quote_Number", "Project_Detail", "Status"]
        if len(projects_df) > 0 and projects_df.iloc[0]["Date"] == "Date":
            projects_df = projects_df.iloc[1:].reset_index(drop=True)
        if "Quote_Number" in projects_df.columns:
            projects_df["Quote_Number"] = projects_df["Quote_Number"].astype(str).str.replace(".0", "", regex=False)
except Exception:
    header_df = pd.DataFrame(columns=["Date", "Quote_Number", "Project_Detail", "Status"])
    conn.update(worksheet="supremacy_projects", data=header_df)
    projects_df = pd.DataFrame(columns=["Date", "Quote_Number", "Project_Detail", "Status"])

# ==============================================
# Sidebar - New Project 輸入區（新增 Date 選擇）
# ==============================================
with st.sidebar:
    st.header("SUPREMACY ENERGY")

    st.markdown("### New Project")

    with st.form(key="supremacy_new_project", clear_on_submit=True):
        # 新增：日期選擇
        project_date = st.date_input("Date *", value=date.today())

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
                    "Date": project_date.strftime("%Y-%m-%d"),
                    "Quote_Number": quote_number.strip(),
                    "Project_Detail": project_detail.strip(),
                    "Status": status
                }])
                # 讀取完整資料再新增
                current_raw = conn.read(worksheet="supremacy_projects", ttl=0)
                updated_df = pd.concat([current_raw, new_row], ignore_index=True)
                conn.update(worksheet="supremacy_projects", data=updated_df)
                st.success(f"已新增專案：{quote_number}")
                # 強制讀最新
                raw_df = conn.read(worksheet="supremacy_projects", ttl=0)
                projects_df = raw_df.iloc[1:].reset_index(drop=True) if len(raw_df) > 1 else pd.DataFrame(columns=["Date", "Quote_Number", "Project_Detail", "Status"])
                projects_df.columns = ["Date", "Quote_Number", "Project_Detail", "Status"]
                projects_df["Quote_Number"] = projects_df["Quote_Number"].astype(str).str.replace(".0", "", regex=False)
                st.rerun()

# ==============================================
# 主頁面內容
# ==============================================
st.title("SUPREMACY ENERGY")

# ==============================================
# 卡片式顯示專案
# ==============================================
if len(projects_df) > 0:
    sorted_df = projects_df.sort_values(by="Date", ascending=False).reset_index(drop=True)

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
            <div style="background: white; border-left: 5px solid {status_color}; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); min-height: 80px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <h5 style="margin:0 0 12px 0; color:#1fb429;">{row["Quote_Number"]}</h5>
                    <p style="margin:0 0 16px 0; font-size:1rem; color:#333; line-height:1.6;">{row["Project_Detail"]}</p>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="background:{status_color}; color:white; padding:5px 14px; border-radius:20px; font-size:0.9rem; font-weight:bold;">
                        {row["Status"]}
                    </span>
                    <small style="color:#888;">{row["Date"]}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Edit + Delete 按鈕
            col_edit, col_delete = st.columns(2)

            with col_edit:
                if st.button("Edit", key=f"edit_{idx}", use_container_width=True):
                    st.session_state[f"edit_mode_{idx}"] = True

            with col_delete:
                if st.button("Delete", key=f"delete_{idx}", type="secondary", use_container_width=True):
                    st.session_state[f"confirm_delete_{idx}"] = True

            # Edit 表單
            if st.session_state.get(f"edit_mode_{idx}", False):
                with st.form(key=f"edit_form_{idx}"):
                    new_quote = st.text_input("Quote Number", value=row["Quote_Number"])
                    new_detail = st.text_area("Project Detail", value=row["Project_Detail"], height=120)
                    new_status = st.selectbox("Status", status_options, index=status_options.index(row["Status"]))

                    col_save, col_cancel = st.columns(2)
                    if col_save.form_submit_button("Save", type="primary", use_container_width=True):
                        projects_df.at[idx, "Quote_Number"] = new_quote.strip()
                        projects_df.at[idx, "Project_Detail"] = new_detail.strip()
                        projects_df.at[idx, "Status"] = new_status
                        conn.update(worksheet="supremacy_projects", data=projects_df)
                        st.success("已更新！")
                        del st.session_state[f"edit_mode_{idx}"]
                        st.rerun()
                    if col_cancel.form_submit_button("Cancel", use_container_width=True):
                        del st.session_state[f"edit_mode_{idx}"]
                        st.rerun()

            # Delete 確認
            if st.session_state.get(f"confirm_delete_{idx}", False):
                st.warning(f"確定要刪除專案 **{row['Quote_Number']}** 嗎？")
                col_yes, col_no = st.columns(2)
                if col_yes.button("Yes, Delete", type="primary", key=f"yes_{idx}"):
                    projects_df = projects_df.drop(idx).reset_index(drop=True)
                    conn.update(worksheet="supremacy_projects", data=projects_df)
                    st.success("已刪除！")
                    del st.session_state[f"confirm_delete_{idx}"]
                    st.rerun()
                if col_no.button("Cancel", key=f"no_{idx}"):
                    del st.session_state[f"confirm_delete_{idx}"]
                    st.rerun()

else:
    st.info("尚未新增任何專案，請在左側欄輸入並提交。")

# ==============================================
# 頁腳
# ==============================================
st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")