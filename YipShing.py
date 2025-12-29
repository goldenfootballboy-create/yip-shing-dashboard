import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
import json
from datetime import date
import time

# ==============================================
# 頁面設定
# ==============================================
st.set_page_config(
    page_title="YIP SHING Project Dashboard",
    page_icon="https://i.imgur.com/Q8ehtk3.jpeg",
    layout="wide"
)

# ==============================================
# Google Sheets 連接 + 讀取（快取 + 重試）
# ==============================================
conn = st.connection('gsheets', type=GSheetsConnection)

max_retries = 3
df = None

for attempt in range(max_retries):
    try:
        df = conn.read(worksheet="projects", usecols=list(range(16)), ttl=300)
        df = df.dropna(how="all")
        break
    except Exception:
        if attempt < max_retries - 1:
            time.sleep(5)
        else:
            st.error("無法連線到 Google Sheets，請稍後再試或檢查網路")
            st.stop()

required = ["Project_Type","Project_Name","Year","Lead_Time","Customer","Supervisor",
            "Qty","Real_Count","Project_Spec","Description","Progress_Reminder",
            "Parts_Arrival","Installation_Complete","Testing_Complete","Cleaning_Complete","Delivery_Complete"]

if df.empty:
    df = pd.DataFrame(columns=required)

for c in required:
    if c not in df.columns:
        df[c] = "" if c != "Year" else 2025

date_cols = ["Lead_Time","Parts_Arrival","Installation_Complete","Testing_Complete","Cleaning_Complete","Delivery_Complete"]
for c in date_cols:
    df[c] = pd.to_datetime(df[c], errors="coerce")

df["Year"] = pd.to_numeric(df["Year"], errors="coerce").fillna(date.today().year).astype(int)
df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(1).astype(int)
df["Real_Count"] = pd.to_numeric(df["Real_Count"], errors="coerce").fillna(df["Qty"]).astype(int)

# 讀取 checklist
checklist_raw = None
for attempt in range(max_retries):
    try:
        checklist_raw = conn.read(worksheet="checklist", ttl=300)
        break
    except Exception:
        if attempt < max_retries - 1:
            time.sleep(5)
        else:
            checklist_raw = pd.DataFrame()

checklist_db = {}
if not checklist_raw.empty:
    for _, row in checklist_raw.iterrows():
        if "Project_Name" in row and "Checklist_Data" in row and pd.notna(row["Checklist_Data"]):
            try:
                checklist_db[row["Project_Name"]] = json.loads(row["Checklist_Data"])
            except:
                pass

# 儲存函數
def save_projects():
    df_save = df.copy()
    for c in date_cols:
        df_save[c] = df_save[c].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None)
    conn.update(worksheet="projects", data=df_save)
    time.sleep(2)

def save_checklist():
    if not checklist_db:
        empty_df = pd.DataFrame(columns=["Project_Name", "Checklist_Data"])
        conn.update(worksheet="checklist", data=empty_df)
    else:
        checklist_list = [{"Project_Name": k, "Checklist_Data": json.dumps(v, ensure_ascii=False)} for k, v in checklist_db.items()]
        checklist_save = pd.DataFrame(checklist_list)
        conn.update(worksheet="checklist", data=checklist_save)
    time.sleep(2)

# ==============================================
# 進度計算 + 顏色
# ==============================================
def calculate_progress(row):
    p = 0
    today = date.today()
    if pd.notna(row.get("Parts_Arrival")) and row["Parts_Arrival"].date() < today:
        p += 30
    if pd.notna(row.get("Installation_Complete")) and row["Installation_Complete"].date() < today:
        p += 40
    if pd.notna(row.get("Testing_Complete")) and row["Testing_Complete"].date() < today:
        p += 10
    if pd.notna(row.get("Cleaning_Complete")) and row["Cleaning_Complete"].date() < today:
        p += 10
    if pd.notna(row.get("Delivery_Complete")) and row["Delivery_Complete"].date() < today:
        p += 10
    return min(p, 100)

def get_color(pct):
    if pct >= 100: return "#0066ff"
    elif pct >= 90: return "#00aa00"
    elif pct >= 70: return "#66cc66"
    elif pct >= 30: return "#ffaa00"
    else: return "#ff4444"

def fmt(d):
    return pd.to_datetime(d).strftime("%Y-%m-%d") if pd.notna(d) else "—"

# ==============================================
# 專案卡片渲染函數
# ==============================================
def render_project_card(row, idx):
    pct = calculate_progress(row)
    color = get_color(pct)

    project_name = row["Project_Name"]
    current_check = checklist_db.get(project_name, {"purchase": [], "done_p": [], "drawing": [], "done_d": []})
    all_items = current_check["purchase"] + current_check["drawing"]
    done_items = set(current_check["done_p"]) | set(current_check["done_d"])
    real_items = [item for item in all_items if item and str(item).strip()]
    has_missing = any(str(item).strip() and str(item) not in done_items for item in real_items)
    all_done = len(real_items) > 0 and not has_missing
    is_empty = len(real_items) == 0

    status_tag = ""
    if is_empty:
        status_tag = '<span style="background:#888888; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:0.8rem; margin-left:10px;">Please add checklist</span>'
    elif all_done:
        status_tag = '<span style="background:#F0FFFD; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:1.2rem; margin-left:10px;">✅</span>'
    elif has_missing:
        status_tag = '<span style="background:#ff4444; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:0.8rem; margin-left:10px;">Missing Submission</span>'

    reminder_text = str(row.get("Progress_Reminder", "")).strip() or "In Progress"
    reminder_display = f'<div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); font-weight:bold; font-size:0.8rem; color:white; text-shadow:1px 1px 3px black; pointer-events:none; z-index:10;">{reminder_text}</div>'

    st.markdown(f"""
    <div style="background: linear-gradient(to right, {color} {pct}%, #f0f0f0 {pct}%); 
                border-radius: 8px; padding: 10px 15px; margin: 10px 0; 
                box-shadow: 0 2px 6px rgba(0,0,0,0.1); position: relative; overflow:hidden;">
        {reminder_display}
        <div style="display: flex; justify-content: space-between; align-items: center; position:relative; z-index:5;">
            <div style="font-weight: bold; color:#000000;">
                {row['Project_Name']} • {row['Project_Type']}
            </div>
            <div>
                {status_tag}
                <span style="color:white; background:{color}; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:1rem; margin-left:10px;">
                    {pct}%
                </span>
            </div>
        </div>
        <div style="font-size:0.85rem; color:#121111; margin-top:6px; position:relative; z-index:5;">
            {row.get('Customer','—')} | {row.get('Supervisor','—')} | Qty:{row.get('Qty',0)} | 
            Lead Time: {fmt(row['Lead_Time'])}
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"Details • {row['Project_Name']}", expanded=False):
        st.markdown(f"**Year:** {row['Year']} | **Lead Time:** {fmt(row['Lead_Time'])}")
        st.markdown(f"**Customer:** {row.get('Customer','—')} | **Supervisor:** {row.get('Supervisor','—')} | **Qty:** {row.get('Qty',0)}")

        if row.get("Project_Spec"):
            st.markdown("**Project Specification:**")
            for line in row["Project_Spec"].split("\n"):
                if line.strip():
                    key, val = line.split(": ",1) if ": " in line else ("", line)
                    st.markdown(f"• **{key}:** {val}")

        if row.get("Description"):
            st.markdown(f"**Description:** {row['Description']}")

        if st.button("Checklist Panel", key=f"cl_btn_{idx}", use_container_width=True):
            st.session_state[f"cl_open_{idx}"] = not st.session_state.get(f"cl_open_{idx}", False)

        if st.session_state.get(f"cl_open_{idx}", False):
            current = checklist_db.get(project_name, {"purchase": [],"done_p": [],"drawing": [],"done_d": []})

            st.markdown("<h4 style='text-align:center;'>Purchase List        Drawings Submission</h4>", unsafe_allow_html=True)

            new_purchase = []
            new_done_p = set()
            new_drawing = []
            new_done_d = set()

            max_rows = max(len(current["purchase"]), len(current["drawing"]), 6)

            for i in range(max_rows):
                c1, c2 = st.columns(2)
                with c1:
                    text = current["purchase"][i] if i < len(current["purchase"]) else ""
                    checked = text in current["done_p"]
                    col_chk, col_txt = st.columns([1,7])
                    with col_chk:
                        chk = st.checkbox("", value=checked, key=f"p_{idx}_{i}")
                    with col_txt:
                        txt = st.text_input("", value=text, key=f"pt_{idx}_{i}", label_visibility="collapsed")
                    if txt.strip():
                        new_purchase.append(txt.strip())
                        if chk:
                            new_done_p.add(txt.strip())
                with c2:
                    text = current["drawing"][i] if i < len(current["drawing"]) else ""
                    checked = text in current["done_d"]
                    col_chk, col_txt = st.columns([1,7])
                    with col_chk:
                        chk = st.checkbox("", value=checked, key=f"d_{idx}_{i}")
                    with col_txt:
                        txt = st.text_input("", value=text, key=f"dt_{idx}_{i}", label_visibility="collapsed")
                    if txt.strip():
                        new_drawing.append(txt.strip())
                        if chk:
                            new_done_d.add(txt.strip())

            if st.button("SAVE CHECKLIST", key=f"save_cl_{idx}", type="primary", use_container_width=True):
                checklist_db[project_name] = {
                    "purchase": new_purchase,
                    "done_p": list(new_done_p),
                    "drawing": new_drawing,
                    "done_d": list(new_done_d)
                }
                save_checklist()
                st.cache_data.clear()
                st.success("Checklist 已永久儲存到 Google Sheets！")
                st.rerun()

# ==============================================
# 左側側邊欄
# ==============================================
with st.sidebar:
    st.header("View Controls")

    if st.button("All Projects", use_container_width=True, type="primary", key="btn_all"):
        st.session_state.view_mode = "all"
    if st.button("Delay Projects", use_container_width=True, type="secondary", key="btn_delay"):
        st.session_state.view_mode = "delay"

    if st.button("📅Calendar", use_container_width=True, type="primary", key="btn_calendar"):
        st.session_state.view_mode = "calendar"

    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "all"

    st.markdown("---")

    st.markdown("### Search Project Name")
    search_term = st.text_input(
        "Enter Project Name (partial match)",
        value="",
        key="search_input",
        label_visibility="collapsed"
    )

    st.markdown("---")

    project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
    years = [2024, 2025, 2026]
    month_names = ["All", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    if st.session_state.view_mode == "all":
        st.markdown("### Filters")
        selected_type = st.selectbox("Project Type", project_types, index=project_types.index("All"), key="filter_type")
        selected_year = st.selectbox("Year", years, index=years.index(date.today().year), key="filter_year")
        selected_month = st.selectbox("Month", month_names, index=month_names.index("All"), key="filter_month")
    else:
        selected_type = "All"
        selected_year = date.today().year
        selected_month = "All"

    st.markdown("---")

    st.header("New Project")

    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_type = st.selectbox("Project Type*", ["Enclosure","Open Set","Scania","Marine","K50G3"], key="new_type")
            new_name = st.text_input("Project Name*", key="new_name")
            new_year = st.selectbox("Year*", [2024,2025,2026], index=1, key="new_year")
            new_qty = st.number_input("Qty", min_value=1, value=1, key="new_qty")
        with c2:
            new_customer = st.text_input("Customer", key="new_customer")
            new_supervisor = st.text_input("Supervisor", key="new_supervisor")
            new_leadtime = st.date_input("Lead Time*", value=date.today(), key="new_leadtime")

        # Progress Dates 直接放在主表單
        st.markdown("**Progress Dates**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            d1 = st.date_input("Parts Arrival", value=None, key="d1")
            d2 = st.date_input("Installation Complete", value=None, key="d2")
            d3 = st.date_input("Testing Complete", value=None, key="d3")
        with col_d2:
            d4 = st.date_input("Cleaning Complete", value=None, key="d4")
            d5 = st.date_input("Delivery Complete", value=None, key="d5")

        reminder = st.text_input("Progress Reminder (顯示在進度條中間)", placeholder="例如：等緊報價 / 生產中 / 已發貨", key="reminder")

        # Project Specification 按鈕（彈出視窗）
        if st.button("Project Specification", type="primary", use_container_width=True):
            st.session_state.spec_dialog_open = True

        # Project Specification 彈出視窗
        @st.dialog("Project Specification", width="large")
        def spec_dialog():
            st.markdown("**Specification**")
            # 5 行 2 欄布局
            row1 = st.columns(2)
            with row1[0]:
                s_genset = st.text_input("Genset model", key="dlg_genset")
            with row1[1]:
                s_genset_sn = st.text_input("S/N", key="dlg_genset_sn")

            row2 = st.columns(2)
            with row2[0]:
                s_alternator = st.text_input("Alternator Model", key="dlg_alternator")
            with row2[1]:
                s_alternator_sn = st.text_input("S/N", key="dlg_alternator_sn")

            row3 = st.columns(2)
            with row3[0]:
                s_controller = st.text_input("Controller", key="dlg_controller")
            with row3[1]:
                s_controller_sn = st.text_input("S/N", key="dlg_controller_sn")

            row4 = st.columns(2)
            with row4[0]:
                s_breaker = st.text_input("Circuit breaker Size", key="dlg_breaker")
            with row4[1]:
                s_breaker_sn = st.text_input("S/N", key="dlg_breaker_sn")

            row5 = st.columns(2)
            with row5[0]:
                s_charger = st.text_input("Charger", key="dlg_charger")
            with row5[1]:
                s_charger_sn = st.text_input("S/N", key="dlg_charger_sn")

            desc = st.text_area("Description", height=150, key="dlg_desc")

            if st.button("Save & Close", type="primary"):
                st.session_state.spec_data = {
                    "genset": s_genset or '—',
                    "genset_sn": s_genset_sn or '—',
                    "alternator": s_alternator or '—',
                    "alternator_sn": s_alternator_sn or '—',
                    "controller": s_controller or '—',
                    "controller_sn": s_controller_sn or '—',
                    "breaker": s_breaker or '—',
                    "breaker_sn": s_breaker_sn or '—',
                    "charger": s_charger or '—',
                    "charger_sn": s_charger_sn or '—',
                    "desc": desc or ""
                }
                st.rerun()

        if st.session_state.get("spec_dialog_open", False):
            spec_dialog()

        if st.form_submit_button("Add", type="primary", use_container_width=True):
            if not new_name.strip():
                st.error("Project Name required!")
            elif new_name in df["Project_Name"].values:
                st.error("Name exists!")
            else:
                # 取彈出視窗資料
                spec_data = st.session_state.get("spec_data", {
                    "genset": "—", "genset_sn": "—", "alternator": "—", "alternator_sn": "—",
                    "controller": "—", "controller_sn": "—", "breaker": "—", "breaker_sn": "—",
                    "charger": "—", "charger_sn": "—", "desc": ""
                })
                spec_lines = [
                    f"Genset model: {spec_data['genset']} | S/N: {spec_data['genset_sn']}",
                    f"Alternator Model: {spec_data['alternator']} | S/N: {spec_data['alternator_sn']}",
                    f"Controller: {spec_data['controller']} | S/N: {spec_data['controller_sn']}",
                    f"Circuit breaker Size: {spec_data['breaker']} | S/N: {spec_data['breaker_sn']}",
                    f"Charger: {spec_data['charger']} | S/N: {spec_data['charger_sn']}"
                ]
                spec_text = "\n".join(spec_lines)

                new_project = {
                    "Project_Type": new_type, "Project_Name": new_name, "Year": int(new_year),
                    "Lead_Time": new_leadtime, "Customer": new_customer or "", "Supervisor": new_supervisor or "",
                    "Qty": new_qty, "Real_Count": new_qty, "Project_Spec": spec_text, "Description": spec_data["desc"],
                    "Progress_Reminder": reminder or "", "Parts_Arrival": d1, "Installation_Complete": d2,
                    "Testing_Complete": d3, "Cleaning_Complete": d4, "Delivery_Complete": d5
                }
                df = pd.concat([df, pd.DataFrame([new_project])], ignore_index=True)
                save_projects()
                st.cache_data.clear()
                # 清空資料
                if "spec_data" in st.session_state:
                    del st.session_state.spec_data
                if "spec_dialog_open" in st.session_state:
                    del st.session_state.spec_dialog_open
                st.success(f"Added: {new_name}")
                st.rerun()

# ==============================================
# 篩選邏輯
# ==============================================
today = date.today()
filtered_df = df.copy()

has_search = search_term.strip() != ""
if has_search:
    search_term_lower = search_term.strip().lower()
    filtered_df = filtered_df[filtered_df["Project_Name"].str.lower().str.contains(search_term_lower, na=False)]

if st.session_state.view_mode == "delay":
    filtered_df = filtered_df[
        filtered_df["Lead_Time"].notna() &
        (filtered_df["Lead_Time"] < pd.Timestamp(today)) &
        (filtered_df.apply(calculate_progress, axis=1) < 100)
    ]
    page_title = "Delay Projects"
else:
    if not has_search:
        if selected_type != "All":
            filtered_df = filtered_df[filtered_df["Project_Type"] == selected_type]
        filtered_df = filtered_df[filtered_df["Year"] == selected_year]
        if selected_month != "All":
            month_map = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
            filtered_df = filtered_df[
                filtered_df["Lead_Time"].notna() &
                (filtered_df["Lead_Time"].dt.month == month_map[selected_month])
            ]
    page_title = "YIP SHING Project Dashboard"

# ==============================================
# 日曆模式（完整支援新增/編輯自定義事件）
# ==============================================
if st.session_state.view_mode == "calendar":
    page_title = "專案日曆視圖"

    try:
        events_df = conn.read(worksheet="calendar_events", ttl=300)
        if events_df.empty:
            events_df = pd.DataFrame(columns=["id", "title", "start", "end", "description", "project_name"])
    except:
        events_df = pd.DataFrame(columns=["id", "title", "start", "end", "description", "project_name"])
        conn.update(worksheet="calendar_events", data=events_df)

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

    calendar_events = calendar(events=events, options=calendar_options, key="project_calendar")

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

    st.stop()

# ==============================================
# 主畫面
# ==============================================
st.markdown(
    f"<h1 style='text-align: center; color: #1fb429; margin-bottom: 30px; font-weight: bold;'>{page_title}</h1>",
    unsafe_allow_html=True
)

if len(filtered_df) == 0:
    if st.session_state.view_mode == "delay":
        st.success("No delay projects! All on time!")
    else:
        st.info("No projects match the selected filters or search term.")
else:
    if not filtered_df.empty:
        progress_series = filtered_df.apply(calculate_progress, axis=1)
        filtered_df = filtered_df.assign(Progress=progress_series) \
                                      .sort_values(by="Progress", ascending=False) \
                                      .drop(columns="Progress")

    counter = filtered_df.groupby("Project_Type")["Qty"].sum().astype(int).sort_index()
    total_qty = int(filtered_df["Qty"].sum())
    st.markdown(f"""
    <div style="position:fixed; top:70px; right:20px; background:#1e3a8a; color:white; padding:12px 18px; 
                border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.3); z-index:1000; font-size:0.9rem; text-align:center;">
        <strong style="font-size:1.1rem;">Total: {total_qty}</strong><br>
        {"<br>".join([f"<strong>{k}:</strong> {v}" for k, v in counter.items()])}
    </div>
    """, unsafe_allow_html=True)

    rows = filtered_df.to_dict('records')
    for i in range(0, len(rows), 2):
        col1, col2 = st.columns(2)

        with col1:
            if i < len(rows):
                row = rows[i]
                idx = filtered_df.index[i]
                render_project_card(row, idx)

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("Edit", key=f"edit_{idx}"):
                        st.session_state[f"editing_{idx}"] = not st.session_state.get(f"editing_{idx}", False)
                with btn_col2:
                    if st.button("Delete", key=f"del_{idx}", type="secondary"):
                        st.session_state[f"confirm_delete_{idx}"] = True

                if st.session_state.get(f"editing_{idx}", False):
                    st.markdown("---")
                    st.subheader(f"Editing: {row['Project_Name']}")
                    with st.form(key=f"edit_form_{idx}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            e_type = st.selectbox("Project Type*", ["Enclosure","Open Set","Scania","Marine","K50G3"],
                                                  index=["Enclosure","Open Set","Scania","Marine","K50G3"].index(row["Project_Type"]))
                            e_name = st.text_input("Project Name*", value=row["Project_Name"])
                            e_year = st.selectbox("Year*", [2024,2025,2026], index=[2024,2025,2026].index(row["Year"]))
                            e_qty = st.number_input("Qty", min_value=1, value=int(row.get("Qty",1)))
                        with c2:
                            e_customer = st.text_input("Customer", value=row.get("Customer",""))
                            e_supervisor = st.text_input("Supervisor", value=row.get("Supervisor",""))
                            e_leadtime = st.date_input("Lead Time*", value=pd.to_datetime(row["Lead_Time"]).date() if pd.notna(row["Lead_Time"]) else date.today())

                        st.markdown("**Progress Dates**")
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            e_d1 = st.date_input("Parts Arrival", value=pd.to_datetime(row["Parts_Arrival"]).date() if pd.notna(row["Parts_Arrival"]) else None, key=f"d1e{idx}")
                            e_d2 = st.date_input("Installation Complete", value=pd.to_datetime(row["Installation_Complete"]).date() if pd.notna(row["Installation_Complete"]) else None, key=f"d2e{idx}")
                            e_d3 = st.date_input("Testing Complete", value=pd.to_datetime(row["Testing_Complete"]).date() if pd.notna(row["Testing_Complete"]) else None, key=f"d3e{idx}")
                        with col_d2:
                            e_d4 = st.date_input("Cleaning Complete", value=pd.to_datetime(row["Cleaning_Complete"]).date() if pd.notna(row["Cleaning_Complete"]) else None, key=f"d4e{idx}")
                            e_d5 = st.date_input("Delivery Complete", value=pd.to_datetime(row["Delivery_Complete"]).date() if pd.notna(row["Delivery_Complete"]) else None, key=f"d5e{idx}")

                            e_reminder = st.text_input("Progress Reminder", value=row.get("Progress_Reminder",""))

                        # Project Specification 按鈕（彈出視窗）
                        if st.button("Project Specification", type="primary", use_container_width=True):
                            st.session_state[f"edit_spec_dialog_{idx}"] = True

                        # Edit Specification 彈出視窗
                        @st.dialog("Project Specification", width="large")
                        def edit_spec_dialog(row, idx):
                            st.markdown("**Specification**")
                            curr_spec = row.get("Project_Spec","")
                            lines = [line.split(": ",1)[1].split(" | S/N: ") if " | S/N: " in line else [line.split(": ",1)[1] if ": " in line else "", ""] for line in curr_spec.split("\n")] if curr_spec else [["","","","","","","","","",""]]

                            row1 = st.columns(2)
                            with row1[0]:
                                e_s1 = st.text_input("Genset model", value=lines[0][0] if len(lines)>0 else "")
                            with row1[1]:
                                e_s1_sn = st.text_input("S/N", value=lines[0][1] if len(lines[0])>1 else "")

                            row2 = st.columns(2)
                            with row2[0]:
                                e_s2 = st.text_input("Alternator Model", value=lines[1][0] if len(lines)>1 else "")
                            with row2[1]:
                                e_s2_sn = st.text_input("S/N", value=lines[1][1] if len(lines[1])>1 else "")

                            row3 = st.columns(2)
                            with row3[0]:
                                e_s3 = st.text_input("Controller", value=lines[2][0] if len(lines)>2 else "")
                            with row3[1]:
                                e_s3_sn = st.text_input("S/N", value=lines[2][1] if len(lines[2])>1 else "")

                            row4 = st.columns(2)
                            with row4[0]:
                                e_s4 = st.text_input("Circuit breaker Size", value=lines[3][0] if len(lines)>3 else "")
                            with row4[1]:
                                e_s4_sn = st.text_input("S/N", value=lines[3][1] if len(lines[3])>1 else "")

                            row5 = st.columns(2)
                            with row5[0]:
                                e_s5 = st.text_input("Charger", value=lines[4][0] if len(lines)>4 else "")
                            with row5[1]:
                                e_s5_sn = st.text_input("S/N", value=lines[4][1] if len(lines[4])>1 else "")

                            e_desc = st.text_area("Description", value=row.get("Description",""), height=150)

                            if st.button("Save & Close", type="primary"):
                                new_spec = "\n".join([
                                    f"Genset model: {e_s1 or '—'} | S/N: {e_s1_sn or '—'}",
                                    f"Alternator Model: {e_s2 or '—'} | S/N: {e_s2_sn or '—'}",
                                    f"Controller: {e_s3 or '—'} | S/N: {e_s3_sn or '—'}",
                                    f"Circuit breaker Size: {e_s4 or '—'} | S/N: {e_s4_sn or '—'}",
                                    f"Charger: {e_s5 or '—'} | S/N: {e_s5_sn or '—'}"
                                ])
                                df.at[idx, "Project_Spec"] = new_spec
                                df.at[idx, "Description"] = e_desc or ""
                                save_projects()
                                st.cache_data.clear()
                                st.success("Specification 已更新！")
                                st.rerun()

                        if st.session_state.get(f"edit_spec_dialog_{idx}", False):
                            edit_spec_dialog(row, idx)

                        if st.form_submit_button("Save Changes", type="primary"):
                            if not e_name.strip():
                                st.error("Project Name required!")
                            else:
                                df.at[idx, "Project_Type"] = e_type
                                df.at[idx, "Project_Name"] = e_name
                                df.at[idx, "Year"] = int(e_year)
                                df.at[idx, "Lead_Time"] = e_leadtime
                                df.at[idx, "Customer"] = e_customer or ""
                                df.at[idx, "Supervisor"] = e_supervisor or ""
                                df.at[idx, "Qty"] = e_qty
                                df.at[idx, "Real_Count"] = e_qty
                                df.at[idx, "Progress_Reminder"] = e_reminder or ""
                                df.at[idx, "Parts_Arrival"] = e_d1
                                df.at[idx, "Installation_Complete"] = e_d2
                                df.at[idx, "Testing_Complete"] = e_d3
                                df.at[idx, "Cleaning_Complete"] = e_d4
                                df.at[idx, "Delivery_Complete"] = e_d5
                                save_projects()
                                st.cache_data.clear()
                                del st.session_state[f"editing_{idx}"]
                                st.success("Updated!")
                                st.rerun()

                if st.session_state.get(f"confirm_delete_{idx}", False):
                    st.warning(f"確定要刪除專案 **{row['Project_Name']}** 嗎？")
                    col_yes, col_no = st.columns(2)
                    if col_yes.button("Yes, Delete", type="primary"):
                        df = df.drop(idx).reset_index(drop=True)
                        save_projects()
                        checklist_db.pop(row["Project_Name"], None)
                        save_checklist()
                        st.cache_data.clear()
                        if f"confirm_delete_{idx}" in st.session_state:
                            del st.session_state[f"confirm_delete_{idx}"]
                        st.success("已刪除！")
                        st.rerun()
                    if col_no.button("Cancel"):
                        if f"confirm_delete_{idx}" in st.session_state:
                            del st.session_state[f"confirm_delete_{idx}"]
                        st.rerun()

        with col2:
            if i + 1 < len(rows):
                row = rows[i + 1]
                idx = filtered_df.index[i + 1]
                render_project_card(row, idx)

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("Edit", key=f"edit_{idx}"):
                        st.session_state[f"editing_{idx}"] = not st.session_state.get(f"editing_{idx}", False)

                with btn_col2:
                    if st.button("Delete", key=f"del_{idx}", type="secondary"):
                        st.session_state[f"confirm_delete_{idx}"] = True

                if st.session_state.get(f"editing_{idx}", False):
                    st.markdown("---")
                    st.subheader(f"Editing: {row['Project_Name']}")
                    with st.form(key=f"edit_form_{idx}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            e_type = st.selectbox("Project Type*", ["Enclosure","Open Set","Scania","Marine","K50G3"],
                                                  index=["Enclosure","Open Set","Scania","Marine","K50G3"].index(row["Project_Type"]))
                            e_name = st.text_input("Project Name*", value=row["Project_Name"])
                            e_year = st.selectbox("Year*", [2024,2025,2026], index=[2024,2025,2026].index(row["Year"]))
                            e_qty = st.number_input("Qty", min_value=1, value=int(row.get("Qty",1)))
                        with c2:
                            e_customer = st.text_input("Customer", value=row.get("Customer",""))
                            e_supervisor = st.text_input("Supervisor", value=row.get("Supervisor",""))
                            e_leadtime = st.date_input("Lead Time*", value=pd.to_datetime(row["Lead_Time"]).date() if pd.notna(row["Lead_Time"]) else date.today())

                        st.markdown("**Progress Dates**")
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            e_d1 = st.date_input("Parts Arrival", value=pd.to_datetime(row["Parts_Arrival"]).date() if pd.notna(row["Parts_Arrival"]) else None, key=f"d1e{idx}")
                            e_d2 = st.date_input("Installation Complete", value=pd.to_datetime(row["Installation_Complete"]).date() if pd.notna(row["Installation_Complete"]) else None, key=f"d2e{idx}")
                            e_d3 = st.date_input("Testing Complete", value=pd.to_datetime(row["Testing_Complete"]).date() if pd.notna(row["Testing_Complete"]) else None, key=f"d3e{idx}")
                        with col_d2:
                            e_d4 = st.date_input("Cleaning Complete", value=pd.to_datetime(row["Cleaning_Complete"]).date() if pd.notna(row["Cleaning_Complete"]) else None, key=f"d4e{idx}")
                            e_d5 = st.date_input("Delivery Complete", value=pd.to_datetime(row["Delivery_Complete"]).date() if pd.notna(row["Delivery_Complete"]) else None, key=f"d5e{idx}")

                            e_reminder = st.text_input("Progress Reminder", value=row.get("Progress_Reminder",""))

                        # Project Specification 按鈕（彈出視窗）
                        if st.button("Project Specification", type="primary", use_container_width=True):
                            st.session_state[f"edit_spec_dialog_{idx}"] = True

                        # Edit Specification 彈出視窗
                        @st.dialog("Project Specification", width="large")
                        def edit_spec_dialog(row, idx):
                            st.markdown("**Specification**")
                            curr_spec = row.get("Project_Spec","")
                            lines = [line.split(": ",1)[1].split(" | S/N: ") if " | S/N: " in line else [line.split(": ",1)[1] if ": " in line else "", ""] for line in curr_spec.split("\n")] if curr_spec else [["","","","","","","","","",""]]

                            row1 = st.columns(2)
                            with row1[0]:
                                e_s1 = st.text_input("Genset model", value=lines[0][0] if len(lines)>0 else "")
                            with row1[1]:
                                e_s1_sn = st.text_input("S/N", value=lines[0][1] if len(lines[0])>1 else "")

                            row2 = st.columns(2)
                            with row2[0]:
                                e_s2 = st.text_input("Alternator Model", value=lines[1][0] if len(lines)>1 else "")
                            with row2[1]:
                                e_s2_sn = st.text_input("S/N", value=lines[1][1] if len(lines[1])>1 else "")

                            row3 = st.columns(2)
                            with row3[0]:
                                e_s3 = st.text_input("Controller", value=lines[2][0] if len(lines)>2 else "")
                            with row3[1]:
                                e_s3_sn = st.text_input("S/N", value=lines[2][1] if len(lines[2])>1 else "")

                            row4 = st.columns(2)
                            with row4[0]:
                                e_s4 = st.text_input("Circuit breaker Size", value=lines[3][0] if len(lines)>3 else "")
                            with row4[1]:
                                e_s4_sn = st.text_input("S/N", value=lines[3][1] if len(lines[3])>1 else "")

                            row5 = st.columns(2)
                            with row5[0]:
                                e_s5 = st.text_input("Charger", value=lines[4][0] if len(lines)>4 else "")
                            with row5[1]:
                                e_s5_sn = st.text_input("S/N", value=lines[4][1] if len(lines[4])>1 else "")

                            e_desc = st.text_area("Description", value=row.get("Description",""), height=150)

                            if st.button("Save & Close", type="primary"):
                                new_spec = "\n".join([
                                    f"Genset model: {e_s1 or '—'} | S/N: {e_s1_sn or '—'}",
                                    f"Alternator Model: {e_s2 or '—'} | S/N: {e_s2_sn or '—'}",
                                    f"Controller: {e_s3 or '—'} | S/N: {e_s3_sn or '—'}",
                                    f"Circuit breaker Size: {e_s4 or '—'} | S/N: {e_s4_sn or '—'}",
                                    f"Charger: {e_s5 or '—'} | S/N: {e_s5_sn or '—'}"
                                ])
                                df.at[idx, "Project_Spec"] = new_spec
                                df.at[idx, "Description"] = e_desc or ""
                                save_projects()
                                st.cache_data.clear()
                                st.success("Specification 已更新！")
                                st.rerun()

                        if st.session_state.get(f"edit_spec_dialog_{idx}", False):
                            edit_spec_dialog(row, idx)

                        if st.form_submit_button("Save Changes", type="primary"):
                            if not e_name.strip():
                                st.error("Project Name required!")
                            else:
                                df.at[idx, "Project_Type"] = e_type
                                df.at[idx, "Project_Name"] = e_name
                                df.at[idx, "Year"] = int(e_year)
                                df.at[idx, "Lead_Time"] = e_leadtime
                                df.at[idx, "Customer"] = e_customer or ""
                                df.at[idx, "Supervisor"] = e_supervisor or ""
                                df.at[idx, "Qty"] = e_qty
                                df.at[idx, "Real_Count"] = e_qty
                                df.at[idx, "Progress_Reminder"] = e_reminder or ""
                                df.at[idx, "Parts_Arrival"] = e_d1
                                df.at[idx, "Installation_Complete"] = e_d2
                                df.at[idx, "Testing_Complete"] = e_d3
                                df.at[idx, "Cleaning_Complete"] = e_d4
                                df.at[idx, "Delivery_Complete"] = e_d5
                                save_projects()
                                st.cache_data.clear()
                                del st.session_state[f"editing_{idx}"]
                                st.success("Updated!")
                                st.rerun()

                if st.session_state.get(f"confirm_delete_{idx}", False):
                    st.warning(f"確定要刪除專案 **{row['Project_Name']}** 嗎？")
                    col_yes, col_no = st.columns(2)
                    if col_yes.button("Yes, Delete", type="primary"):
                        df = df.drop(idx).reset_index(drop=True)
                        save_projects()
                        checklist_db.pop(row["Project_Name"], None)
                        save_checklist()
                        st.cache_data.clear()
                        if f"confirm_delete_{idx}" in st.session_state:
                            del st.session_state[f"confirm_delete_{idx}"]
                        st.success("已刪除！")
                        st.rerun()
                    if col_no.button("Cancel"):
                        if f"confirm_delete_{idx}" in st.session_state:
                            del st.session_state[f"confirm_delete_{idx}"]
                        st.rerun()

st.markdown("---")
st.caption("Projects Management System")