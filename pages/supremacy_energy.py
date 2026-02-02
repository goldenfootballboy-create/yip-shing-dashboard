import streamlit as st
import pandas as pd
from datetime import date
import time
import gspread
from google.oauth2.service_account import Credentials
import html

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
        break
    except gspread.exceptions.APIError as e:
        st.warning(f"連線失敗（嘗試 {attempt+1}/3）：{str(e)}，5 秒後重試...")
        time.sleep(5)
    except Exception as e:
        st.error(f"連線異常：{str(e)}")
        raise e

if spreadsheet is None:
    st.error("無法連線到 Google Sheets，請稍後再試或檢查 secrets.toml")
    st.stop()

worksheet_projects = spreadsheet.worksheet("supremacy_projects")
worksheet_manpower = spreadsheet.worksheet("supremacy_manpower")

# ==============================================
# 初始化 session_state 中的資料
# ==============================================
@st.cache_data(ttl=300)
def load_projects():
    try:
        data = worksheet_projects.get_all_records()
        df = pd.DataFrame(data)
        required_cols = ["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        df["Quote_Number"] = df["Quote_Number"].astype(str).str.replace(r"\.0$", "", regex=True)
        df["Work_Order"] = df["Work_Order"].fillna("").astype(str)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"讀取 supremacy_projects 失敗：{e}")
        return pd.DataFrame(columns=["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"])

@st.cache_data(ttl=300)
def load_manpower():
    try:
        data = worksheet_manpower.get_all_records()
        df = pd.DataFrame(data)
        required = ["Quote_Number", "Staff", "Start_Date", "End_Date"]
        for col in required:
            if col not in df.columns:
                df[col] = ""
        df["Quote_Number"] = df["Quote_Number"].astype(str).str.replace(r"\.0$", "", regex=True)
        df["Start_Date"] = pd.to_datetime(df["Start_Date"], errors="coerce")
        df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"讀取 supremacy_manpower 失敗：{e}")
        return pd.DataFrame(columns=["Quote_Number", "Staff", "Start_Date", "End_Date"])

if "projects_df" not in st.session_state:
    st.session_state.projects_df = load_projects()

if "manpower_df" not in st.session_state:
    st.session_state.manpower_df = load_manpower()

# ==============================================
# 儲存函數
# ==============================================
def save_projects():
    df_save = st.session_state.projects_df.copy()
    if "Date" in df_save.columns:
        df_save["Date"] = df_save["Date"].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "")
    worksheet_projects.clear()
    worksheet_projects.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    time.sleep(1.5)

def save_manpower():
    df_save = st.session_state.manpower_df.copy()
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
            elif quote_number.strip() in st.session_state.projects_df["Quote_Number"].values:
                st.error("此 Quote Number 已存在！")
            else:
                new_row = {
                    "Date": pd.to_datetime(project_date),
                    "Quote_Number": quote_number.strip(),
                    "Work_Order": work_order.strip(),
                    "Project_Detail": project_detail.strip(),
                    "Status": status
                }
                st.session_state.projects_df = pd.concat([
                    st.session_state.projects_df,
                    pd.DataFrame([new_row])
                ], ignore_index=True)
                save_projects()
                st.success(f"已新增專案：{quote_number}")
                st.rerun()

    st.markdown("---")
    st.markdown("### 🔍 搜尋專案")
    search_query = st.text_input("輸入 Quote Number 或 Work Order", key="supremacy_search", label_visibility="collapsed")
    if st.button("清除搜尋", type="secondary", use_container_width=True):
        st.session_state.supremacy_search = ""
        st.rerun()

    st.markdown("---")
    if st.button("📅 查看主日曆", type="primary", use_container_width=True):
        st.switch_page("pages/YipShing.py")

# ==============================================
# 主畫面
# ==============================================
st.title("SUPREMACY ENERGY")

# 搜尋過濾
display_df = st.session_state.projects_df.copy()
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

# 卡片顯示（一行 2 張卡片 + 安全顯示）
if len(display_df) > 0:
    sorted_df = display_df.sort_values(by="Date", ascending=False).reset_index(drop=True)
    cols = st.columns(2)

    for idx, row in sorted_df.iterrows():
        with cols[idx % 2]:
            # 先定義 key
            edit_key = f"edit_{idx}_{row['Quote_Number']}"
            del_key = f"del_proj_{idx}_{row['Quote_Number']}"
            edit_mode_key = f"edit_mode_{idx}_{row['Quote_Number']}"
            confirm_del_key = f"confirm_del_{idx}_{row['Quote_Number']}"

            status_color = {"Quoting": "#ffaa00", "Confirmed": "#00aa00",
                            "In Production": "#0066ff", "Completed": "#66cc66"}.get(row["Status"], "#888888")

            manpower_records = st.session_state.manpower_df[
                st.session_state.manpower_df["Quote_Number"] == row["Quote_Number"]
            ]
            if len(manpower_records) > 0:
                manpower_html = "<div style='margin-top:8px;'>"
                manpower_html += "<small style='color:#000; font-weight:bold;'>借調：</small><br>"
                for _, rec in manpower_records.iterrows():
                    start = rec["Start_Date"].strftime("%Y-%m-%d") if pd.notna(rec["Start_Date"]) else "—"
                    end = rec["End_Date"].strftime("%Y-%m-%d") if pd.notna(rec["End_Date"]) else "進行中"
                    manpower_html += f"<small style='color:#000;'>• {rec['Staff']} ({start} → {end})</small><br>"
                manpower_html += "</div>"
            else:
                manpower_html = "<div style='margin-top:8px; color:#999;'><small>無借調記錄</small></div>"

            date_str = row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "—"

            escaped_detail = html.escape(row["Project_Detail"].strip())  # 去除前後空白

            # 標題行：Quote Number + Status（右上角）
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                <h5 style="margin:0; color:#1fb429;">Quote Number：{row["Quote_Number"]}</h5>
                <span style="background:{status_color}; color:white; padding:4px 10px; border-radius:14px; font-weight:bold; font-size:0.85rem;">
                    {row["Status"]}
                </span>
            </div>
            <small style="color:#666; margin-bottom:8px; display:block;">Work Order: <strong>{row['Work_Order'] or '無'}</strong></small>
            """, unsafe_allow_html=True)

            # Project Detail（緊接上面，無空白）
            st.markdown(f"""
            <p style="margin:0 0 12px 0; font-size:1rem; color:#1e3a8a; line-height:1.6; white-space: pre-wrap;">
                {escaped_detail}
            </p>
            """, unsafe_allow_html=True)

            # 借調記錄（無分隔線）
            st.markdown(manpower_html, unsafe_allow_html=True)

            # 按鈕
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Edit", key=edit_key, use_container_width=True):
                    st.session_state[edit_mode_key] = True
            with col2:
                if st.button("Delete", key=del_key, type="secondary", use_container_width=True):
                    st.session_state[confirm_del_key] = True

            # 分隔線放在按鈕下面（每個項目結束後）
            st.markdown("---")

            # 編輯模式（保持原邏輯）
            if st.session_state.get(edit_mode_key, False):
                original_idx = st.session_state.projects_df[
                    st.session_state.projects_df["Quote_Number"] == row["Quote_Number"]
                ].index[0]

                st.markdown("### 現有借調記錄（可刪除）")
                current_manpower = st.session_state.manpower_df[
                    st.session_state.manpower_df["Quote_Number"] == row["Quote_Number"]
                ].copy().reset_index(drop=True)
                if len(current_manpower) > 0:
                    for m_idx, rec in current_manpower.iterrows():
                        del_man_key = f"del_man_{idx}_{row['Quote_Number']}_{m_idx}"
                        start_str = rec["Start_Date"].strftime("%Y-%m-%d") if pd.notna(rec["Start_Date"]) else "—"
                        if st.button(
                            f"刪除借調：{rec['Staff']} ({start_str})",
                            key=del_man_key, type="secondary", use_container_width=True
                        ):
                            st.session_state.manpower_df = st.session_state.manpower_df.drop(
                                st.session_state.manpower_df[
                                    (st.session_state.manpower_df["Quote_Number"] == row["Quote_Number"]) &
                                    (st.session_state.manpower_df["Staff"] == rec["Staff"]) &
                                    (st.session_state.manpower_df["Start_Date"] == rec["Start_Date"])
                                ].index
                            ).reset_index(drop=True)
                            save_manpower()
                            st.success(f"已刪除借調：{rec['Staff']}")
                            st.rerun()
                else:
                    st.info("尚未借調人員")

                with st.form(key=f"edit_form_{idx}_{row['Quote_Number']}"):
                    new_quote = st.text_input("Quote Number", value=row["Quote_Number"])
                    new_work_order = st.text_input("Work Order", value=row["Work_Order"])
                    new_detail = st.text_area("Project Detail", value=row["Project_Detail"], height=120)
                    new_status = st.selectbox("Status", status_options, index=status_options.index(row["Status"]))

                    st.markdown("### 新增借調")
                    new_staff = st.text_input("員工姓名（新增借調）")
                    col_ns, col_ne = st.columns(2)
                    with col_ns:
                        new_start = st.date_input("開始日期", value=date.today(), key=f"ns_{idx}_{row['Quote_Number']}")
                    with col_ne:
                        new_end = st.date_input("結束日期（留空表示進行中）", value=None, key=f"ne_{idx}_{row['Quote_Number']}")

                    col_save, col_cancel = st.columns(2)
                    if col_save.form_submit_button("SAVE", type="primary", use_container_width=True):
                        st.session_state.projects_df.at[original_idx, "Quote_Number"] = new_quote.strip()
                        st.session_state.projects_df.at[original_idx, "Work_Order"] = new_work_order.strip()
                        st.session_state.projects_df.at[original_idx, "Project_Detail"] = new_detail.strip()
                        st.session_state.projects_df.at[original_idx, "Status"] = new_status
                        save_projects()

                        if new_staff.strip():
                            new_rec = {
                                "Quote_Number": new_quote.strip(),
                                "Staff": new_staff.strip(),
                                "Start_Date": pd.to_datetime(new_start),
                                "End_Date": pd.to_datetime(new_end) if new_end else pd.NaT
                            }
                            st.session_state.manpower_df = pd.concat([
                                st.session_state.manpower_df,
                                pd.DataFrame([new_rec])
                            ], ignore_index=True)
                            save_manpower()

                        st.success("專案與借調已更新！")
                        if edit_mode_key in st.session_state:
                            del st.session_state[edit_mode_key]
                        st.rerun()

                    if col_cancel.form_submit_button("取消", use_container_width=True):
                        if edit_mode_key in st.session_state:
                            del st.session_state[edit_mode_key]
                        st.rerun()

            # 刪除確認
            if st.session_state.get(confirm_del_key, False):
                st.warning(f"確定要永久刪除專案 **{row['Quote_Number']}** 嗎？（包含所有借調記錄）")
                c1, c2 = st.columns(2)
                if c1.button("確認刪除", type="primary", key=f"yes_del_{idx}_{row['Quote_Number']}", use_container_width=True):
                    st.session_state.projects_df = st.session_state.projects_df[
                        st.session_state.projects_df["Quote_Number"] != row["Quote_Number"]
                    ].reset_index(drop=True)
                    save_projects()
                    st.session_state.manpower_df = st.session_state.manpower_df[
                        st.session_state.manpower_df["Quote_Number"] != row["Quote_Number"]
                    ].reset_index(drop=True)
                    save_manpower()
                    st.success("專案及所有借調已刪除！")
                    if confirm_del_key in st.session_state:
                        del st.session_state[confirm_del_key]
                    st.rerun()
                if c2.button("取消", key=f"no_del_{idx}_{row['Quote_Number']}", use_container_width=True):
                    if confirm_del_key in st.session_state:
                        del st.session_state[confirm_del_key]
                    st.rerun()

else:
    st.info("尚未新增任何副業專案" if not search_query else "無搜尋結果")

st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")