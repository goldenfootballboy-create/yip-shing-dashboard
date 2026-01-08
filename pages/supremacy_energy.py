import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ==============================================
# 頁面設定
# ==============================================
st.set_page_config(
    page_title="SUPREMACY ENERGY",
    page_icon="https://i.imgur.com/Q8ehtk3.jpeg",
    layout="wide"
)

# ==============================================
# Google Sheets 連接
# ==============================================
conn = st.connection("gsheets", type=GSheetsConnection)

# ==============================================
# 讀取 supremacy_projects
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
        projects_df["Work_Order"] = projects_df["Work_Order"].fillna("").astype(str)
        # 關鍵：轉換 Date 為 datetime 以支援 .dt.year / .dt.month
        projects_df["Date"] = pd.to_datetime(projects_df["Date"], errors="coerce")
except Exception:
    projects_df = pd.DataFrame(columns=["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"])

# ==============================================
# 讀取 supremacy_manpower
# ==============================================
try:
    manpower_raw = conn.read(worksheet="supremacy_manpower", ttl=300)
    if manpower_raw.empty or len(manpower_raw.columns) < 4:
        manpower_df = pd.DataFrame(columns=["Quote_Number", "Staff", "Start_Date", "End_Date"])
    else:
        if len(manpower_raw) > 0 and str(manpower_raw.iloc[0,0]).strip().lower() in ["quote_number", "quote number", "報價單號"]:
            manpower_raw = manpower_raw.iloc[1:].reset_index(drop=True)
        manpower_raw.columns = ["Quote_Number", "Staff", "Start_Date", "End_Date"][:len(manpower_raw.columns)]
        manpower_raw["Quote_Number"] = manpower_raw["Quote_Number"].astype(str).str.replace(".0", "", regex=False)
        manpower_df = manpower_raw.copy()
except Exception:
    manpower_df = pd.DataFrame(columns=["Quote_Number", "Staff", "Start_Date", "End_Date"])

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
                st.success(f"已新增專案：{quote_number}")
                st.rerun()

    st.markdown("---")

    # === Filter by Date ===
    st.markdown("### 📅 Filter by Date")

    # 年份選項（自動取得 + 加入 2025）
    years = sorted(projects_df["Date"].dt.year.dropna().unique(), reverse=True)
    years = list(years) + [2025] if 2025 not in years else list(years)
    selected_year = st.selectbox("Year", ["All"] + years, index=0, key="filter_year")

    # 月份選項
    months = ["All", "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    selected_month = st.selectbox("Month", months, index=0, key="filter_month")

    st.markdown("---")

    # === Search Projects ===
    st.markdown("### 🔍 Search Projects")
    search_query = st.text_input("Enter Quote Number or Work Order", key="supremacy_search", label_visibility="collapsed")
    if st.button("Clear Search", type="secondary", use_container_width=True):
        if "supremacy_search" in st.session_state:
            del st.session_state.supremacy_search
        st.rerun()

    st.markdown("---")

# ==============================================
# 主畫面標題
# ==============================================
st.title("SUPREMACY ENERGY")

# ==============================================
# 搜尋 + 年月篩選（現在會生效）
# ==============================================
display_df = projects_df.copy()

# 搜尋
if search_query:
    query = search_query.strip().lower()
    mask = (display_df["Quote_Number"].str.lower().str.contains(query) |
            display_df["Work_Order"].str.lower().str.contains(query))
    display_df = display_df[mask]

# 年份篩選
if st.session_state.get("filter_year") != "All":
    selected_year = st.session_state["filter_year"]
    display_df = display_df[display_df["Date"].dt.year == selected_year]

# 月份篩選
if st.session_state.get("filter_month") != "All":
    selected_month = st.session_state["filter_month"]
    month_num = months.index(selected_month)
    display_df = display_df[display_df["Date"].dt.month == month_num]

# 顯示結果數量
if len(display_df) > 0:
    st.success(f"Found {len(display_df)} matching projects")
else:
    st.info("No projects found")

# ==============================================
# 長條卡片顯示
# ==============================================
if len(display_df) > 0:
    sorted_df = display_df.sort_values(by="Date", ascending=False).reset_index(drop=True)

    for _, row in sorted_df.iterrows():
        status_color = {"Quoting": "#ffaa00", "Confirmed": "#00aa00",
                        "In Production": "#0066ff", "Completed": "#66cc66"}.get(row["Status"], "#888888")

        # Quote Number 和 Work Order 並排
        quote_line = f"<div style='font-weight: bold; font-size: 1.1rem; color: #1fb429;'>Quote Number：{row['Quote_Number']}</div>"
        work_order_line = f"<div style='font-size: 1.0rem; color: #333;'>Work Order：{row['Work_Order'] or '無'}</div>"

        # 借調顯示人名
        manpower_records = manpower_df[manpower_df["Quote_Number"] == row["Quote_Number"]]
        if len(manpower_records) > 0:
            staff_names = [rec["Staff"].strip() for rec in manpower_records.itertuples() if rec.Staff and rec.Staff.strip()]
            manpower_text = "借調：" + "、".join(staff_names) if staff_names else "尚未借調"
        else:
            manpower_text = "尚未借調"

        # 右側狀態與日期
        right_section = f"""
        <div style="text-align: right; min-width: 140px;">
            <span style="background:{status_color}; color:white; padding:5px 14px; border-radius:18px; font-weight:bold; font-size:0.85rem;">
                {row["Status"]}
            </span>
            <div style="margin-top: 8px; color:#777; font-size:0.85rem;">
                建立日期：{row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "—"}
            </div>
        </div>
        """

        # 長條卡片
        st.markdown(f"""
        <div style="background: white; border-left: 6px solid {status_color}; border-radius: 12px; padding: 18px 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 15px;">
            <div style="flex: 1;">
                <div style="display: flex; flex-wrap: wrap; gap: 20px; align-items: baseline; margin-bottom: 10px;">
                    {quote_line}
                    {work_order_line}
                </div>
                <p style="margin: 10px 0 0 0; font-size: 0.95rem; color: #444; line-height: 1.5;">
                    {row['Project_Detail']}
                </p>
                <div style="font-size: 0.9rem; color: #000; margin-top: 10px; font-weight: 500;">
                    {manpower_text}
                </div>
            </div>
            {right_section}
        </div>
        """, unsafe_allow_html=True)

        # Edit / Delete 按鈕
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Edit", key=f"edit_{row['Quote_Number']}", use_container_width=True):
                st.session_state[f"edit_mode_{row['Quote_Number']}"] = True
        with col2:
            if st.button("Delete", key=f"del_proj_{row['Quote_Number']}", type="secondary", use_container_width=True):
                st.session_state[f"confirm_del_{row['Quote_Number']}"] = True
            # ================ 編輯模式 ================
            if st.session_state.get(f"edit_mode_{row['Quote_Number']}", False):
                original_idx = projects_df[projects_df["Quote_Number"] == row["Quote_Number"]].index[0]

                st.markdown("### 現有借調記錄")
                current_manpower = manpower_df[manpower_df["Quote_Number"] == row["Quote_Number"]].copy().reset_index(drop=True)
                if len(current_manpower) > 0:
                    for m_idx, rec in current_manpower.iterrows():
                        if st.button(f"刪除借調：{rec['Staff']}", key=f"del_man_{row['Quote_Number']}_{m_idx}", type="secondary", use_container_width=True):
                            # 刪除該筆借調
                            manpower_df = manpower_df.drop(
                                manpower_df[
                                    (manpower_df["Quote_Number"] == row["Quote_Number"]) &
                                    (manpower_df["Staff"] == rec["Staff"]) &
                                    (manpower_df["Start_Date"] == rec["Start_Date"])
                                ].index
                            ).reset_index(drop=True)
                            conn.update(worksheet="supremacy_manpower", data=manpower_df)

                            # 強制刷新最新資料
                            latest_manpower = conn.read(worksheet="supremacy_manpower", ttl=0)
                            if not latest_manpower.empty and str(latest_manpower.iloc[0,0]).strip().lower() in ["quote_number", "quote number", "報價單號"]:
                                latest_manpower = latest_manpower.iloc[1:].reset_index(drop=True)
                            if not latest_manpower.empty:
                                latest_manpower.columns = ["Quote_Number", "Staff", "Start_Date", "End_Date"][:len(latest_manpower.columns)]
                                latest_manpower["Quote_Number"] = latest_manpower["Quote_Number"].astype(str).str.replace(".0", "", regex=False)
                            manpower_df = latest_manpower.copy() if not latest_manpower.empty else pd.DataFrame(columns=["Quote_Number", "Staff", "Start_Date", "End_Date"])

                            st.success(f"已刪除借調：{rec['Staff']}")
                            st.rerun()

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
                        conn.update(worksheet="supremacy_projects", data=projects_df)

                        if new_staff.strip():
                            new_rec = pd.DataFrame([{
                                "Quote_Number": new_quote.strip(),
                                "Staff": new_staff.strip(),
                                "Start_Date": new_start.strftime("%Y-%m-%d"),
                                "End_Date": new_end.strftime("%Y-%m-%d") if new_end else ""
                            }])
                            manpower_df = pd.concat([manpower_df, new_rec], ignore_index=True)
                            conn.update(worksheet="supremacy_manpower", data=manpower_df)

                            # 強制刷新
                            latest_manpower = conn.read(worksheet="supremacy_manpower", ttl=0)
                            if not latest_manpower.empty and str(latest_manpower.iloc[0,0]).strip().lower() in ["quote_number", "quote number", "報價單號"]:
                                latest_manpower = latest_manpower.iloc[1:].reset_index(drop=True)
                            if not latest_manpower.empty:
                                latest_manpower.columns = ["Quote_Number", "Staff", "Start_Date", "End_Date"][:len(latest_manpower.columns)]
                                latest_manpower["Quote_Number"] = latest_manpower["Quote_Number"].astype(str).str.replace(".0", "", regex=False)
                            manpower_df = latest_manpower.copy() if not latest_manpower.empty else pd.DataFrame(columns=["Quote_Number", "Staff", "Start_Date", "End_Date"])

                        st.success("專案與借調已更新！")
                        del st.session_state[f"edit_mode_{row['Quote_Number']}"]
                        st.rerun()

                    if col_cancel.form_submit_button("取消", use_container_width=True):
                        del st.session_state[f"edit_mode_{row['Quote_Number']}"]
                        st.rerun()

            # ================ 刪除專案確認 ================
            if st.session_state.get(f"confirm_del_{row['Quote_Number']}", False):
                st.warning(f"確定要永久刪除專案 **{row['Quote_Number']}** 嗎？")
                c1, c2 = st.columns(2)
                if c1.button("確認刪除", type="primary", key=f"yes_del_{row['Quote_Number']}", use_container_width=True):
                    # 先從本地移除
                    projects_df = projects_df[projects_df["Quote_Number"] != row["Quote_Number"]].reset_index(drop=True)
                    conn.update(worksheet="supremacy_projects", data=projects_df)

                    manpower_df = manpower_df[manpower_df["Quote_Number"] != row["Quote_Number"]].reset_index(drop=True)
                    conn.update(worksheet="supremacy_manpower", data=manpower_df)

                    # 關鍵：強制從 Google Sheet 重新讀取最新資料，覆蓋本地快取
                    latest_projects = conn.read(worksheet="supremacy_projects", ttl=0)
                    if not latest_projects.empty and str(latest_projects.iloc[0,0]).strip().lower() in ["date", "日期"]:
                        latest_projects = latest_projects.iloc[1:].reset_index(drop=True)
                    latest_projects = latest_projects.iloc[:, :5]
                    latest_projects.columns = ["Date", "Quote_Number", "Work_Order", "Project_Detail", "Status"]
                    latest_projects["Quote_Number"] = latest_projects["Quote_Number"].astype(str).str.replace(".0", "", regex=False)
                    latest_projects["Work_Order"] = latest_projects["Work_Order"].fillna("").astype(str)
                    latest_projects["Date"] = pd.to_datetime(latest_projects["Date"], errors="coerce")
                    projects_df = latest_projects.copy()

                    latest_manpower = conn.read(worksheet="supremacy_manpower", ttl=0)
                    if not latest_manpower.empty and str(latest_manpower.iloc[0,0]).strip().lower() in ["quote_number", "quote number", "報價單號"]:
                        latest_manpower = latest_manpower.iloc[1:].reset_index(drop=True)
                    latest_manpower.columns = ["Quote_Number", "Staff", "Start_Date", "End_Date"][:len(latest_manpower.columns)]
                    latest_manpower["Quote_Number"] = latest_manpower["Quote_Number"].astype(str).str.replace(".0", "", regex=False)
                    manpower_df = latest_manpower.copy()

                    st.success("專案及所有借調已成功刪除！")
                    st.rerun()
                if c2.button("取消", key=f"no_del_{row['Quote_Number']}", use_container_width=True):
                    del st.session_state[f"confirm_del_{row['Quote_Number']}"]
                    st.rerun()

else:
    st.info("尚未新增任何副業專案" if not search_query else "無搜尋結果")

st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")