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
# Google Sheets 連接 + 讀取
# ==============================================
conn = st.connection('gsheets', type=GSheetsConnection)

max_retries = 3
df = pd.DataFrame(columns=[
    "Project_Type","Project_Name","Year","Lead_Time","Customer","Supervisor",
    "Qty","Real_Count","Project_Spec","Description","Progress_Reminder",
    "Parts_Arrival","Installation_Complete","Testing_Complete","Cleaning_Complete","Delivery_Complete"
])

for attempt in range(max_retries):
    try:
        temp_df = conn.read(worksheet="projects", usecols=list(range(16)), ttl=300)
        if temp_df is not None and not temp_df.empty:
            temp_df = temp_df.dropna(how="all")
            df = temp_df
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
checklist_raw = pd.DataFrame()
for attempt in range(max_retries):
    try:
        checklist_raw = conn.read(worksheet="checklist", ttl=300)
        break
    except Exception:
        if attempt < max_retries - 1:
            time.sleep(5)

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
# 進度計算 + 顏色 + fmt
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

        # 解析 Project_Spec
        spec_text = row.get("Project_Spec", "")
        power_line = "Prime: — Standby: — — —"
        genset_line = alternator_line = controller_line = breaker_line = charger_line = "— | S/N: —"

        if spec_text and spec_text.strip():
            visible_part = spec_text.split("||EXTRA||")[0] if "||EXTRA||" in spec_text else spec_text

            # 提取 Prime / Standby / Hz / Voltage
            if "||EXTRA||" in spec_text:
                try:
                    extra_part = spec_text.split("||EXTRA||")[1]
                    extra_data = json.loads(extra_part.strip())
                    prime = f"{extra_data.get('prime','').strip()}kW" if extra_data.get('prime','').strip() else "—"
                    standby = f"{extra_data.get('standby','').strip()}kW" if extra_data.get('standby','').strip() else "—"
                    hz = f"{extra_data.get('hz','')}Hz" if extra_data.get('hz') else "—"
                    voltage = f"{extra_data.get('voltage','')}V" if extra_data.get('voltage') else "—"
                    power_line = f"Prime: {prime} Standby: {standby} {hz} {voltage}"
                except:
                    power_line = "Prime: — Standby: — — —"

            # 提取 5 項規格
            lines = visible_part.strip().split("\n")
            items = ["Genset model", "Alternator Model", "Controller", "Circuit breaker Size", "Charger"]
            for i, line in enumerate(lines):
                if i < len(items) and line.strip():
                    parts = line.split(" | S/N: ")
                    model_part = parts[0]
                    model = model_part.split(": ", 1)[1] if ": " in model_part else "—"
                    sn = parts[1] if len(parts) > 1 else "—"
                    if i == 0: genset_line = f"{model} | S/N: {sn}"
                    elif i == 1: alternator_line = f"{model} | S/N: {sn}"
                    elif i == 2: controller_line = f"{model} | S/N: {sn}"
                    elif i == 3: breaker_line = f"{model} | S/N: {sn}"
                    elif i == 4: charger_line = f"{model} | S/N: {sn}"

        st.markdown("**Project Specification:**")
        st.markdown(f"• {power_line}")
        st.markdown(f"• **Genset model:** {genset_line}")
        st.markdown(f"• **Alternator Model:** {alternator_line}")
        st.markdown(f"• **Controller:** {controller_line}")
        st.markdown(f"• **Circuit breaker Size:** {breaker_line}")
        st.markdown(f"• **Charger:** {charger_line}")

        # Description
        desc = row.get("Description", "")
        st.markdown(f"**Description:** {desc.strip() if not pd.isna(desc) and desc.strip() else '—'}")

        # Checklist Panel（保持不變）
        if st.button("Checklist Panel", key=f"cl_btn_{idx}", use_container_width=True):
            st.session_state[f"cl_open_{idx}"] = not st.session_state.get(f"cl_open_{idx}", False)

        if st.session_state.get(f"cl_open_{idx}", False):
            current = checklist_db.get(project_name, {"purchase": [], "done_p": [], "drawing": [], "done_d": []})
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

    # 按鈕區域
    col_spec, col_delete = st.columns(2)
    with col_spec:
        if st.button("Edit Project Spec.", key=f"spec_btn_{idx}", type="primary", use_container_width=True):
            st.session_state["current_edit_idx"] = idx
            st.session_state["show_edit_spec_dialog"] = True
            st.rerun()
    with col_delete:
        if st.button("Delete", key=f"del_{idx}", type="secondary", use_container_width=True):
            st.session_state["delete_idx"] = idx
            st.session_state["show_delete_confirm"] = True

    delete_placeholder = st.empty()
    if st.session_state.get("show_delete_confirm", False) and st.session_state.get("delete_idx") == idx:
        with delete_placeholder.container():
            st.markdown("---")
            st.warning(f"確定要刪除專案 **{row['Project_Name']}** 嗎？此動作無法復原！")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("確認刪除", type="primary", key=f"confirm_del_{idx}"):
                    df.drop(idx, inplace=True)
                    df.reset_index(drop=True, inplace=True)
                    save_projects()
                    checklist_db.pop(row["Project_Name"], None)
                    save_checklist()
                    st.cache_data.clear()
                    st.session_state["show_delete_confirm"] = False
                    st.success(f"已成功刪除專案：{row['Project_Name']}")
                    st.rerun()
            with col_no:
                if st.button("取消", key=f"cancel_del_{idx}"):
                    st.session_state["show_delete_confirm"] = False
                    st.rerun()
    else:
        delete_placeholder.empty()

# ==============================================
# Edit Project Specification Dialog
# ==============================================
if st.session_state.get("show_edit_spec_dialog", False):
    idx_to_edit = st.session_state["current_edit_idx"]
    row_to_edit = df.loc[idx_to_edit]

    @st.dialog("Edit Project Specification", width="large")
    def edit_spec_dialog():
        st.markdown(f"**Editing Specification for: {row_to_edit['Project_Name']}**")
        st.markdown("**請填寫完畢後按「Save & Close」儲存並關閉**")

        curr_spec = row_to_edit.get("Project_Spec", "")
        visible_spec = curr_spec.split("||EXTRA||")[0] if "||EXTRA||" in curr_spec else curr_spec
        extra_data = {"prime": "", "standby": "", "hz": "50", "voltage": "400"}
        if "||EXTRA||" in curr_spec:
            try:
                extra_data = json.loads(curr_spec.split("||EXTRA||")[1])
            except:
                pass

        lines = []
        if visible_spec.strip():
            for line in visible_spec.strip().split("\n"):
                if line.strip():
                    parts = line.split(" | S/N: ")
                    model_part = parts[0]
                    model = model_part.split(": ", 1)[1] if ": " in model_part else "—"
                    sn = parts[1] if len(parts) > 1 else "—"
                    lines.append([model, sn])
        while len(lines) < 5:
            lines.append(["—", "—"])

        # Prime / Standby / Hz / Voltage 在最上面
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            e_prime = st.text_input("Prime (KW)", value=extra_data.get("prime", ""), key=f"edit_prime_{idx_to_edit}")
            e_hz = st.selectbox("Hz", ["50", "60"], index=0 if extra_data.get("hz","50")=="50" else 1, key=f"edit_hz_{idx_to_edit}")
        with col_p2:
            e_standby = st.text_input("Standby (KW)", value=extra_data.get("standby", ""), key=f"edit_standby_{idx_to_edit}")
            e_voltage = st.selectbox("Voltage", ["380","400","415","440","480"],
                                     index=["380","400","415","440","480"].index(extra_data.get("voltage","400")),
                                     key=f"edit_voltage_{idx_to_edit}")

        st.markdown("---")

        # 原本 5 項規格
        row1 = st.columns(2)
        with row1[0]: e_s1 = st.text_input("Genset model(發動機型號)", value=lines[0][0], key=f"edit_genset_{idx_to_edit}")
        with row1[1]: e_s1_sn = st.text_input("S/N", value=lines[0][1], key=f"edit_genset_sn_{idx_to_edit}")

        row2 = st.columns(2)
        with row2[0]: e_s2 = st.text_input("Alternator Model(電球)", value=lines[1][0], key=f"edit_alternator_{idx_to_edit}")
        with row2[1]: e_s2_sn = st.text_input("S/N", value=lines[1][1], key=f"edit_alternator_sn_{idx_to_edit}")

        row3 = st.columns(2)
        with row3[0]: e_s3 = st.text_input("Controller(控制器)", value=lines[2][0], key=f"edit_controller_{idx_to_edit}")
        with row3[1]: e_s3_sn = st.text_input("S/N", value=lines[2][1], key=f"edit_controller_sn_{idx_to_edit}")

        row4 = st.columns(2)
        with row4[0]: e_s4 = st.text_input("Circuit breaker Size(斷路器)", value=lines[3][0], key=f"edit_breaker_{idx_to_edit}")
        with row4[1]: e_s4_sn = st.text_input("S/N", value=lines[3][1], key=f"edit_breaker_sn_{idx_to_edit}")

        row5 = st.columns(2)
        with row5[0]: e_s5 = st.text_input("Charger(充電機)", value=lines[4][0], key=f"edit_charger_{idx_to_edit}")
        with row5[1]: e_s5_sn = st.text_input("S/N", value=lines[4][1], key=f"edit_charger_sn_{idx_to_edit}")

        e_desc = st.text_area("Description", value=row_to_edit.get("Description","") or "", height=150, key=f"edit_desc_{idx_to_edit}")

        if st.button("Save & Close", type="primary", use_container_width=True):
            new_visible = "\n".join([
                f"Genset model: {e_s1 or '—'} | S/N: {e_s1_sn or '—'}",
                f"Alternator Model: {e_s2 or '—'} | S/N: {e_s2_sn or '—'}",
                f"Controller: {e_s3 or '—'} | S/N: {e_s3_sn or '—'}",
                f"Circuit breaker Size: {e_s4 or '—'} | S/N: {e_s4_sn or '—'}",
                f"Charger: {e_s5 or '—'} | S/N: {e_s5_sn or '—'}"
            ])
            extra_json = json.dumps({
                "prime": e_prime.strip(),
                "standby": e_standby.strip(),
                "hz": e_hz,
                "voltage": e_voltage
            })
            df.at[idx_to_edit, "Project_Spec"] = new_visible + "||EXTRA||" + extra_json
            df.at[idx_to_edit, "Description"] = e_desc.strip()

            with st.spinner("正在儲存至 Google Sheets，請稍候..."):
                save_projects()
                st.cache_data.clear()

            st.success("Specification 已成功更新！")
            st.session_state["show_edit_spec_dialog"] = False
            st.rerun()

    result = edit_spec_dialog()
    if result is None:
        pass

# ==============================================
# 左側側邊欄 & New Project
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
    search_term = st.text_input("Enter Project Name (partial match)", value="", key="search_input", label_visibility="collapsed")

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

        if st.form_submit_button("Add", type="primary", use_container_width=True):
            if not new_name.strip():
                st.error("Project Name required!")
            elif new_name in df["Project_Name"].values:
                st.error("Name exists!")
            else:
                spec_data = st.session_state.get("spec_data", {
                    "genset": "—", "genset_sn": "—", "alternator": "—", "alternator_sn": "—",
                    "controller": "—", "controller_sn": "—", "breaker": "—", "breaker_sn": "—",
                    "charger": "—", "charger_sn": "—",
                    "prime": "", "standby": "", "hz": "50", "voltage": "400", "desc": ""
                })

                visible_lines = [
                    f"Genset model: {spec_data['genset']} | S/N: {spec_data['genset_sn']}",
                    f"Alternator Model: {spec_data['alternator']} | S/N: {spec_data['alternator_sn']}",
                    f"Controller: {spec_data['controller']} | S/N: {spec_data['controller_sn']}",
                    f"Circuit breaker Size: {spec_data['breaker']} | S/N: {spec_data['breaker_sn']}",
                    f"Charger: {spec_data['charger']} | S/N: {spec_data['charger_sn']}"
                ]
                extra_json = json.dumps({
                    "prime": spec_data.get("prime", ""),
                    "standby": spec_data.get("standby", ""),
                    "hz": spec_data.get("hz", "50"),
                    "voltage": spec_data.get("voltage", "400")
                })
                spec_text = "\n".join(visible_lines) + "||EXTRA||" + extra_json

                new_project = {
                    "Project_Type": new_type, "Project_Name": new_name, "Year": int(new_year),
                    "Lead_Time": new_leadtime, "Customer": new_customer or "", "Supervisor": new_supervisor or "",
                    "Qty": new_qty, "Real_Count": new_qty, "Project_Spec": spec_text, "Description": spec_data.get("desc", ""),
                    "Progress_Reminder": reminder or "", "Parts_Arrival": d1, "Installation_Complete": d2,
                    "Testing_Complete": d3, "Cleaning_Complete": d4, "Delivery_Complete": d5
                }
                df = pd.concat([df, pd.DataFrame([new_project])], ignore_index=True)

                with st.spinner("正在新增專案並儲存至 Google Sheets，請稍候..."):
                    save_projects()
                    st.cache_data.clear()

                if "spec_data" in st.session_state:
                    del st.session_state.spec_data
                if "spec_dialog_open" in st.session_state:
                    del st.session_state.spec_dialog_open

                st.success(f"已成功新增專案：{new_name}")
                st.rerun()

    if st.button("Project Specification", type="primary", use_container_width=True):
        st.session_state.spec_dialog_open = True

    @st.dialog("Project Specification", width="large")
    def spec_dialog():
        st.markdown("**請填寫專案規格**")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            s_prime = st.text_input("Prime (KW)", key="dlg_prime")
            s_hz = st.selectbox("Hz", ["50", "60"], key="dlg_hz")
        with col_p2:
            s_standby = st.text_input("Standby (KW)", key="dlg_standby")
            s_voltage = st.selectbox("Voltage", ["380","400","415","440","480"], key="dlg_voltage")

        st.markdown("---")

        row1 = st.columns(2)
        with row1[0]: s_genset = st.text_input("Genset model(發動機型號)", key="dlg_new_genset")
        with row1[1]: s_genset_sn = st.text_input("S/N", key="dlg_new_genset_sn")

        row2 = st.columns(2)
        with row2[0]: s_alternator = st.text_input("Alternator Model(電球)", key="dlg_new_alternator")
        with row2[1]: s_alternator_sn = st.text_input("S/N", key="dlg_new_alternator_sn")

        row3 = st.columns(2)
        with row3[0]: s_controller = st.text_input("Controller(控制器)", key="dlg_new_controller")
        with row3[1]: s_controller_sn = st.text_input("S/N", key="dlg_new_controller_sn")

        row4 = st.columns(2)
        with row4[0]: s_breaker = st.text_input("Circuit breaker Size(斷路器)", key="dlg_new_breaker")
        with row4[1]: s_breaker_sn = st.text_input("S/N", key="dlg_new_breaker_sn")

        row5 = st.columns(2)
        with row5[0]: s_charger = st.text_input("Charger(充電機)", key="dlg_new_charger")
        with row5[1]: s_charger_sn = st.text_input("S/N", key="dlg_new_charger_sn")

        desc = st.text_area("Description", height=150, key="dlg_new_desc")

        if st.button("Save & Close", type="primary", use_container_width=True):
            st.session_state.spec_data = {
                "genset": s_genset or '—', "genset_sn": s_genset_sn or '—',
                "alternator": s_alternator or '—', "alternator_sn": s_alternator_sn or '—',
                "controller": s_controller or '—', "controller_sn": s_controller_sn or '—',
                "breaker": s_breaker or '—', "breaker_sn": s_breaker_sn or '—',
                "charger": s_charger or '—', "charger_sn": s_charger_sn or '—',
                "prime": s_prime.strip(), "standby": s_standby.strip(),
                "hz": s_hz, "voltage": s_voltage, "desc": desc.strip()
            }

            with st.spinner("正在儲存規格，請稍候..."):
                time.sleep(0.3)  # 讓 spinner 至少顯示一下

            st.success("規格已暫存，可繼續新增專案！")
            st.session_state.spec_dialog_open = False
            st.rerun()

    if st.session_state.get("spec_dialog_open", False):
        spec_dialog()

# ==============================================
# 篩選與主畫面
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

if st.session_state.view_mode == "calendar":
    # 原日曆程式碼保持不變
    st.stop()

st.markdown(f"<h1 style='text-align: center; color: #1fb429; margin-bottom: 30px; font-weight: bold;'>{page_title}</h1>", unsafe_allow_html=True)

if len(filtered_df) == 0:
    if st.session_state.view_mode == "delay":
        st.success("No delay projects! All on time!")
    else:
        st.info("No projects match the selected filters or search term.")
else:
    progress_series = filtered_df.apply(calculate_progress, axis=1)
    filtered_df = filtered_df.assign(Progress=progress_series).sort_values(by="Progress", ascending=False).drop(columns="Progress")

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
                render_project_card(rows[i], filtered_df.index[i])
        with col2:
            if i + 1 < len(rows):
                render_project_card(rows[i + 1], filtered_df.index[i + 1])

st.markdown("---")
st.caption("Projects Management System")