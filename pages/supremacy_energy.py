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
# 讀取或建立 supremacy_projects worksheet（支援 Work Order）
# ==============================================
try:
    raw_df = conn.read(worksheet="supremacy_projects", ttl=300)
    if raw_df.empty or len(raw_df.columns) < 5:
        header_df = pd.DataFrame(columns=["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"])
        conn.update(worksheet="supremacy_projects", data=header_df)
        projects_df = pd.DataFrame(columns=["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"])
    else:
        raw_df = raw_df.iloc[:, :5]
        raw_df.columns = ["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"]
        if len(raw_df) > 0 and str(raw_df.iloc[0]["Date"]).strip().lower() in ["date", "日期"]:
            raw_df = raw_df.iloc[1:].reset_index(drop=True)
        projects_df = raw_df.copy()
        projects_df["Quote_Number"] = projects_df["Quote_Number"].astype(str).str.replace(".0", "", regex=False)
        if "Work_Order" not in projects_df.columns:
            projects_df["Work_Order"] = ""
        projects_df["Work_Order"] = projects_df["Work_Order"].fillna("").astype(str)
except Exception:
    header_df = pd.DataFrame(columns=["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"])
    conn.update(worksheet="supremacy_projects", data=header_df)
    projects_df = pd.DataFrame(columns=["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"])

# ==============================================
# Sidebar - 新增專案 + 搜尋功能
# ==============================================
with st.sidebar:
    st.header("SUPREMACY ENERGY")

    st.markdown("### 新增副業專案")

    with st.form(key="supremacy_new_project", clear_on_submit=True):
        project_date = st.date_input("Date *", value=date.today())
        quote_number = st.text_input("Quote Number *")
        work_order = st.text_input("Work Order")
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
                    "Work_Order": work_order.strip(),
                    "Project_Detail": project_detail.strip(),
                    "Status": status
                }])
                current_raw = conn.read(worksheet="supremacy_projects", ttl=0)
                if len(current_raw) > 0 and str(current_raw.iloc[0,0]).strip().lower() in ["date", "日期"]:
                    current_raw = current_raw.iloc[1:]
                updated_df = pd.concat([current_raw, new_row], ignore_index=True)
                conn.update(worksheet="supremacy_projects", data=updated_df)
                st.success(f"已新增專案：{quote_number} (Work Order: {work_order or '無'})")
                st.rerun()

    st.markdown("---")

    st.markdown("### 🔍 搜尋專案")
    search_query = st.text_input(
        "輸入 Quote Number 或 Work Order",
        placeholder="例如：Q2025-001 或 WO-456",
        key="supremacy_search",
        label_visibility="collapsed"
    )

    if st.button("清除搜尋", type="secondary", use_container_width=True):
        if "supremacy_search" in st.session_state:
            del st.session_state.supremacy_search
        st.rerun()

# ==============================================
# 主畫面標題
# ==============================================
st.title("SUPREMACY ENERGY - 副業專案管理")

# ==============================================
# 應用搜尋邏輯
# ==============================================
display_df = projects_df.copy()
if search_query:
    query = search_query.strip().lower()
    mask = (
        display_df["Quote_Number"].astype(str).str.lower().str.contains(query) |
        display_df["Work_Order"].astype(str).str.lower().str.contains(query)
    )
    display_df = display_df[mask].reset_index(drop=True)
    if len(display_df) == 0:
        st.info(f"找不到包含「{search_query}」的專案")
    else:
        st.success(f"找到 {len(display_df)} 個符合的專案")

# ==============================================
# 卡片式顯示專案
# ==============================================
if len(display_df) > 0:
    sorted_df = display_df.sort_values(by="Date", ascending=False).reset_index(drop=True)

    cols = st.columns(4)
    for idx, row in sorted_df.iterrows():
        with cols[idx % 4]:
            status_color = {
                "Quoting": "#ffaa00",
                "Confirmed": "#00aa00",
                "In Production": "#0066ff",
                "Completed": "#66cc66"
            }.get(row["Status"], "#888888")

            work_order_display = f"<br><small style='color:#666;'>Work Order: <strong>{row['Work_Order'] or '無'}</strong></small>" if row["Work_Order"] else ""

            st.markdown(f"""
            <div style="background: white; border-left: 5px solid {status_color}; border-radius: 12px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); min-height: 250px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <h5 style="margin:0 0 8px 0; color:#1fb429;">{row["Quote_Number"]}</h5>
                    {work_order_display}
                    <p style="margin:16px 0 0 0; font-size:1rem; color:#333; line-height:1.6; flex-grow:1;">{row["Project_Detail"]}</p>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:20px;">
                    <span style="background:{status_color}; color:white; padding:6px 16px; border-radius:20px; font-size:0.95rem; font-weight:bold;">
                        {row["Status"]}
                    </span>
                    <small style="color:#888;">{row["Date"]}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_edit, col_delete = st.columns(2)

            with col_edit:
                if st.button("Edit", key=f"edit_sup_{idx}", use_container_width=True):
                    st.session_state[f"edit_mode_sup_{idx}"] = True

            with col_delete:
                if st.button("Delete", key=f"delete_sup_{idx}", type="secondary", use_container_width=True):
                    st.session_state[f"confirm_delete_sup_{idx}"] = True

            # Edit 表單
            if st.session_state.get(f"edit_mode_sup_{idx}", False):
                original_idx = sorted_df.index[idx]
                with st.form(key=f"edit_form_sup_{idx}"):
                    new_quote = st.text_input("Quote Number", value=row["Quote_Number"])
                    new_work_order = st.text_input("Work Order", value=row["Work_Order"])
                    new_detail = st.text_area("Project Detail", value=row["Project_Detail"], height=120)
                    new_status = st.selectbox("Status", status_options, index=status_options.index(row["Status"]))

                    col_save, col_cancel = st.columns(2)
                    if col_save.form_submit_button("Save", type="primary", use_container_width=True):
                        projects_df.at[original_idx, "Quote_Number"] = new_quote.strip()
                        projects_df.at[original_idx, "Work_Order"] = new_work_order.strip()
                        projects_df.at[original_idx, "Project_Detail"] = new_detail.strip()
                        projects_df.at[original_idx, "Status"] = new_status
                        conn.update(worksheet="supremacy_projects", data=projects_df)
                        st.success("已更新專案！")
                        st.rerun()
                    if col_cancel.form_submit_button("Cancel", use_container_width=True):
                        del st.session_state[f"edit_mode_sup_{idx}"]
                        st.rerun()

            # Delete 確認
            if st.session_state.get(f"confirm_delete_sup_{idx}", False):
                st.warning(f"確定要刪除專案 **{row['Quote_Number']}** 嗎？")
                col_yes, col_no = st.columns(2)
                if col_yes.button("Yes, Delete", type="primary", key=f"yes_sup_{idx}"):
                    projects_df = projects_df.drop(original_idx).reset_index(drop=True)
                    conn.update(worksheet="supremacy_projects", data=projects_df)
                    st.success("已刪除專案！")
                    st.rerun()
                if col_no.button("Cancel", key=f"no_sup_{idx}"):
                    del st.session_state[f"confirm_delete_sup_{idx}"]
                    st.rerun()

else:
    if search_query:
        st.info("沒有找到符合搜尋條件的專案")
    else:
        st.info("尚未新增任何副業專案，請在左側欄輸入並提交。")

# ==============================================
# 頁腳
# ==============================================
st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")