import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
from datetime import date
import time

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
# 讀取主專案資料 (projects) - 用於自動生成事件
# ==============================================
try:
    df = conn.read(worksheet="projects", usecols=list(range(16)), ttl=300)
    df = df.dropna(how="all")
except:
    df = pd.DataFrame()

# ==============================================
# 讀取或建立 supremacy_projects worksheet (本頁專案列表)
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
# 讀取或建立 calendar_events worksheet (共用日曆事件)
# ==============================================
try:
    events_df = conn.read(worksheet="calendar_events", ttl=300)
    if events_df.empty:
        events_df = pd.DataFrame(columns=["id", "title", "start", "end", "description", "project_name"])
except:
    events_df = pd.DataFrame(columns=["id", "title", "start", "end", "description", "project_name"])
    conn.update(worksheet="calendar_events", data=events_df)

# ==============================================
# Sidebar
# ==============================================
with st.sidebar:
    st.header("SUPREMACY ENERGY")

    # Calendar 按鈕
    if st.button("📅 Calendar", use_container_width=True, type="primary", key="supremacy_calendar"):
        st.session_state.supremacy_view = "calendar"

    # New Project 表單
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
# 預設視圖控制
# ==============================================
if "supremacy_view" not in st.session_state:
    st.session_state.supremacy_view = "dashboard"

# ==============================================
# Calendar 視圖（與主頁完全共用資料）
# ==============================================
if st.session_state.supremacy_view == "calendar":
    st.title("專案日曆視圖")

    # 轉成 calendar 所需格式
    events = []
    for _, row in events_df.iterrows():
        events.append({
            "id": str(row["id"]),
            "title": row["title"],
            "start": row["start"],
            "end": row["end"] if pd.notna(row["end"]) else row["start"],
            "description": row["description"] if pd.notna(row["description"]) else "",
            "extendedProps": {"project_name": row["project_name"] if pd.notna(row["project_name"]) else ""}
        })

    # 自動加入主專案日期事件
    for _, proj in df.iterrows():
        if pd.notna(proj["Parts_Arrival"]):
            events.append({
                "title": f"零件到貨: {proj['Project_Name']}",
                "start": proj["Parts_Arrival"].strftime("%Y-%m-%d"),
                "color": "#a8e6cf",
                "extendedProps": {"project_name": proj["Project_Name"]}
            })
        if pd.notna(proj["Testing_Complete"]):
            events.append({
                "title": f"測試完成: {proj['Project_Name']}",
                "start": proj["Testing_Complete"].strftime("%Y-%m-%d"),
                "color": "#ff9f89",
                "extendedProps": {"project_name": proj["Project_Name"]}
            })

    calendar_options = {
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        },
        "selectable": True,
        "selectMirror": True,
        "selectOverlap": False,
        "selectAllow": "function(selectInfo) { return true; }",
        "editable": True,
        "dayMaxEvents": True,
        "height": "800px",
        "locale": "zh-hk",
    }

    calendar_events = calendar(events=events, options=calendar_options, key="supremacy_calendar")

    # 編輯事件
    if calendar_events.get("eventClick"):
        event = calendar_events["eventClick"]["event"]
        st.subheader(f"編輯事件: {event['title']}")
        new_title = st.text_input("標題", event['title'])
        new_date = st.date_input("日期", pd.to_datetime(event['start']).date())
        new_desc = st.text_area("描述", event.get('extendedProps', {}).get('description', ''))
        if st.button("儲存修改"):
            events_df.loc[events_df["id"] == event["id"], ["title", "start", "description"]] = [new_title, new_date.strftime("%Y-%m-%d"), new_desc]
            conn.update(worksheet="calendar_events", data=events_df)
            st.success("事件已更新！")
            st.rerun()

    # 新增事件（點空白日期）
    select_info = calendar_events.get("select")
    if select_info:
        st.subheader("新增事件")
        title = st.text_input("事件標題", value="新工作")
        desc = st.text_area("描述", value="")
        if st.button("新增"):
            new_id = str(int(events_df["id"].max()) + 1) if not events_df.empty and pd.notna(events_df["id"].max()) else "1"
            start_date = select_info["startStr"][:10]
            end_date = select_info.get("endStr", "")[:10] if select_info.get("endStr") else start_date
            new_row = pd.DataFrame([{
                "id": new_id,
                "title": title,
                "start": start_date,
                "end": end_date,
                "description": desc,
                "project_name": ""
            }])
            events_df = pd.concat([events_df, new_row], ignore_index=True)
            conn.update(worksheet="calendar_events", data=events_df)
            st.success("事件已新增！")
            st.rerun()

# ==============================================
# Dashboard 視圖（預設）
# ==============================================
else:
    st.title("SUPREMACY ENERGY")

    st.markdown("""
    ### 專案管理系統

    此頁面專門用於 SUPREMACY ENERGY 系列專案報價與追蹤。
    """)

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