import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ==============================================
# 頁面設定
# ==============================================
st.set_page_config(
    page_title="SUPREMACY ENERGY - 副業專案管理",
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
        if len(manpower_raw) > 0 and str(manpower_raw.iloc[0, 0]).strip().lower() in ["quote_number", "quote number",
                                                                                      "報價單號"]:
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
                if len(current_raw) > 0 and str(current_raw.iloc[0, 0]).strip().lower() in ["date", "日期"]:
                    current_raw = current_raw.iloc[1:]
                updated_df = pd.concat([current_raw, new_row], ignore_index=True)
                conn.update(worksheet="supremacy_projects", data=updated_df)
                st.success(f"已新增專案：{quote_number}")
                st.rerun()

    st.markdown("---")
    st.markdown("### 🔍 搜尋專案")
    search_query = st.text_input("輸入 Quote Number 或 Work Order", key="supremacy_search",
                                 label_visibility="collapsed")
    if st.button("清除搜尋", type="secondary", use_container_width=True):
        if "supremacy_search" in st.session_state:
            del st.session_state.supremacy_search
        st.rerun()

    st.markdown("---")
    if st.button("📅 查看主日曆", type="primary", use_container_width=True):
        st.switch_page("YipShing.py")
        st.session_state.view_mode = "calendar"

# ==============================================
# 主畫面標題
# ==============================================
st.title("SUPREMACY ENERGY")

# ==============================================
# 搜尋過濾
# ==============================================
display_df = projects_df.copy()
if search_query:
    query = search_query.strip().lower()
    mask = (display_df["Quote_Number"].str.lower().str.contains(query) |
            display_df["Work_Order"].str.lower().str.contains(query))
    display_df = display_df[mask].reset_index(drop=True)
    if len(display_df) > 0:
        st.success(f"找到 {len(display_df)} 個符合的專案")
    else:
        st.info("無搜尋結果")

# ==============================================
# 長方形卡片列表顯示（使用 f-string，完全解決卡串問題）
# ==============================================
if len(display_df) > 0:
    sorted_df = display_df.sort_values(by="Date", ascending=False).reset_index(drop=True)

    for _, row in sorted_df.iterrows():
        # 狀態顏色
        status_color = {
            "Quoting": "#ffaa00",
            "Confirmed": "#00aa00",
            "In Production": "#0066ff",
            "Completed": "#66cc66"
        }.get(row["Status"], "#888888")

        # Work Order 顯示
        work_order_display = f"<small style='color:#666;'>Work Order: <strong>{row['Work_Order'] or '無'}</strong></small>" if row["Work_Order"] else ""

        # 借調顯示
        manpower_records = manpower_df[manpower_df["Quote_Number"] == row["Quote_Number"]]
        if len(manpower_records) > 0:
            manpower_lines = []
            for _, rec in manpower_records.iterrows():
                start = rec["Start_Date"]
                end = rec["End_Date"].strip() if pd.notna(rec["End_Date"]) and str(rec["End_Date"]).strip() else "進行中"
                manpower_lines.append(f"• {rec['Staff']} ({start} → {end})")
            manpower_html = f"<div style='margin-top:12px; padding-top:12px; border-top:1px dashed #ddd;'><small style='color:#000; font-weight:bold;'>借調：</small><br><small style='color:#000;'>" + "<br>".join(manpower_lines) + "</small></div>"
        else:
            manpower_html = ""

        # 使用 f-string 直接渲染整個卡片（最安全！）
        st.markdown(f"""
        <div style="background: white; border-left: 6px solid {status_color}; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 300px;">
                    <h4 style="margin:0 0 8px 0; color:#1fb429;">{row['Quote_Number']}</h4>
                    {work_order_display}
                    <p style="margin: 12px 0 0 0; font-size:1rem; color:#333; line-height:1.6;">{row['Project_Detail']}</p>
                    {manpower_html}
                </div>
                <div style="text-align: right; min-width: 200px;">
                    <div style="display: inline-block; text-align: center;">
                        <span style="background:{status_color}; color:white; padding:10px 24px; border-radius:25px; font-weight:bold; font-size:1.1rem; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">
                            {row['Status']}
                        </span>
                        <br><br>
                        <small style="color:#777; font-size:0.95rem;">
                            建立日期：{row['Date']}
                        </small>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Edit / Delete 按鈕
        col1, col2, col_spacer = st.columns([1, 1, 4])
        with col1:
            if st.button("Edit", key=f"edit_{row['Quote_Number']}", use_container_width=True):
                st.session_state[f"edit_mode_{row['Quote_Number']}"] = True
        with col2:
            if st.button("Delete", key=f"del_proj_{row['Quote_Number']}", type="secondary", use_container_width=True):
                st.session_state[f"confirm_del_{row['Quote_Number']}"] = True

        # 後續編輯模式、刪除確認保持不變
        # 其餘編輯模式、刪除確認等保持不變（你原本的程式碼即可）
        # ... （後面的編輯模式和刪除確認邏輯照舊） ...

        st.markdown("<hr style='margin: 30px 0; border-color: #eee;'>", unsafe_allow_html=True)

        # ================ 編輯模式 ================
        if st.session_state.get(f"edit_mode_{row['Quote_Number']}", False):
            original_idx = projects_df[projects_df["Quote_Number"] == row["Quote_Number"]].index[0]

            current_manpower = manpower_df[manpower_df["Quote_Number"] == row["Quote_Number"]].copy().reset_index(
                drop=True)
            if len(current_manpower) > 0:
                st.markdown("### 現有借調記錄（僅顯示刪除按鈕）")
                for m_idx, rec in current_manpower.iterrows():
                    if st.button(f"刪除借調：{rec['Staff']}", key=f"del_man_{row['Quote_Number']}_{m_idx}",
                                 type="secondary", use_container_width=True):
                        manpower_df = manpower_df.drop(
                            manpower_df[
                                (manpower_df["Quote_Number"] == row["Quote_Number"]) &
                                (manpower_df["Staff"] == rec["Staff"]) &
                                (manpower_df["Start_Date"] == rec["Start_Date"])
                                ].index
                        ).reset_index(drop=True)
                        conn.update(worksheet="supremacy_manpower", data=manpower_df)

                        latest_manpower = conn.read(worksheet="supremacy_manpower", ttl=0)
                        if not latest_manpower.empty and str(latest_manpower.iloc[0, 0]).strip().lower() in [
                            "quote_number", "quote number", "報價單號"]:
                            latest_manpower = latest_manpower.iloc[1:].reset_index(drop=True)
                        if not latest_manpower.empty:
                            latest_manpower.columns = ["Quote_Number", "Staff", "Start_Date", "End_Date"][
                                :len(latest_manpower.columns)]
                            latest_manpower["Quote_Number"] = latest_manpower["Quote_Number"].astype(str).str.replace(
                                ".0", "", regex=False)
                        manpower_df = latest_manpower.copy() if not latest_manpower.empty else pd.DataFrame(
                            columns=["Quote_Number", "Staff", "Start_Date", "End_Date"])

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

                        latest_manpower = conn.read(worksheet="supremacy_manpower", ttl=0)
                        if not latest_manpower.empty and str(latest_manpower.iloc[0, 0]).strip().lower() in [
                            "quote_number", "quote number", "報價單號"]:
                            latest_manpower = latest_manpower.iloc[1:].reset_index(drop=True)
                        if not latest_manpower.empty:
                            latest_manpower.columns = ["Quote_Number", "Staff", "Start_Date", "End_Date"][
                                :len(latest_manpower.columns)]
                            latest_manpower["Quote_Number"] = latest_manpower["Quote_Number"].astype(str).str.replace(
                                ".0", "", regex=False)
                        manpower_df = latest_manpower.copy() if not latest_manpower.empty else pd.DataFrame(
                            columns=["Quote_Number", "Staff", "Start_Date", "End_Date"])

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
                projects_df = projects_df[projects_df["Quote_Number"] != row["Quote_Number"]].reset_index(drop=True)
                conn.update(worksheet="supremacy_projects", data=projects_df)
                manpower_df = manpower_df[manpower_df["Quote_Number"] != row["Quote_Number"]].reset_index(drop=True)
                conn.update(worksheet="supremacy_manpower", data=manpower_df)
                st.success("專案及所有借調已刪除！")
                st.rerun()
            if c2.button("取消", key=f"no_del_{row['Quote_Number']}", use_container_width=True):
                del st.session_state[f"confirm_del_{row['Quote_Number']}"]
                st.rerun()

        st.markdown("<hr style='margin: 30px 0; border-color: #eee;'>", unsafe_allow_html=True)

else:
    st.info("尚未新增任何副業專案" if not search_query else "無搜尋結果")

st.markdown("---")
st.caption("SUPREMACY ENERGY Project Management System © 2025 YIP SHING")