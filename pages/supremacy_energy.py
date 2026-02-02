import streamlit as st
import pandas as pd
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials


# ==============================================
# 輔助函數：安全轉換 DataFrame 給 gspread
# ==============================================
def df_to_gspread_values(df):
    """將 pandas DataFrame 轉成 gspread 可接受的純 Python 值列表"""
    values = [df.columns.tolist()]  # 標頭

    for _, row in df.iterrows():
        row_list = []
        for val in row:
            if pd.isna(val):  # 處理 NaN, NaT, None
                row_list.append("")
            elif isinstance(val, (pd.Timestamp, datetime.date, datetime.datetime)):
                row_list.append(val.strftime("%Y-%m-%d"))
            else:
                row_list.append(str(val) if val is not None else "")
        values.append(row_list)

    return values


# ==============================================
# 頁面設定
# ==============================================
st.set_page_config(
    page_title="SUPREMACY ENERGY",
    page_icon="https://i.imgur.com/Q8ehtk3.jpeg",
    layout="wide"
)


# ==============================================
# Google Sheets 連線
# ==============================================
@st.cache_resource(show_spinner="正在連線 Google Sheets...", ttl=1800)
def get_spreadsheet():
    creds_info = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)

    spreadsheet_id = creds_info.get("spreadsheet", "").strip()
    if not spreadsheet_id:
        st.error("secrets 中缺少 'spreadsheet'（試算表 ID）")
        st.stop()
    if len(spreadsheet_id) != 44:
        st.error("Spreadsheet ID 長度不正確（應為 44 個字元）")
        st.info(f"讀到的值：{spreadsheet_id}")
        st.stop()
    if spreadsheet_id.count("-") not in [0, 4]:
        st.warning("Spreadsheet ID 連字號數量不尋常，但仍嘗試連線...")

    try:
        return client.open_by_key(spreadsheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("找不到該試算表")
        st.info(f"ID：{spreadsheet_id}")
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
    st.stop()

# 欄位處理（空表補標頭）
if projects_df.empty or len(projects_df.columns) < 5:
    header = ["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"]
    projects_df = pd.DataFrame(columns=header)
    worksheet_projects.update([header])

if manpower_df.empty or len(manpower_df.columns) < 4:
    header_man = ["Quote_Number", "Staff", "Start_Date", "End_Date"]
    manpower_df = pd.DataFrame(columns=header_man)
    worksheet_manpower.update([header_man])

# 資料清理 - 強制轉字串，避免 Timestamp 問題
projects_df["Quote_Number"] = projects_df["Quote_Number"].astype(str).str.replace(r"\.0$", "", regex=True)
projects_df["Work_Order"] = projects_df["Work_Order"].fillna("").astype(str)
projects_df["Date"] = pd.to_datetime(projects_df["Date"], errors="coerce").apply(
    lambda x: x.strftime("%Y-%m-%d") if pd.notnull(x) else ""
)
projects_df = projects_df.fillna("")

manpower_df["Quote_Number"] = manpower_df["Quote_Number"].astype(str).str.replace(r"\.0$", "", regex=True)
manpower_df = manpower_df.fillna("")

# ==============================================
# Sidebar
# ==============================================
with st.sidebar:
    st.header("SUPREMACY ENERGY")

    st.markdown("### Filters")
    years = sorted(set(int(x[:4]) for x in projects_df["Date"] if x and len(x) >= 4), reverse=True)
    if 2025 not in years:
        years = [2025] + years
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

                current_projects = pd.DataFrame(worksheet_projects.get_all_records())
                if not current_projects.empty and str(current_projects.iloc[0, 0]).strip().lower() in ["date", "日期"]:
                    current_projects = current_projects.iloc[1:].reset_index(drop=True)

                updated_projects = pd.concat([current_projects, new_row], ignore_index=True)
                # worksheet_projects.clear()  # 暫時註解，避免意外清空
                worksheet_projects.update(df_to_gspread_values(updated_projects))

                st.success(f"已新增專案：{quote_number}")
                st.rerun()

    st.markdown("---")

    st.markdown("### 🔍 搜尋專案")
    search_query = st.text_input("輸入 Quote Number 或 Work Order", key="supremacy_search",
                                 label_visibility="collapsed")
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
    display_df = display_df[display_df["Date"].str.startswith(str(selected_year))]

if selected_month != "All":
    month_num = months.index(selected_month)
    display_df = display_df[display_df["Date"].str[5:7] == f"{month_num:02d}"]

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
                    staff_names = [rec["Staff"].strip() for _, rec in manpower_records.iterrows() if
                                   rec["Staff"] and rec["Staff"].strip()]
                    manpower_text = "借調：" + "、".join(staff_names) if staff_names else "尚未借調"

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
                                    建立日期：{row['Date'] if row['Date'] else "—"}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Edit / Delete 按鈕
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Edit", key=f"edit_{row['Quote_Number']}_{i + j}", use_container_width=True):
                            st.session_state[f"edit_mode_{row['Quote_Number']}_{i + j}"] = True
                    with col2:
                        if st.button("Delete", key=f"del_proj_{row['Quote_Number']}_{i + j}", type="secondary",
                                     use_container_width=True):
                            st.session_state[f"confirm_del_{row['Quote_Number']}_{i + j}"] = True

                    # 編輯模式
                    if st.session_state.get(f"edit_mode_{row['Quote_Number']}_{i + j}", False):
                        original_idx = projects_df[projects_df["Quote_Number"] == row["Quote_Number"]].index[0]

                        st.markdown("### 現有借調記錄")
                        current_manpower = manpower_df[
                            manpower_df["Quote_Number"] == row["Quote_Number"]].copy().reset_index(drop=True)
                        if len(current_manpower) > 0:
                            for m_idx, rec in current_manpower.iterrows():
                                if st.button(f"刪除借調：{rec['Staff']}",
                                             key=f"del_man_{row['Quote_Number']}_{i + j}_{m_idx}", type="secondary",
                                             use_container_width=True):
                                    manpower_df = manpower_df.drop(
                                        manpower_df[
                                            (manpower_df["Quote_Number"] == row["Quote_Number"]) &
                                            (manpower_df["Staff"] == rec["Staff"]) &
                                            (manpower_df["Start_Date"] == rec["Start_Date"])
                                            ].index
                                    ).reset_index(drop=True)
                                    # worksheet_manpower.clear()  # 暫時註解
                                    worksheet_manpower.update(df_to_gspread_values(manpower_df))
                                    st.success(f"已刪除借調：{rec['Staff']}")
                                    st.rerun()

                        with st.form(key=f"edit_form_{row['Quote_Number']}_{i + j}"):
                            new_quote = st.text_input("Quote Number", value=row["Quote_Number"])
                            new_work_order = st.text_input("Work Order", value=row["Work_Order"])
                            new_detail = st.text_area("Project Detail", value=row["Project_Detail"], height=120)
                            new_status = st.selectbox("Status", status_options,
                                                      index=status_options.index(row["Status"]))

                            st.markdown("### 新增借調")
                            new_staff = st.text_input("員工姓名（新增借調）")
                            col_ns, col_ne = st.columns(2)
                            with col_ns:
                                new_start = st.date_input("開始日期", value=date.today(),
                                                          key=f"ns_{row['Quote_Number']}_{i + j}")
                            with col_ne:
                                new_end = st.date_input("結束日期（留空表示進行中）", value=None,
                                                        key=f"ne_{row['Quote_Number']}_{i + j}")

                            col_save, col_cancel = st.columns(2)
                            if col_save.form_submit_button("SAVE", type="primary", use_container_width=True):
                                projects_df.at[original_idx, "Quote_Number"] = new_quote.strip()
                                projects_df.at[original_idx, "Work_Order"] = new_work_order.strip()
                                projects_df.at[original_idx, "Project_Detail"] = new_detail.strip()
                                projects_df.at[original_idx, "Status"] = new_status

                                # worksheet_projects.clear()  # 暫時註解
                                worksheet_projects.update(df_to_gspread_values(projects_df))

                                if new_staff.strip():
                                    new_rec = pd.DataFrame([{
                                        "Quote_Number": new_quote.strip(),
                                        "Staff": new_staff.strip(),
                                        "Start_Date": new_start.strftime("%Y-%m-%d"),
                                        "End_Date": new_end.strftime("%Y-%m-%d") if new_end else ""
                                    }])
                                    manpower_df = pd.concat([manpower_df, new_rec], ignore_index=True)
                                    # worksheet_manpower.clear()  # 暫時註解
                                    worksheet_manpower.update(df_to_gspread_values(manpower_df))

                                st.success("專案與借調已更新！")
                                if f"edit_mode_{row['Quote_Number']}_{i + j}" in st.session_state:
                                    del st.session_state[f"edit_mode_{row['Quote_Number']}_{i + j}"]
                                st.rerun()

                            if col_cancel.form_submit_button("取消", use_container_width=True):
                                if f"edit_mode_{row['Quote_Number']}_{i + j}" in st.session_state:
                                    del st.session_state[f"edit_mode_{row['Quote_Number']}_{i + j}"]
                                st.rerun()

                    # 刪除專案確認
                    if st.session_state.get(f"confirm_del_{row['Quote_Number']}_{i + j}", False):
                        st.warning(f"確定要永久刪除專案 **{row['Quote_Number']}** 嗎？")
                        c1, c2 = st.columns(2)
                        if c1.button("確認刪除", type="primary", key=f"yes_del_{row['Quote_Number']}_{i + j}",
                                     use_container_width=True):
                            projects_df = projects_df[projects_df["Quote_Number"] != row["Quote_Number"]].reset_index(
                                drop=True)
                            manpower_df = manpower_df[manpower_df["Quote_Number"] != row["Quote_Number"]].reset_index(
                                drop=True)

                            try:
                                # worksheet_projects.clear()  # 暫時註解，避免清空
                                worksheet_projects.update(df_to_gspread_values(projects_df))
                                # worksheet_manpower.clear()
                                worksheet_manpower.update(df_to_gspread_values(manpower_df))
                                st.success("專案及所有借調已刪除！")
                            except Exception as e:
                                st.error(f"寫入 Google Sheet 失敗：{str(e)}")
                                st.warning("資料未更新，但 Sheet 未被清空，請檢查後重試")
                            st.rerun()
                        if c2.button("取消", key=f"no_del_{row['Quote_Number']}_{i + j}", use_container_width=True):
                            if f"confirm_del_{row['Quote_Number']}_{i + j}" in st.session_state:
                                del st.session_state[f"confirm_del_{row['Quote_Number']}_{i + j}"]
                            st.rerun()

st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")