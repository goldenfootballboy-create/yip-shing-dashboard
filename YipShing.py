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
        visible_spec = spec_text.split("||EXTRA||")[0] if "||EXTRA||" in spec_text else spec_text
        extra_data = {}
        if "||EXTRA||" in spec_text:
            try:
                extra_data = json.loads(spec_text.split("||EXTRA||")[1])
            except:
                pass

        prime = extra_data.get("prime", "").strip() or "—"
        standby = extra_data.get("standby", "").strip() or "—"

        genset = alternator = panel = breaker_type = "—"
        genset_sn = alternator_sn = panel_sn = "—"

        breaker_rating = extra_data.get("breaker_rating", "—")
        poles = extra_data.get("poles", "—")
        spring_charging = extra_data.get("spring_charging", "—")
        control_voltage = extra_data.get("control_voltage", "—")

        lines = visible_spec.strip().split("\n") if visible_spec.strip() else []
        for line in lines:
            if "Genset model:" in line:
                parts = line.split(" | S/N: ")
                genset = parts[0].split(": ")[1] if ": " in parts[0] else "—"
                genset_sn = parts[1] if len(parts) > 1 else "—"
            elif "Alternator Model:" in line:
                parts = line.split(" | S/N: ")
                alternator = parts[0].split(": ")[1] if ": " in parts[0] else "—"
                alternator_sn = parts[1] if len(parts) > 1 else "—"
            elif "Panel model:" in line:
                parts = line.split(" | S/N: ")
                panel = parts[0].split(": ")[1] if ": " in parts[0] else "—"
                panel_sn = parts[1] if len(parts) > 1 else "—"
            elif "Breaker Type:" in line:
                breaker_type = line.split(": ")[1] if ": " in line else "—"

        st.markdown("**Project Specification:**")
        st.markdown(f"• Prime: {prime} Standby: {standby}")
        st.markdown(f"• **Genset model:** {genset} | S/N: {genset_sn}")
        st.markdown(f"• **Alternator Model:** {alternator} | S/N: {alternator_sn}")
        st.markdown(f"• **Panel model:** {panel} | S/N: {panel_sn}")
        st.markdown(f"• **Breaker Type:** {breaker_type} | S/N: —")
        st.markdown(f"• **Charger:** SmartGen 8A | S/N: — Breaker Rating: {breaker_rating} Poles: {poles} Spring Charging: {spring_charging} Control Voltage: {control_voltage}")

        # Description
        desc_raw = row.get("Description")
        if pd.isna(desc_raw):
            desc = "—"
        else:
            desc = str(desc_raw).strip() or "—"
        st.markdown(f"**Description:** {desc}")

        # Checklist Panel
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
# Edit Project Specification Dialog - 用橫線分區
# ==============================================
if st.session_state.get("show_edit_spec_dialog", False):
    idx_to_edit = st.session_state["current_edit_idx"]
    row_to_edit = df.loc[idx_to_edit]

    @st.dialog("Edit Project Specification", width="large")
    def edit_spec_dialog():
        st.markdown(f"**Editing Specification for: {row_to_edit['Project_Name']}**")

        curr_spec = row_to_edit.get("Project_Spec", "")
        visible_spec = curr_spec.split("||EXTRA||")[0] if "||EXTRA||" in curr_spec else curr_spec
        extra_data = {}
        if "||EXTRA||" in curr_spec:
            try:
                extra_data = json.loads(curr_spec.split("||EXTRA||")[1])
            except:
                pass

        def get(key, default=""):
            return extra_data.get(key, default)

        # Prime & Standby
        st.markdown("### Prime & Standby Power")
        col_ps = st.columns(2)
        with col_ps[0]:
            e_prime = st.text_input("Prime (kW)", value=get("prime", ""))
        with col_ps[1]:
            e_standby = st.text_input("Standby (kW)", value=get("standby", ""))

        st.markdown("---")

        # Engine 發動機
        st.markdown("**Engine 發動機**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            e_genset_model = st.text_input("Genset model(發動機型號)", value=get("genset_model", ""))
        with col2:
            e_genset_sn = st.text_input("S/N", value=get("genset_sn", ""))
        with col3:
            e_engine_color = st.text_input("Color(顏色)", value=get("engine_color", ""))
        with col4:
            e_engine_year = st.text_input("Year(年份)", value=get("engine_year", ""))
        e_engine_heater = st.text_input("Engine Heater(發動機加熱器) kW", value=get("engine_heater", ""))

        st.markdown("---")

        # Alternator (電球)
        st.markdown("**Alternator (電球)**")
        col1, col2, col3 = st.columns(3)
        with col1:
            e_alt_model = st.text_input("Alternator Model(電球型號)", value=get("alt_model", ""))
        with col2:
            e_alt_sn = st.text_input("S/N", value=get("alt_sn", ""))
        with col3:
            e_alt_color = st.text_input("Color(顏色)", value=get("alt_color", ""))
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            e_droop = st.selectbox("DroopKit", ["Include", "Not Include"], index=0 if get("droop", "Include") == "Include" else 1)
        with col_d2:
            e_pmg = st.text_input("PMG", value=get("pmg", ""))
        with col_d3:
            e_alt_heater = st.selectbox("Alternator Heater (交流發電機加熱器)", ["Include", "Not Include"], index=0 if get("alt_heater", "Include") == "Include" else 1)

        st.markdown("---")

        # Radiator (水箱)
        st.markdown("**Radiator (水箱)**")
        col1, col2, col3 = st.columns(3)
        with col1:
            e_rad_model = st.text_input("Radiator model(水箱型號)", value=get("rad_model", ""))
        with col2:
            e_rad_sn = st.text_input("S/N", value=get("rad_sn", ""))
        with col3:
            e_rad_temp = st.text_input("Temperature(温度)", value=get("rad_temp", ""))
        e_fan_size = st.text_input("風扇呎吋", value=get("fan_size", ""))
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            e_coolant_sensor = st.selectbox("Coolant temperature sensor", ["Include", "Not Include"], index=0 if get("coolant_sensor", "Include") == "Include" else 1)
        with col_s2:
            e_low_water = st.selectbox("Low water level float switch", ["Include", "Not Include"], index=0 if get("low_water", "Include") == "Include" else 1)

        st.markdown("---")

        # Base Frame (底架)
        st.markdown("**Base Frame (底架)**")
        e_base_model = st.text_input("Base Frame model(底架型號)", value=get("base_model", ""))
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            e_avm = st.text_input("Anti-Vibration Mount (避震腳)", value=get("avm", ""))
        with col_a2:
            e_avm_qty = st.number_input("Qty(數量)", min_value=0, value=int(get("avm_qty", 0)))

        st.markdown("---")

        # Container (貨櫃)
        st.markdown("**Container (貨櫃)**")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            e_cont_size = st.selectbox("Size(呎吋)", ["20'ftHQ", "20'ftGP"], index=0 if get("cont_size", "20'ftHQ") == "20'ftHQ" else 1)
        with col_c2:
            e_cont_type = st.selectbox("Type(種類)", ["FIEO", "Motorized"], index=0 if get("cont_type", "FIEO") == "FIEO" else 1)
        with col_c3:
            e_cont_color = st.text_input("Color(顏色)", value=get("cont_color", ""))
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            e_fork_slot = st.selectbox("是否帶叉槽位", ["Yes", "No"], index=0 if get("fork_slot", "Yes") == "Yes" else 1)
        with col_f2:
            e_anti_noise = st.selectbox("Anti-Noise(78-80Dba @7M 75% loading)", ["Yes", "No"], index=0 if get("anti_noise", "Yes") == "Yes" else 1)
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            e_internal_silencer = st.selectbox("Internal Silencer (內部消聲器)", ["Include", "Not Include"], index=0 if get("internal_silencer", "Include") == "Include" else 1)
        with col_i2:
            e_ss_locks = st.selectbox("304 Stainless Steel Door Locks & Hinges", ["Include", "Not Include"], index=0 if get("ss_locks", "Include") == "Include" else 1)
        e_emergency_stop = st.selectbox("Emergency Stop Button (緊急暫停)", ["Include", "Not Include"], index=0 if get("emergency_stop", "Include") == "Include" else 1)

        st.markdown("---")

        # Panel (控制器)
        st.markdown("**Panel (控制器)**")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            e_panel_model = st.text_input("Panel model(控制器型號)", value=get("panel_model", ""))
        with col_p2:
            e_panel_sn = st.text_input("S/N", value=get("panel_sn", ""))
        e_co_detector = st.selectbox("CO 探測器 (OLED)", ["Include", "Not Include"], index=0 if get("co_detector", "Include") == "Include" else 1)

        st.markdown("---")

        # Circuit Breaker (斷路器)
        st.markdown("**Circuit Breaker (斷路器)**")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            e_breaker_type = st.selectbox("Breaker Type (斷路器種類)", ["ACB", "MCCB"], index=0 if get("breaker_type", "ACB") == "ACB" else 1)
        with col_b2:
            e_breaker_rating = st.text_input("Breaker Rating (斷路器容量)", value=get("breaker_rating", ""))
        col_p3, col_p4 = st.columns(2)
        with col_p3:
            e_poles = st.selectbox("Poles(極數)", ["3P", "4P"], index=0 if get("poles", "3P") == "3P" else 1)
        with col_p4:
            e_spring_charging = st.selectbox("Spring Charging(斷路器操作)", ["Motorized", "Single Usage"], index=0 if get("spring_charging", "Motorized") == "Motorized" else 1)
        e_control_voltage = st.text_input("Control Voltage(控制電壓)", value=get("control_voltage", ""))

        e_desc = st.text_area("Description", value=row_to_edit.get("Description","") or "", height=150)

        if st.button("Save & Close", type="primary", use_container_width=True):
            new_visible = "\n".join([
                f"Genset model: {e_genset_model or '—'} | S/N: {e_genset_sn or '—'}",
                f"Alternator Model: {e_alt_model or '—'} | S/N: {e_alt_sn or '—'}",
                f"Panel model: {e_panel_model or '—'} | S/N: {e_panel_sn or '—'}",
                f"Breaker Type: {e_breaker_type or '—'}"
            ])

            extra_dict = {
                "prime": e_prime.strip(),
                "standby": e_standby.strip(),
                "genset_model": e_genset_model,
                "genset_sn": e_genset_sn,
                "engine_color": e_engine_color,
                "engine_year": e_engine_year,
                "engine_heater": e_engine_heater,
                "alt_model": e_alt_model,
                "alt_sn": e_alt_sn,
                "alt_color": e_alt_color,
                "droop": e_droop,
                "pmg": e_pmg,
                "alt_heater": e_alt_heater,
                "rad_model": e_rad_model,
                "rad_sn": e_rad_sn,
                "rad_temp": e_rad_temp,
                "fan_size": e_fan_size,
                "coolant_sensor": e_coolant_sensor,
                "low_water": e_low_water,
                "base_model": e_base_model,
                "avm": e_avm,
                "avm_qty": str(e_avm_qty),
                "cont_size": e_cont_size,
                "cont_type": e_cont_type,
                "cont_color": e_cont_color,
                "fork_slot": e_fork_slot,
                "anti_noise": e_anti_noise,
                "internal_silencer": e_internal_silencer,
                "ss_locks": e_ss_locks,
                "emergency_stop": e_emergency_stop,
                "panel_model": e_panel_model,
                "panel_sn": e_panel_sn,
                "co_detector": e_co_detector,
                "breaker_type": e_breaker_type,
                "breaker_rating": e_breaker_rating,
                "poles": e_poles,
                "spring_charging": e_spring_charging,
                "control_voltage": e_control_voltage
            }
            extra_json = json.dumps(extra_dict, ensure_ascii=False)

            df.at[idx_to_edit, "Project_Spec"] = new_visible + "||EXTRA||" + extra_json
            df.at[idx_to_edit, "Description"] = e_desc.strip()

            with st.spinner("正在儲存至 Google Sheets，請稍候..."):
                save_projects()
                st.cache_data.clear()

            st.success("Specification 已成功更新！")
            st.session_state["show_edit_spec_dialog"] = False
            st.rerun()

    edit_spec_dialog()

# ==============================================
# New Project Specification Dialog - 用橫線分區
# ==============================================
if st.sidebar.button("Project Specification", type="primary", use_container_width=True):
    st.session_state.spec_dialog_open = True

if st.session_state.get("spec_dialog_open", False):
    @st.dialog("Project Specification", width="large")
    def spec_dialog():
        st.markdown("**請填寫專案規格**")

        # Prime & Standby
        st.markdown("### Prime & Standby Power")
        col_ps = st.columns(2)
        with col_ps[0]:
            s_prime = st.text_input("Prime (kW)", key="dlg_prime")
        with col_ps[1]:
            s_standby = st.text_input("Standby (kW)", key="dlg_standby")

        st.markdown("---")

        # Engine 發動機
        st.markdown("**Engine 發動機**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            s_genset_model = st.text_input("Genset model(發動機型號)", key="dlg_genset_model")
        with col2:
            s_genset_sn = st.text_input("S/N", key="dlg_genset_sn")
        with col3:
            s_engine_color = st.text_input("Color(顏色)", key="dlg_engine_color")
        with col4:
            s_engine_year = st.text_input("Year(年份)", key="dlg_engine_year")
        s_engine_heater = st.text_input("Engine Heater(發動機加熱器) kW", key="dlg_engine_heater")

        st.markdown("---")

        # Alternator (電球)
        st.markdown("**Alternator (電球)**")
        col1, col2, col3 = st.columns(3)
        with col1:
            s_alt_model = st.text_input("Alternator Model(電球型號)", key="dlg_alt_model")
        with col2:
            s_alt_sn = st.text_input("S/N", key="dlg_alt_sn")
        with col3:
            s_alt_color = st.text_input("Color(顏色)", key="dlg_alt_color")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            s_droop = st.selectbox("DroopKit", ["Include", "Not Include"], key="dlg_droop")
        with col_d2:
            s_pmg = st.text_input("PMG", key="dlg_pmg")
        with col_d3:
            s_alt_heater = st.selectbox("Alternator Heater (交流發電機加熱器)", ["Include", "Not Include"], key="dlg_alt_heater")

        st.markdown("---")

        # Radiator (水箱)
        st.markdown("**Radiator (水箱)**")
        col1, col2, col3 = st.columns(3)
        with col1:
            s_rad_model = st.text_input("Radiator model(水箱型號)", key="dlg_rad_model")
        with col2:
            s_rad_sn = st.text_input("S/N", key="dlg_rad_sn")
        with col3:
            s_rad_temp = st.text_input("Temperature(温度)", key="dlg_rad_temp")
        s_fan_size = st.text_input("風扇呎吋", key="dlg_fan_size")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            s_coolant_sensor = st.selectbox("Coolant temperature sensor", ["Include", "Not Include"], key="dlg_coolant_sensor")
        with col_s2:
            s_low_water = st.selectbox("Low water level float switch", ["Include", "Not Include"], key="dlg_low_water")

        st.markdown("---")

        # Base Frame (底架)
        st.markdown("**Base Frame (底架)**")
        s_base_model = st.text_input("Base Frame model(底架型號)", key="dlg_base_model")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            s_avm = st.text_input("Anti-Vibration Mount (避震腳)", key="dlg_avm")
        with col_a2:
            s_avm_qty = st.number_input("Qty(數量)", min_value=0, value=0, key="dlg_avm_qty")

        st.markdown("---")

        # Container (貨櫃)
        st.markdown("**Container (貨櫃)**")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            s_cont_size = st.selectbox("Size(呎吋)", ["20'ftHQ", "20'ftGP"], key="dlg_cont_size")
        with col_c2:
            s_cont_type = st.selectbox("Type(種類)", ["FIEO", "Motorized"], key="dlg_cont_type")
        with col_c3:
            s_cont_color = st.text_input("Color(顏色)", key="dlg_cont_color")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            s_fork_slot = st.selectbox("是否帶叉槽位", ["Yes", "No"], key="dlg_fork_slot")
        with col_f2:
            s_anti_noise = st.selectbox("Anti-Noise(78-80Dba @7M 75% loading)", ["Yes", "No"], key="dlg_anti_noise")
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            s_internal_silencer = st.selectbox("Internal Silencer (內部消聲器)", ["Include", "Not Include"], key="dlg_internal_silencer")
        with col_i2:
            s_ss_locks = st.selectbox("304 Stainless Steel Door Locks & Hinges", ["Include", "Not Include"], key="dlg_ss_locks")
        s_emergency_stop = st.selectbox("Emergency Stop Button (緊急暫停)", ["Include", "Not Include"], key="dlg_emergency_stop")

        st.markdown("---")

        # Panel (控制器)
        st.markdown("**Panel (控制器)**")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            s_panel_model = st.text_input("Panel model(控制器型號)", key="dlg_panel_model")
        with col_p2:
            s_panel_sn = st.text_input("S/N", key="dlg_panel_sn")
        s_co_detector = st.selectbox("CO 探測器 (OLED)", ["Include", "Not Include"], key="dlg_co_detector")

        st.markdown("---")

        # Circuit Breaker (斷路器)
        st.markdown("**Circuit Breaker (斷路器)**")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            s_breaker_type = st.selectbox("Breaker Type (斷路器種類)", ["ACB", "MCCB"], key="dlg_breaker_type")
        with col_b2:
            s_breaker_rating = st.text_input("Breaker Rating (斷路器容量)", key="dlg_breaker_rating")
        col_p3, col_p4 = st.columns(2)
        with col_p3:
            s_poles = st.selectbox("Poles(極數)", ["3P", "4P"], key="dlg_poles")
        with col_p4:
            s_spring_charging = st.selectbox("Spring Charging(斷路器操作)", ["Motorized", "Single Usage"], key="dlg_spring_charging")
        s_control_voltage = st.text_input("Control Voltage(控制電壓)", key="dlg_control_voltage")

        desc = st.text_area("Description", height=150, key="dlg_desc")

        if st.button("Save & Close", type="primary", use_container_width=True):
            st.session_state.spec_data = {
                "prime": s_prime.strip(),
                "standby": s_standby.strip(),
                "genset_model": s_genset_model,
                "genset_sn": s_genset_sn,
                "engine_color": s_engine_color,
                "engine_year": s_engine_year,
                "engine_heater": s_engine_heater,
                "alt_model": s_alt_model,
                "alt_sn": s_alt_sn,
                "alt_color": s_alt_color,
                "droop": s_droop,
                "pmg": s_pmg,
                "alt_heater": s_alt_heater,
                "rad_model": s_rad_model,
                "rad_sn": s_rad_sn,
                "rad_temp": s_rad_temp,
                "fan_size": s_fan_size,
                "coolant_sensor": s_coolant_sensor,
                "low_water": s_low_water,
                "base_model": s_base_model,
                "avm": s_avm,
                "avm_qty": str(s_avm_qty),
                "cont_size": s_cont_size,
                "cont_type": s_cont_type,
                "cont_color": s_cont_color,
                "fork_slot": s_fork_slot,
                "anti_noise": s_anti_noise,
                "internal_silencer": s_internal_silencer,
                "ss_locks": s_ss_locks,
                "emergency_stop": s_emergency_stop,
                "panel_model": s_panel_model,
                "panel_sn": s_panel_sn,
                "co_detector": s_co_detector,
                "breaker_type": s_breaker_type,
                "breaker_rating": s_breaker_rating,
                "poles": s_poles,
                "spring_charging": s_spring_charging,
                "control_voltage": s_control_voltage,
                "desc": desc.strip()
            }

            st.success("規格已暫存，可繼續新增專案！")
            st.session_state.spec_dialog_open = False
            st.rerun()

    spec_dialog()

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
                spec_data = st.session_state.get("spec_data", {})

                visible_lines = [
                    f"Genset model: {spec_data.get('genset_model', '—')} | S/N: {spec_data.get('genset_sn', '—')}",
                    f"Alternator Model: {spec_data.get('alt_model', '—')} | S/N: {spec_data.get('alt_sn', '—')}",
                    f"Panel model: {spec_data.get('panel_model', '—')} | S/N: {spec_data.get('panel_sn', '—')}",
                    f"Breaker Type: {spec_data.get('breaker_type', '—')}"
                ]
                extra_json = json.dumps(spec_data, ensure_ascii=False)
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

# ==============================================
# 篩選邏輯 & 主畫面
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
    # 原日曆程式碼（保持不變）
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