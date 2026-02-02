import streamlit as st
import pandas as pd
import json
from datetime import date
import time
import gspread
from google.oauth2.service_account import Credentials

# ==============================================
# 頁面設定
# ==============================================
st.set_page_config(
    page_title="SUPREMACY ENERGY",
    page_icon="https://i.imgur.com/Q8ehtk3.jpeg",
    layout="wide"
)


# ==============================================
# Google Sheets 連線（使用你的平鋪式 secrets，無需 private_gsheet_credentials）
# ==============================================
@st.cache_resource(show_spinner="正在連線 Google Sheets...", ttl=1800)  # 快取 30 分鐘，避免重複授權
def get_spreadsheet():
    creds_info = st.secrets["connections"]["gsheets"]

    # 直接把 creds_info 傳進去（你的 secrets 已經是完整的 service account dict）
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)

    spreadsheet_id = creds_info.get("spreadsheet", "").strip()

    if not spreadsheet_id:
        st.error("secrets 中缺少 'spreadsheet'（試算表 ID）")
        st.stop()

    # 只驗證長度（最安全）
    if len(spreadsheet_id) != 44:
        st.error("Spreadsheet ID 長度不正確（應為 44 個字元）")
        st.info(f"讀到的值：{spreadsheet_id}")
        st.stop()

    # 可選：如果想提醒使用者可能格式怪怪的
    if spreadsheet_id.count("-") not in [0, 4]:
        st.warning("Spreadsheet ID 包含不尋常的連字號數量，但仍嘗試連線...")

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        return spreadsheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("找不到該試算表")
        st.info(f"請確認 ID 是否正確：{spreadsheet_id}")
        st.info(
            "也請確認服務帳號 'yips-824@precise-plane-481307-u2.iam.gserviceaccount.com' 已加入試算表並給予「編輯者」權限")
        st.stop()
    except gspread.exceptions.APIError as e:
        err = str(e).lower()
        if "403" in err or "permission" in err:
            st.error("權限不足（403 Forbidden）")
            st.info("""
            請執行以下步驟：
            1. 開啟你的 Google Sheet（ID: 17GqTXQOxLSRLqd0DuNE24XVC20caWwpkXYJB6vwNwzA）
            2. 點擊右上角「分享」
            3. 加入 email：yips-824@precise-plane-481307-u2.iam.gserviceaccount.com
            4. 權限選擇「編輯者」
            """)
            st.stop()
        else:
            st.error(f"Google API 錯誤：{e}")
            st.stop()
    except Exception as e:
        st.error(f"連線失敗：{type(e).__name__} - {e}")
        st.stop()


# 取得 spreadsheet（只執行一次，之後快取）
spreadsheet = get_spreadsheet()

# 讀取工作表
try:
    worksheet_projects = spreadsheet.worksheet("supremacy_projects")
    projects_data = worksheet_projects.get_all_records()
    projects_df = pd.DataFrame(projects_data)

    worksheet_manpower = spreadsheet.worksheet("supremacy_manpower")
    manpower_data = worksheet_manpower.get_all_records()
    manpower_df = pd.DataFrame(manpower_data)
except gspread.exceptions.WorksheetNotFound as e:
    st.error(f"找不到工作表：{e}")
    st.info("請確認試算表中已有 'supremacy_projects' 和 'supremacy_manpower' 兩個工作表")
    st.stop()

# 欄位處理（如果工作表空或欄位不對，補上標頭）
if projects_df.empty or len(projects_df.columns) < 5:
    header = ["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"]
    projects_df = pd.DataFrame(columns=header)
    worksheet_projects.update([header])

if manpower_df.empty or len(manpower_df.columns) < 4:
    header_man = ["Quote_Number", "Staff", "Start_Date", "End_Date"]
    manpower_df = pd.DataFrame(columns=header_man)
    worksheet_manpower.update([header_man])

# 資料清理
projects_df["Quote_Number"] = projects_df["Quote_Number"].astype(str).str.replace(r"\.0$", "", regex=True)
projects_df["Work_Order"] = projects_df["Work_Order"].fillna("").astype(str)
projects_df["Date"] = pd.to_datetime(projects_df["Date"], errors="coerce")

manpower_df["Quote_Number"] = manpower_df["Quote_Number"].astype(str).str.replace(r"\.0$", "", regex=True)
# ==============================================
# Sidebar
# ==============================================
with st.sidebar:
    st.header("SUPREMACY ENERGY")

    # Filters
    st.markdown("### Filters")

    years = sorted(projects_df["Date"].dt.year.dropna().unique(), reverse=True)
    years = list(years) + [2025] if 2025 not in years else list(years)
    selected_year = st.selectbox("Year", ["All"] + years, index=0)

    months = ["All", "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    selected_month = st.selectbox("Month", months, index=0)

    st.markdown("---")

    st.markdown("### New Project")

    with st.form(key="supremacy_new_project", clear_on_submit=True):
        project_date = st.date_input("Date *", value=date.today())
        quote_number = st.text_input("Quote Number *")
        work_order = st.text_input("Work Order")
        project_detail = st.text_area("Project Detail *", height=150)
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

                # 讀取最新資料，避免覆蓋
                current_projects = pd.DataFrame(worksheet_projects.get_all_records())
                if not current_projects.empty and str(current_projects.iloc[0,0]).strip().lower() in ["date", "日期"]:
                    current_projects = current_projects.iloc[1:].reset_index(drop=True)
                updated_projects = pd.concat([current_projects, new_row], ignore_index=True)
                worksheet_projects.clear()
                worksheet_projects.update([updated_projects.columns.values.tolist()] + updated_projects.values.tolist())

                st.success(f"已新增專案：{quote_number}")
                st.rerun()

    st.markdown("---")

    st.markdown("### 🔍 搜尋專案")
    search_query = st.text_input("輸入 Quote Number 或 Work Order", key="supremacy_search", label_visibility="collapsed")
    if st.button("清除搜尋", type="secondary", use_container_width=True):
        st.rerun()

    st.markdown("---")

    if st.button("📅 查看主日曆", type="primary", use_container_width=True):
        st.session_state.view_mode = "calendar"
        st.switch_page("YipShing.py")

# ==============================================
# 主畫面標題
# ==============================================
st.title("SUPREMACY ENERGY")

# ==============================================
# 搜尋 + 年月篩選
# ==============================================
display_df = projects_df.copy()

if search_query:
    query = search_query.strip().lower()
    mask = (display_df["Quote_Number"].str.lower().str.contains(query) |
            display_df["Work_Order"].str.lower().str.contains(query))
    display_df = display_df[mask]

if selected_year != "All":
    display_df = display_df[display_df["Date"].dt.year == int(selected_year)]

if selected_month != "All":
    month_num = months.index(selected_month)
    display_df = display_df[display_df["Date"].dt.month == month_num]

# ==============================================
# 卡片顯示（一行 2 個）
# ==============================================
if len(display_df) > 0:
    sorted_df = display_df.sort_values(by="Date", ascending=False).reset_index(drop=True)

    for i in range(0, len(sorted_df), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(sorted_df):
                row = sorted_df.iloc[i + j]
                with cols[j]:
                    status_color = {"Quoting": "#ffaa00", "Confirmed": "#00aa00",
                                    "In Production": "#0066ff", "Completed": "#66cc66"}.get(row["Status"], "#888888")

                    work_order_text = f"Work Order: {row['Work_Order']}" if row["Work_Order"] else ""

                    manpower_records = manpower_df[manpower_df["Quote_Number"] == row["Quote_Number"]]
                    if len(manpower_records) > 0:
                        staff_names = [rec["Staff"].strip() for _, rec in manpower_records.iterrows()
                                       if rec["Staff"] and rec["Staff"].strip()]
                        manpower_text = "借調：" + "、".join(staff_names) if staff_names else "尚未借調"
                    else:
                        manpower_text = "尚未借調"

                    st.markdown(f"""
                    <div style="background: white; border-left: 6px solid {status_color}; border-radius: 10px; padding: 14px 16px; margin-bottom: 20px; box-shadow: 0 3px 10px rgba(0,0,0,0.08);">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                            <div style="flex: 1; min-width: 280px;">
                                <div style="font-weight: bold; font-size: 1.1rem; color: #1fb429;">
                                    Quote Number：{row['Quote_Number']}
                                </div>
                                <div style="font-size: 1.0rem; color: #333; margin-top: 4px;">
                                    {work_order_text}
                                </div>
                                <p style="margin:8px 0 0 0; font-size:0.9rem; color:#444; line-height:1.4;">
                                    {row['Project_Detail']}
                                </p>
                                <div style="font-size:0.85rem; color:#000; margin-top:8px; font-weight:500;">
                                    {manpower_text}
                                </div>
                            </div>
                            <div style="text-align: right; min-width:140px;">
                                <span style="background:{status_color}; color:white; padding:5px 14px; border-radius:18px; font-weight:bold; font-size:0.85rem;">
                                    {row['Status']}
                                </span>
                                <div style="margin-top:8px; color:#777; font-size:0.85rem;">
                                    建立日期：{row['Date'].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "—"}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Edit / Delete 按鈕
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Edit", key=f"edit_{row['Quote_Number']}_{i+j}", use_container_width=True):
                            st.session_state[f"edit_mode_{row['Quote_Number']}_{i+j}"] = True
                    with col2:
                        if st.button("Delete", key=f"del_proj_{row['Quote_Number']}_{i+j}", type="secondary", use_container_width=True):
                            st.session_state[f"confirm_del_{row['Quote_Number']}_{i+j}"] = True

                    # 編輯模式（你的原有邏輯，改成 gspread 更新）
                    if st.session_state.get(f"edit_mode_{row['Quote_Number']}_{i+j}", False):
                        original_idx = projects_df[projects_df["Quote_Number"] == row["Quote_Number"]].index[0]

                        st.markdown("### 現有借調記錄")
                        current_manpower = manpower_df[manpower_df["Quote_Number"] == row["Quote_Number"]].copy().reset_index(drop=True)
                        if len(current_manpower) > 0:
                            for m_idx, rec in current_manpower.iterrows():
                                if st.button(f"刪除借調：{rec['Staff']}", key=f"del_man_{row['Quote_Number']}_{i+j}_{m_idx}", type="secondary", use_container_width=True):
                                    manpower_df = manpower_df.drop(
                                        manpower_df[
                                            (manpower_df["Quote_Number"] == row["Quote_Number"]) &
                                            (manpower_df["Staff"] == rec["Staff"]) &
                                            (manpower_df["Start_Date"] == rec["Start_Date"])
                                        ].index
                                    ).reset_index(drop=True)
                                    worksheet_manpower.clear()
                                    worksheet_manpower.update([manpower_df.columns.values.tolist()] + manpower_df.values.tolist())
                                    st.success(f"已刪除借調：{rec['Staff']}")
                                    st.rerun()

                        with st.form(key=f"edit_form_{row['Quote_Number']}_{i+j}"):
                            new_quote = st.text_input("Quote Number", value=row["Quote_Number"])
                            new_work_order = st.text_input("Work Order", value=row["Work_Order"])
                            new_detail = st.text_area("Project Detail", value=row["Project_Detail"], height=120)
                            new_status = st.selectbox("Status", status_options, index=status_options.index(row["Status"]))

                            st.markdown("### 新增借調")
                            new_staff = st.text_input("員工姓名（新增借調）")
                            col_ns, col_ne = st.columns(2)
                            with col_ns:
                                new_start = st.date_input("開始日期", value=date.today(), key=f"ns_{row['Quote_Number']}_{i+j}")
                            with col_ne:
                                new_end = st.date_input("結束日期（留空表示進行中）", value=None, key=f"ne_{row['Quote_Number']}_{i+j}")

                            col_save, col_cancel = st.columns(2)
                            if col_save.form_submit_button("SAVE", type="primary", use_container_width=True):
                                # 更新專案資料
                                projects_df.at[original_idx, "Quote_Number"] = new_quote.strip()
                                projects_df.at[original_idx, "Work_Order"] = new_work_order.strip()
                                projects_df.at[original_idx, "Project_Detail"] = new_detail.strip()
                                projects_df.at[original_idx, "Status"] = new_status

                                worksheet_projects.clear()
                                worksheet_projects.update([projects_df.columns.values.tolist()] + projects_df.values.tolist())

                                if new_staff.strip():
                                    new_rec = pd.DataFrame([{
                                        "Quote_Number": new_quote.strip(),
                                        "Staff": new_staff.strip(),
                                        "Start_Date": new_start.strftime("%Y-%m-%d"),
                                        "End_Date": new_end.strftime("%Y-%m-%d") if new_end else ""
                                    }])
                                    manpower_df = pd.concat([manpower_df, new_rec], ignore_index=True)
                                    worksheet_manpower.clear()
                                    worksheet_manpower.update([manpower_df.columns.values.tolist()] + manpower_df.values.tolist())

                                st.success("專案與借調已更新！")
                                del st.session_state[f"edit_mode_{row['Quote_Number']}_{i+j}"]
                                st.rerun()

                            if col_cancel.form_submit_button("取消", use_container_width=True):
                                del st.session_state[f"edit_mode_{row['Quote_Number']}_{i+j}"]
                                st.rerun()

                    # 刪除專案確認
                    if st.session_state.get(f"confirm_del_{row['Quote_Number']}_{i+j}", False):
                        st.warning(f"確定要永久刪除專案 **{row['Quote_Number']}** 嗎？")
                        c1, c2 = st.columns(2)
                        if c1.button("確認刪除", type="primary", key=f"yes_del_{row['Quote_Number']}_{i+j}", use_container_width=True):
                            projects_df = projects_df[projects_df["Quote_Number"] != row["Quote_Number"]].reset_index(drop=True)
                            worksheet_projects.clear()
                            worksheet_projects.update([projects_df.columns.values.tolist()] + projects_df.values.tolist())

                            manpower_df = manpower_df[manpower_df["Quote_Number"] != row["Quote_Number"]].reset_index(drop=True)
                            worksheet_manpower.clear()
                            worksheet_manpower.update([manpower_df.columns.values.tolist()] + manpower_df.values.tolist())

                            st.success("專案及所有借調已刪除！")
                            st.rerun()
                        if c2.button("取消", key=f"no_del_{row['Quote_Number']}_{i+j}", use_container_width=True):
                            del st.session_state[f"confirm_del_{row['Quote_Number']}_{i+j}"]
                            st.rerun()

st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")