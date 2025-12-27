import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
from datetime import date

# ==============================================
# 頁面設定
# ==============================================
st.set_page_config(
    page_title="SUPREMACY ENERGY Calendar - YIP SHING",
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
# 生成日曆事件
# ==============================================
events = []

# 自定義事件（從 calendar_events 讀取）
for _, row in events_df.iterrows():
    events.append({
        "id": str(row["id"]),
        "title": row["title"],
        "start": row["start"],
        "end": row["end"] if pd.notna(row["end"]) else row["start"],
        "description": row["description"] if pd.notna(row["description"]) else "",
        "extendedProps": {"project_name": row["project_name"] if pd.notna(row["project_name"]) else ""}
    })

# 自動加入主專案事件（Parts Arrival & Testing Complete）
for _, proj in df.iterrows():
    if pd.notna(proj["Parts_Arrival"]):
        parts_date = proj["Parts_Arrival"].date()
        events.append({
            "title": f"零件到貨: {proj['Project_Name']}",
            "start": parts_date.strftime("%Y-%m-%d"),
            "color": "#a8e6cf",
            "extendedProps": {"project_name": proj["Project_Name"]}
        })
    if pd.notna(proj["Testing_Complete"]):
        test_date = proj["Testing_Complete"].date()
        events.append({
            "title": f"測試完成: {proj['Project_Name']}",
            "start": test_date.strftime("%Y-%m-%d"),
            "color": "#ff9f89",
            "extendedProps": {"project_name": proj["Project_Name"]}
        })

# ==============================================
# 日曆設定（與主頁完全一樣）
# ==============================================
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

# ==============================================
# 編輯事件
# ==============================================
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

# ==============================================
# 新增事件（點空白日期）
# ==============================================
select_info = calendar_events.get("select")
if select_info and isinstance(select_info, dict):
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
# 頁面標題
# ==============================================
st.title("SUPREMACY ENERGY Calendar")

st.info("此日曆與主頁完全共用資料，包括專案自動事件與自定義事件。")

# ==============================================
# 頁腳
# ==============================================
st.markdown("---")
st.caption("SUPREMACY ENERGY Calendar © 2025 YIP SHING")