import streamlit as st
import pandas as pd
from datetime import date
import time
import gspread
from google.oauth2.service_account import Credentials

# ==============================================
# 頁面設定
# ==============================================
st.set_page_config(
    page_title="SUPREMACY ENERGY - 副業專案管理",
    page_icon="https://i.imgur.com/Q8ehtk3.jpeg",
    layout="wide"
)

# ==============================================
# Google Sheets 連線（與 Yip Shing Dashboard 完全相同方式）
# ==============================================
creds_info = st.secrets["connections"]["gsheets"]
creds = Credentials.from_service_account_info(
    creds_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
client = gspread.authorize(creds)

spreadsheet = None
for attempt in range(3):
    try:
        spreadsheet_id = creds_info["spreadsheet"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        # st.success("連線成功！Spreadsheet 名稱：" + spreadsheet.title)  # 正式上線可註解掉
        break
    except gspread.exceptions.APIError as e:
        st.warning(f"連線失敗（嘗試 {attempt + 1}/3）：{str(e)}，5 秒後重試...")
        time.sleep(5)
    except Exception as e:
        st.error(f"連線異常：{str(e)}")
        raise e

if spreadsheet is None:
    st.error("無法連線到 Google Sheets，請稍後再試或檢查 secrets.toml")
    st.stop()

# 取得工作表
worksheet_projects = spreadsheet.worksheet("supremacy_projects")
worksheet_manpower = spreadsheet.worksheet("supremacy_manpower")

# ==============================================
# 讀取 supremacy_projects
# ==============================================
try:
    data = worksheet_projects.get_all_records()
    projects_df = pd.DataFrame(data)

    # 確保必要欄位存在
    required_cols = ["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"]
    for col in required_cols:
        if col not in projects_df.columns:
            projects_df[col] = ""

    # 清理 Quote_Number（移除可能的 .0）
    projects_df["Quote_Number"] = projects_df["Quote_Number"].astype(str).str.replace(r"\.0$", "", regex=True)
    projects_df["Work_Order"] = projects_df["Work_Order"].fillna("").astype(str)

    # 日期欄位轉 datetime
    projects_df["Date"] = pd.to_datetime(projects_df["Date"], errors="coerce")

except Exception as e:
    st.error(f"讀取 supremacy_projects 失敗：{e}")
    projects_df = pd.DataFrame(columns=["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"])

# ==============================================
# 讀取 supremacy_manpower
# ==============================================
try:
    manpower_data = worksheet_manpower.get_all_records()
    manpower_df = pd.DataFrame(manpower_data)

    required_manpower = ["Quote_Number", "Staff", "Start_Date", "End_Date"]
    for col in required_manpower:
        if col not in manpower_df.columns:
            manpower_df[col] = ""

    manpower_df["Quote_Number"] = manpower_df["Quote_Number"].astype(str).str.replace(r"\.0$", "", regex=True)
    manpower_df["Start_Date"] = pd.to_datetime(manpower_df["Start_Date"], errors="coerce")
    manpower_df["End_Date"] = pd.to_datetime(manpower_df["End_Date"], errors="coerce")

except Exception as e:
    st.error(f"讀取 supremacy_manpower 失敗：{e}")
    manpower_df = pd.DataFrame(columns=["Quote_Number", "Staff", "Start_Date", "End_Date"])


# ==============================================
# 儲存函數
# ==============================================
def save_projects():
    df_save = projects_df.copy()
    if "Date" in df_save.columns:
        df_save["Date"] = df_save["Date"].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "")
    worksheet_projects.clear()
    worksheet_projects.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    time.sleep(1.5)


def save_manpower():
    df_save = manpower_df.copy()
    for col in ["Start_Date", "End_Date"]:
        if col in df_save.columns:
            df_save[col] = df_save[col].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "")
    worksheet_manpower.clear()
    worksheet_manpower.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    time.sleep(1.5)


# ==============================================
# Sidebar
# ==============================================
with st.sidebar:
    st.header("SUPREMACY ENERGY")

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
            elif quote_number.strip() in projects_df["Quote_Number"].values:
                st.error("此 Quote Number 已存在！")
            else:
                new_row = {
                    "Date": project_date,
                    "Quote_Number": quote_number.strip(),
                    "Work_Order": work_order.strip(),
                    "Project_Detail": project_detail.strip(),
                    "Status": status
                }
                global projects_df
                projects_df = pd.concat([projects_df, pd.DataFrame([new_row])], ignore_index=True)
                save_projects()
                st.success(f"已新增專案：{quote_number}")
                st.rerun()

    st.markdown("---")
    st.markdown("### 🔍 搜尋專案")
    search_query = st.text_input("輸入 Quote Number 或 Work Order", key="supremacy_search",
                                 label_visibility="collapsed")
    if st.button("清除搜尋", type="secondary", use_container_width=True):
        st.session_state.supremacy_search = ""
        st.rerun()

    st.markdown("---")
    if st.button("📅 查看主日曆", type="primary", use_container_width=True):
        # 如果您有使用多頁面功能，請改成正確的頁面名稱
        st.switch_page("pages/YipShing.py")  # 依實際檔案路徑調整

# ==============================================
# 主畫面標題
# ==============================================
st.title("SUPREMACY ENERGY - 副業專案管理")

# ==============================================
# 搜尋過濾
# ==============================================
display_df = projects_df.copy()
if search_query:
    query = search_query.strip().lower()
    mask = (
            display_df["Quote_Number"].astype(str).str.lower().str.contains(query) |
            display_df["Work_Order"].astype(str).str.lower().str.contains(query)
    )
    display_df = display_df[mask].reset_index(drop=True)
    if len(display_df) > 0:
        st.success(f"找到 {len(display_df)} 個符合的專案")
    else:
        st.info("無搜尋結果")

# ==============================================
# 卡片顯示
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

            work_order_display = (
                f"<br><small style='color:#666;'>Work Order: <strong>{row['Work_Order'] or '無'}</strong></small>"
                if row["Work_Order"] else ""
            )

            manpower_records = manpower_df[manpower_df["Quote_Number"] == row["Quote_Number"]]
            if len(manpower_records) > 0:
                manpower_html = "<div style='margin-top:12px; padding-top:12px; border-top:1px solid #eee;'>"
                manpower_html += "<small style='color:#000; font-weight:bold;'>借調：</small><br>"
                for _, rec in manpower_records.iterrows():
                    start = rec["Start_Date"].strftime("%Y-%m-%d") if pd.notna(rec["Start_Date"]) else "—"
                    end = rec["End_Date"].strftime("%Y-%m-%d") if pd.notna(rec["End_Date"]) else "進行中"
                    manpower_html += f"<small style='color:#000;'>• {rec['Staff']} ({start} → {end})</small><br>"
                manpower_html += "</div>"
            else:
                manpower_html = "<div style='margin-top:12px; padding-top:12px; border-top:1px solid #eee; color:#999;'><small>無借調記錄</small></div>"

            date_str = row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "—"

            st.markdown(f"""
            <div style="background: white; border-left: 5px solid {status_color}; border-radius: 12px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); min-height: 260px;">
                <div>
                    <h5 style="margin:0 0 8px 0; color:#1fb429;">{row["Quote_Number"]}</h5>
                    {work_order_display}
                    <p style="margin:16px 0 0 0; font-size:1rem; color:#333; line-height:1.6;">{row["Project_Detail"]}</p>
                </div>
                <div>{manpower_html}</div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:20px;">
                    <span style="background:{status_color}; color:white; padding:6px 16px; border-radius:20px; font-weight:bold;">
                        {row["Status"]}
                    </span>
                    <small style="color:#888;">{date_str}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Edit", key=f"edit_{row['Quote_Number']}", use_container_width=True):
                    st.session_state[f"edit_mode_{row['Quote_Number']}"] = True
            with col2:
                if st.button("Delete", key=f"del_proj_{row['Quote_Number']}", type="secondary",
                             use_container_width=True):
                    st.session_state[f"confirm_del_{row['Quote_Number']}"] = True

            # ================ 編輯模式 ================
            if st.session_state.get(f"edit_mode_{row['Quote_Number']}", False):
                original_idx = projects_df[projects_df["Quote_Number"] == row["Quote_Number"]].index[0]

                st.markdown("### 現有借調記錄（可刪除）")
                current_manpower = manpower_df[manpower_df["Quote_Number"] == row["Quote_Number"]].copy().reset_index(
                    drop=True)
                if len(current_manpower) > 0:
                    for m_idx, rec in current_manpower.iterrows():
                        if st.button(f"刪除借調：{rec['Staff']} ({rec['Start_Date'].strftime('%Y-%m-%d')})",
                                     key=f"del_man_{row['Quote_Number']}_{m_idx}", type="secondary",
                                     use_container_width=True):
                            manpower_df = manpower_df.drop(
                                manpower_df[
                                    (manpower_df["Quote_Number"] == row["Quote_Number"]) &
                                    (manpower_df["Staff"] == rec["Staff"]) &
                                    (manpower_df["Start_Date"] == rec["Start_Date"])
                                    ].index
                            ).reset_index(drop=True)
                            save_manpower()
                            st.success(f"已刪除借調：{rec['Staff']}")
                            st.rerun()
                else:
                    st.info("尚未借調人員")

                # 專案編輯表單
                with st.form(key=f"edit_form_{row['Quote_Number']}"):
                    new_quote = st.text_input("Quote Number", value=row["Quote_Number"])
                    new_work_order = st.text_input("Work Order", value=row["Work_Order"])
                    new_detail = st.text_area("Project Detail", value=row["Project_Detail"], height=120)
                    new_status = st.selectbox("Status", status_options, index=status_options.index(row["Status"]))

                    st.markdown("### 新增借調")
                    new_staff = st.text_input("員工姓名（新增借調）")
                    col_ns, col_ne = st.columns(2)
                    with col_ns:
                        new_start = st.date_input("開始日期", value=date.today(), key=f"ns_{row['Quote_Number']}")
                    with col_ne:
                        new_end = st.date_input("結束日期（留空表示進行中）", value=None, key=f"ne_{row['Quote_Number']}")

                    col_save, col_cancel = st.columns(2)
                    if col_save.form_submit_button("SAVE", type="primary", use_container_width=True):
                        projects_df.at[original_idx, "Quote_Number"] = new_quote.strip()
                        projects_df.at[original_idx, "Work_Order"] = new_work_order.strip()
                        projects_df.at[original_idx, "Project_Detail"] = new_detail.strip()
                        projects_df.at[original_idx, "Status"] = new_status
                        save_projects()

                        if new_staff.strip():
                            new_rec = {
                                "Quote_Number": new_quote.strip(),
                                "Staff": new_staff.strip(),
                                "Start_Date": new_start,
                                "End_Date": new_end if new_end else pd.NaT
                            }
                            global manpower_df
                            manpower_df = pd.concat([manpower_df, pd.DataFrame([new_rec])], ignore_index=True)
                            save_manpower()

                        st.success("專案與借調已更新！")
                        del st.session_state[f"edit_mode_{row['Quote_Number']}"]
                        st.rerun()

                    if col_cancel.form_submit_button("取消", use_container_width=True):
                        del st.session_state[f"edit_mode_{row['Quote_Number']}"]
                        st.rerun()

            # ================ 刪除專案確認 ================
            if st.session_state.get(f"confirm_del_{row['Quote_Number']}", False):
                st.warning(f"確定要永久刪除專案 **{row['Quote_Number']}** 嗎？（包含所有借調記錄）")
                c1, c2 = st.columns(2)
                if c1.button("確認刪除", type="primary", key=f"yes_del_{row['Quote_Number']}",
                             use_container_width=True):
                    projects_df = projects_df[projects_df["Quote_Number"] != row["Quote_Number"]].reset_index(drop=True)
                    save_projects()
                    manpower_df = manpower_df[manpower_df["Quote_Number"] != row["Quote_Number"]].reset_index(drop=True)
                    save_manpower()
                    st.success("專案及所有借調已刪除！")
                    st.rerun()
                if c2.button("取消", key=f"no_del_{row['Quote_Number']}", use_container_width=True):
                    del st.session_state[f"confirm_del_{row['Quote_Number']}"]
                    st.rerun()

else:
    st.info("尚未新增任何副業專案" if not search_query else "無搜尋結果")

st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")