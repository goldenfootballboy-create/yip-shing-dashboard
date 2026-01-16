import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import date
import time
from streamlit_calendar import calendar

# 全局安全 index 函數（防止 selectbox index 錯誤）
def safe_index(val, options, default=0):
    try:
        return options.index(val)
    except ValueError:
        return default

def fullscreen_loading(message="正在處理，請稍候..."):
    st.markdown(f"""
    <div style="
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        color: white;
        font-size: 1.8rem;
        font-weight: bold;
    ">
        <div style="
            border: 12px solid #f3f3f3;
            border-top: 12px solid #1fb429;
            border-radius: 50%;
            width: 100px;
            height: 100px;
            animation: spin 1s linear infinite;
            margin-bottom: 30px;
        "></div>
        <div>{message}</div>
    </div>
    <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
    """, unsafe_allow_html=True)

# ==============================================
# 頁面設定
# ==============================================
st.set_page_config(
    page_title="YIP SHING Project Dashboard",
    page_icon="https://i.imgur.com/Q8ehtk3.jpeg",
    layout="wide"
)

# 初始化 dialog active flags（防止重複彈出）
if "dialog_active" not in st.session_state:
    st.session_state.dialog_active = None

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
            "Qty","Real_Count","Project_Spec","Progress_Reminder",
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

# 讀取 checklist（保留原功能，與專案無關）
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

        # 讀取規格
        spec_text = row.get("Project_Spec", "")
        specs = []
        if spec_text:
            try:
                if "||EXTRA||" in spec_text:
                    extra_json = spec_text.split("||EXTRA||")[1]
                    specs = json.loads(extra_json)
                    if not isinstance(specs, list):
                        specs = [specs]
                else:
                    extra_data = json.loads(spec_text)
                    specs = [extra_data]
            except:
                specs = []

        qty = row.get("Qty", 1)
        if len(specs) < qty:
            specs += [{}] * (qty - len(specs))

        # 顯示規格
        if qty == 1:
            spec = specs[0] if specs else {}
            st.markdown("**Project Specification:**")
            st.markdown(f"• Prime: {spec.get('prime', '—')} Standby: {spec.get('standby', '—')}")
            st.markdown(f"• Voltage: {spec.get('voltage', '—')} Frequency: {spec.get('frequency', '—')} RPM: {spec.get('rpm', '—')}")
            st.markdown(f"• **Genset model:** {spec.get('genset_model', '—')} | S/N: {spec.get('genset_sn', '—')}")
            st.markdown(f"• **Alternator Model:** {spec.get('alt_model', '—')} | S/N: {spec.get('alt_sn', '—')}")
            st.markdown(f"• **Panel model:** {spec.get('panel_model', '—')} | S/N: {spec.get('panel_sn', '—')}")
            st.markdown(f"• **Breaker Type:** {spec.get('breaker_type', '—')} | Breaker Rating: {spec.get('breaker_rating', '—')} Poles: {spec.get('poles', '—')}")
            st.markdown(f"• Spring Charging: {spec.get('spring_charging', '—')} Control Voltage: {spec.get('control_voltage', '—')}")
            st.markdown(f"**Remarks:**")
            st.markdown(f"{spec.get('remarks', '—')}")
        else:
            tabs = st.tabs([f"第 {i+1} 台" for i in range(qty)])
            for i in range(qty):
                with tabs[i]:
                    spec = specs[i] if i < len(specs) else {}
                    st.markdown("**Project Specification:**")
                    st.markdown(f"• Prime: {spec.get('prime', '—')} Standby: {spec.get('standby', '—')}")
                    st.markdown(f"• Voltage: {spec.get('voltage', '—')} Frequency: {spec.get('frequency', '—')} RPM: {spec.get('rpm', '—')}")
                    st.markdown(f"• **Genset model:** {spec.get('genset_model', '—')} | S/N: {spec.get('genset_sn', '—')}")
                    st.markdown(f"• **Alternator Model:** {spec.get('alt_model', '—')} | S/N: {spec.get('alt_sn', '—')}")
                    st.markdown(f"• **Panel model:** {spec.get('panel_model', '—')} | S/N: {spec.get('panel_sn', '—')}")
                    st.markdown(f"• **Breaker Type:** {spec.get('breaker_type', '—')} | Breaker Rating: {spec.get('breaker_rating', '—')} Poles: {spec.get('poles', '—')}")
                    st.markdown(f"• Spring Charging: {spec.get('spring_charging', '—')} Control Voltage: {spec.get('control_voltage', '—')}")
                    st.markdown(f"**Remarks:**")
                    st.markdown(f"{spec.get('remarks', '—')}")

        # ────────────────────────────────────────────────────────────────
        #  Overview 按鈕 – 彈出完整唯讀規格總覽視窗
        # ────────────────────────────────────────────────────────────────
        if st.button("📊 OverView 完整規格總覽",
                     key=f"overall_spec_btn_{idx}",
                     use_container_width=True,
                     type="secondary",
                     help="點擊查看所有台的完整規格細節（唯讀模式）"):

            @st.dialog(f"完整規格總覽 – {row['Project_Name']} ({qty} 台)", width="large")
            def overall_spec_overview():
                st.markdown(f"**專案：{row['Project_Name']}**　｜　**{qty} 台**　｜　**類型：{row['Project_Type']}**")
                st.markdown("---")

                # 讀取規格資料
                spec_text = row.get("Project_Spec", "")
                specs = []
                if "||EXTRA||" in spec_text:
                    try:
                        extra_json = spec_text.split("||EXTRA||")[1]
                        specs = json.loads(extra_json)
                        if not isinstance(specs, list):
                            specs = [specs]
                    except:
                        specs = []
                else:
                    specs = []

                if len(specs) < qty:
                    specs += [{}] * (qty - len(specs))

                overview_tabs = st.tabs([f"第 {i + 1} 台" for i in range(qty)])

                for machine_idx in range(qty):
                    with overview_tabs[machine_idx]:
                        spec = specs[machine_idx] if machine_idx < len(specs) else {}

                        # ── Prime & Standby ─────────────────────────────────────
                        st.markdown(
                            """<h3 style="color: #1e88e5; margin-bottom: 0.5rem; font-weight: bold;">
                            Prime & Standby Power (功效＆電壓)
                            </h3>""",
                            unsafe_allow_html=True
                        )
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Prime (kW)", spec.get('prime', '—'))
                        c2.metric("Standby (kW)", spec.get('standby', '—'))
                        c3.metric("RPM", spec.get('rpm', '—'))

                        st.markdown(f"**電壓 / 頻率**： {spec.get('voltage', '—')} / {spec.get('frequency', '—')}")

                        st.divider()

                        # ── Engine & Alternator ────────────────────────────────
                        st.markdown(
                            """<h3 style="color: #1e88e5; margin-bottom: 0.5rem; font-weight: bold;">
                            Engine & Alternator (發動機 & 電球)
                            </h3>""",
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"**發動機型號**： {spec.get('genset_model', '—')}　　**S/N**： {spec.get('genset_sn', '—')}")
                        st.markdown(
                            f"**發動機顏色**： {spec.get('engine_color', '—')}　　**年份**： {spec.get('engine_year', '—')}")
                        st.markdown(f"**發動機加熱器**： {spec.get('engine_heater', '—')} kW")
                        st.markdown("    ")
                        st.markdown(f"**電球型號**： {spec.get('alt_model', '—')}　　**S/N**： {spec.get('alt_sn', '—')}")
                        st.markdown(f"**電球顏色**： {spec.get('alt_color', '—')}")
                        st.markdown(
                            f"**Droop**： {spec.get('droop', '—')}　　**PMG**： {spec.get('pmg', '—')}　　**加熱器**： {spec.get('alt_heater', '—')}")

                        st.divider()

                        # ── Radiator & Base ─────────────────────────────────────
                        st.markdown(
                            """<h3 style="color: #1e88e5; margin-bottom: 0.5rem; font-weight: bold;">
                            Radiator & Base Frame (水箱 & 底架)
                            </h3>""",
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"**水箱型號**： {spec.get('rad_model', '—')}　　"
                            f"**S/N**： {spec.get('rad_sn', '—')}　　"
                            f"**溫度**： {spec.get('rad_temp', '—')}"
                        )
                        st.markdown(f"**風扇呎吋**： {spec.get('fan_size', '—')}")
                        st.markdown(f"**水箱護罩**： {spec.get('radiator_guard', '—')}")

                        st.markdown("---")

                        # Fuel Cooler (帶貨源)
                        st.markdown(
                            f"**燃油冷卻器**： {spec.get('fuel_cooler', '—')}　　"
                            f"**貨源**： {spec.get('fuel_cooler_source', '—') or '—'}"
                        )

                        # Coolant temperature sensor (帶貨源)
                        st.markdown(
                            f"**冷卻液溫度感測器**： {spec.get('coolant_sensor', '—')}　　"
                            f"**貨源**： {spec.get('coolant_sensor_source', '—') or '—'}"
                        )

                        # Low water level float switch (帶貨源)
                        st.markdown(
                            f"**低水位浮球開關**： {spec.get('low_water', '—')}　　"
                            f"**貨源**： {spec.get('low_water_source', '—') or '—'}"
                        )
                        st.markdown(f"**底架型號**： {spec.get('base_model', '—')}　　**S/N**： {spec.get('base_sn', '—')}")
                        st.markdown(
                            f"**避震器**： {spec.get('avm', '—')}　數量：{spec.get('avm_qty', '—')}　型號：{spec.get('avm_model', '—')}")

                        st.divider()

                        # ── Container / Panel / Breaker ────────────────────────
                        st.markdown(
                            """<h3 style="color: #1e88e5; margin-bottom: 0.5rem; font-weight: bold;">
                            Container / Panel / Breaker (貨櫃 & 控制器＆斷路器)
                            </h3>""",
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"**貨櫃尺寸**： {spec.get('cont_size', '—')}　　**類型**： {spec.get('cont_type', '—')}")
                        st.markdown(
                            f"**控制器型號**： {spec.get('panel_model', '—')}　　**S/N**： {spec.get('panel_sn', '—')}")
                        st.markdown(
                            f"**斷路器**： {spec.get('breaker_type', '—')}　{spec.get('breaker_rating', '—')}　{spec.get('poles', '—')}")
                        st.markdown(
                            f"**彈簧充電**： {spec.get('spring_charging', '—')}　　**控制電壓**： {spec.get('control_voltage', '—')}")

                        st.divider()

                        # ── Parts ───────────────────────────────────────────────
                        parts = spec.get("parts", [])
                        if parts:
                            st.subheader("配件清單")
                            for p in parts:
                                name = p.get("name", "").strip()
                                source = p.get("source", "—")
                                if name:
                                    st.markdown(f"- **{name}**　（貨源：{source}）")

                        st.divider()

                        # Remarks
                        remarks = spec.get("remarks", "").strip()
                        if remarks:
                            st.subheader("備註")
                            st.info(remarks)

                # 關閉按鈕
                st.markdown("---")
                if st.button("關閉", type="primary", use_container_width=True):
                    st.rerun()

            overall_spec_overview()

        # Checklist Panel（保留原功能，與專案無關）
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
    col_edit_spec, col_edit_info, col_delete = st.columns(3)
    with col_edit_spec:
        if st.button("Edit Project Spec.", key=f"spec_btn_{idx}", type="primary", use_container_width=True):
            st.session_state["current_edit_idx"] = idx
            st.session_state["show_edit_spec_dialog"] = True
            st.rerun()
    with col_edit_info:
        if st.button("Edit Info.", key=f"info_btn_{idx}", type="secondary", use_container_width=True):
            st.session_state["current_edit_idx"] = idx
            st.session_state["show_edit_info_dialog"] = True
            st.rerun()
    with col_delete:
        if st.button("Delete", key=f"del_{idx}", type="secondary", use_container_width=True):
            st.session_state["delete_idx"] = idx
            st.session_state["show_delete_confirm"] = True

    # Delete 確認
    delete_placeholder = st.empty()
    if st.session_state.get("show_delete_confirm", False) and st.session_state.get("delete_idx") == idx:
        with delete_placeholder.container():
            st.markdown("---")
            st.warning(f"確定要刪除專案 **{row['Project_Name']}** 嗎？此動作無法復原！")
            col_yes, col_no = st.columns(2)
            with col_yes:
                delete_disabled = st.session_state.get(f"deleting_{idx}", False)
                if st.button("確認刪除", type="primary", key=f"confirm_del_{idx}", disabled=delete_disabled):
                    st.session_state[f"deleting_{idx}"] = True
                    st.rerun()
            with col_no:
                if st.button("取消", key=f"cancel_del_{idx}"):
                    st.session_state["show_delete_confirm"] = False
                    st.rerun()

        # 全屏 loading + 執行刪除
        if st.session_state.get(f"deleting_{idx}", False):
            fullscreen_loading("正在刪除專案，請稍候...")

            df.drop(idx, inplace=True)
            df.reset_index(drop=True, inplace=True)
            save_projects()
            checklist_db.pop(row["Project_Name"], None)
            save_checklist()
            st.cache_data.clear()
            st.session_state["show_delete_confirm"] = False
            st.session_state[f"deleting_{idx}"] = False
            st.success(f"已成功刪除專案：{row['Project_Name']}")
            st.rerun()

# ==============================================
# Edit Project Specification Dialog - 最終修正版（已移除 Delivery Checklist）
# ==============================================
if st.session_state.get("show_edit_spec_dialog", False):
    if st.session_state.dialog_active != "edit_spec":
        st.session_state.dialog_active = "edit_spec"
        st.rerun()

    idx_to_edit = st.session_state["current_edit_idx"]
    row_to_edit = df.loc[idx_to_edit]
    qty = row_to_edit["Qty"]
    project_type = row_to_edit["Project_Type"]
    is_open_or_marine = project_type in ["Open Set", "Marine"]

    spec_text = row_to_edit.get("Project_Spec", "")
    if "||EXTRA||" in spec_text:
        try:
            extra_json = spec_text.split("||EXTRA||")[1]
            specs = json.loads(extra_json)
            if not isinstance(specs, list):
                specs = [specs]
        except:
            specs = [{} for _ in range(qty)]
    else:
        specs = [{} for _ in range(qty)]

    if len(specs) < qty:
        specs += [{} for _ in range(qty - len(specs))]

    @st.dialog("Edit Project Specification", width="large")
    def edit_spec_dialog():

        st.markdown(f"**正在編輯專案：{row_to_edit['Project_Name']} ({qty} 台機器)**")
        st.markdown(
            """
            <style>
            div[data-testid="column"] {
                display: flex !important;
                align-items: center !important;
            }
            div[data-testid="column"] div[data-testid="stTextInput"],
            div[data-testid="column"] div[data-testid="stSelectbox"] {
                width: 100%;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        tabs = st.tabs([f"第 {i+1} 台" for i in range(qty)])

        new_specs = []
        if qty > 1:
            st.markdown("---")
            st.markdown("### 規格快速複製工具")
            if st.button("📋 從第 1 台複製規格 → 所有其他台",
                         type="primary",
                         use_container_width=True,
                         help="點擊後會把目前第1台已填寫的規格，複製到第2台～最後一台"):

                source_i = 0

                static_fields = [
                    "prime", "standby", "voltage", "frequency", "rpm",
                    "genset_model", "engine_color", "engine_year", "engine_heater", "engine_source",
                    "alt_model", "alt_color", "droop", "pmg", "alt_heater", "alt_source",
                    "rad_model", "rad_temp", "fan_size", "rad_source", "radiator_guard",
                    "fuel_cooler", "fuel_cooler_source",
                    "coolant_sensor", "coolant_sensor_source",
                    "low_water", "low_water_source",
                    "base_model", "base_source",
                    "avm", "avm_model", "avm_qty", "avm_source",
                    "cont_size", "cont_type", "cont_color", "fork_slot", "anti_noise",
                    "internal_silencer", "ss_locks", "emergency_stop", "cont_source",
                    "panel_model", "co_detector", "panel_source", "co_source",
                    "breaker_type", "breaker_rating", "poles", "spring_charging", "control_voltage", "breaker_source",
                    "remarks"
                ]

                for field in static_fields:
                    src_key = f"edit_{field}_{idx_to_edit}_{source_i}"
                    if src_key in st.session_state:
                        value = st.session_state[src_key]
                        for target_i in range(1, qty):
                            target_key = f"edit_{field}_{idx_to_edit}_{target_i}"
                            st.session_state[target_key] = value

                src_parts_key = f"parts_edit_{row_to_edit['Project_Name']}_{source_i}"
                if src_parts_key in st.session_state and st.session_state[src_parts_key]:
                    copied_parts = [p.copy() for p in st.session_state[src_parts_key]]
                    for target_i in range(1, qty):
                        st.session_state[f"parts_edit_{row_to_edit['Project_Name']}_{target_i}"] = copied_parts

                st.success("已成功將第 1 台的規格複製到其他所有台！")
                st.rerun()

        for i in range(qty):
            with tabs[i]:
                current = specs[i] if i < len(specs) else {}

                # Prime & Standby Power
                st.markdown("### Prime & Standby Power")
                col1, col2 = st.columns(2)
                with col1:
                    e_prime = st.text_input("Prime (kW)", value=current.get("prime", ""), key=f"edit_prime_{idx_to_edit}_{i}")
                    e_voltage = st.selectbox("Voltage(電壓)", ["--", "380", "400", "415", "440", "480","Muti-Voltage"],
                                             index=safe_index(current.get("voltage", "--"), ["--", "380", "400", "415", "440", "480","Muti-Voltage"]),
                                             key=f"edit_voltage_{idx_to_edit}_{i}")
                    e_frequency = st.selectbox("Frequency(頻率)", ["--", "50Hz", "60Hz","50Hz&60Hz"],
                                               index=safe_index(current.get("frequency", "--"), ["--", "50Hz", "60Hz","50Hz&60Hz"]),
                                               key=f"edit_frequency_{idx_to_edit}_{i}")
                with col2:
                    e_standby = st.text_input("Standby (kW)", value=current.get("standby", ""), key=f"edit_standby_{idx_to_edit}_{i}")
                    e_rpm = st.selectbox("RPM(轉速)", ["--", "1500", "1800","1500&1800"],
                                         index=safe_index(current.get("rpm", "--"), ["--", "1500", "1800","1500&1800"]),
                                         key=f"edit_rpm_{idx_to_edit}_{i}")

                st.markdown("---")

                # Engine & Alternator Group
                with st.expander("Engine & Alternator Group(發動機＆電球)", expanded=True):
                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Engine 發動機**")
                    with col_source:
                        e_engine_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                       index=safe_index(current.get("engine_source", "--"), ["--", "HK", "DG"]),
                                                       key=f"edit_engine_source_{idx_to_edit}_{i}",
                                                       label_visibility="collapsed")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        e_genset_model = st.text_input("Genset model(發動機型號)", value=current.get("genset_model", ""), key=f"edit_genset_model_{idx_to_edit}_{i}")
                    with col2:
                        e_genset_sn = st.text_input("S/N", value=current.get("genset_sn", ""), key=f"edit_genset_sn_{idx_to_edit}_{i}")
                    with col3:
                        e_engine_color = st.text_input("Color(顏色)", value=current.get("engine_color", ""), key=f"edit_engine_color_{idx_to_edit}_{i}")
                    with col4:
                        e_engine_year = st.text_input("Year(年份)", value=current.get("engine_year", ""), key=f"edit_engine_year_{idx_to_edit}_{i}")
                    e_engine_heater = st.text_input("Engine Heater(發動機加熱器) kW", value=current.get("engine_heater", ""), key=f"edit_engine_heater_{idx_to_edit}_{i}")

                    st.markdown("---")

                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Alternator (電球)**")
                    with col_source:
                        e_alt_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                    index=safe_index(current.get("alt_source", "--"), ["--", "HK", "DG"]),
                                                    key=f"edit_alt_source_{idx_to_edit}_{i}",
                                                    label_visibility="collapsed")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        e_alt_model = st.text_input("Alternator Model(電球型號)", value=current.get("alt_model", ""), key=f"edit_alt_model_{idx_to_edit}_{i}")
                    with col2:
                        e_alt_sn = st.text_input("S/N", value=current.get("alt_sn", ""), key=f"edit_alt_sn_{idx_to_edit}_{i}")
                    with col3:
                        e_alt_color = st.text_input("Color(顏色)", value=current.get("alt_color", ""), key=f"edit_alt_color_{idx_to_edit}_{i}")
                    col_d1, col_d2, col_d3 = st.columns(3)
                    with col_d1:
                        e_droop = st.selectbox("DroopKit", ["--", "Include", "Not Include"], index=safe_index(current.get("droop", "--"), ["--", "Include", "Not Include"]), key=f"edit_droop_{idx_to_edit}_{i}")
                    with col_d2:
                        e_pmg = st.text_input("PMG", value=current.get("pmg", ""), key=f"edit_pmg_{idx_to_edit}_{i}")
                    with col_d3:
                        e_alt_heater = st.selectbox("Alternator Heater", ["--", "Include", "Not Include"], index=safe_index(current.get("alt_heater", "--"), ["--", "Include", "Not Include"]), key=f"edit_alt_heater_{idx_to_edit}_{i}")

                st.markdown("---")

                # Radiator & Base Frame Group
                with st.expander("Radiator & Base Frame Group(水箱＆底架)", expanded=False):
                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Radiator (水箱)**")
                    with col_source:
                        e_rad_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                    index=safe_index(current.get("rad_source", "--"), ["--", "HK", "DG"]),
                                                    key=f"edit_rad_source_{idx_to_edit}_{i}",
                                                    label_visibility="collapsed")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        e_rad_model = st.text_input("Radiator model(水箱型號)", value=current.get("rad_model", ""), key=f"edit_rad_model_{idx_to_edit}_{i}")
                    with col2:
                        e_rad_sn = st.text_input("S/N", value=current.get("rad_sn", ""), key=f"edit_rad_sn_{idx_to_edit}_{i}")
                    with col3:
                        e_rad_temp = st.text_input("Temperature(温度)", value=current.get("rad_temp", ""), key=f"edit_rad_temp_{idx_to_edit}_{i}")
                    e_fan_size = st.text_input("風扇呎吋", value=current.get("fan_size", ""), key=f"edit_fan_size_{idx_to_edit}_{i}")

                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        e_radiator_guard = st.selectbox("Radiator Guard (水箱護罩)", ["--", "Include", "Not Include"],
                                                        index=safe_index(current.get("radiator_guard", "--"), ["--", "Include", "Not Include"]),
                                                        key=f"edit_radiator_guard_{idx_to_edit}_{i}")

                    col_title, col_include, col_source = st.columns([5, 1, 1])
                    with col_title:
                        st.markdown("**Fuel Cooler (燃油冷卻器)**")
                    with col_include:
                        e_fuel_cooler = st.selectbox("", ["--", "Include", "Not Include"],
                                                     index=safe_index(current.get("fuel_cooler", "--"), ["--", "Include", "Not Include"]),
                                                     key=f"edit_fuel_cooler_{idx_to_edit}_{i}",
                                                     label_visibility="collapsed")
                    with col_source:
                        e_fuel_cooler_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                            index=safe_index(current.get("fuel_cooler_source", "--"), ["--", "HK", "DG"]),
                                                            key=f"edit_fuel_cooler_source_{idx_to_edit}_{i}",
                                                            label_visibility="collapsed")

                    col_title, col_include, col_source = st.columns([5, 1, 1])
                    with col_title:
                        st.markdown("**Coolant temperature sensor**")
                    with col_include:
                        e_coolant_sensor = st.selectbox("", ["--", "Include", "Not Include"],
                                                        index=safe_index(current.get("coolant_sensor", "--"), ["--", "Include", "Not Include"]),
                                                        key=f"edit_coolant_sensor_{idx_to_edit}_{i}",
                                                        label_visibility="collapsed")
                    with col_source:
                        e_coolant_sensor_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                               index=safe_index(current.get("coolant_sensor_source", "--"), ["--", "HK", "DG"]),
                                                               key=f"edit_coolant_sensor_source_{idx_to_edit}_{i}",
                                                               label_visibility="collapsed")

                    col_title, col_include, col_source = st.columns([5, 1, 1])
                    with col_title:
                        st.markdown("**Low water level float switch**")
                    with col_include:
                        e_low_water = st.selectbox("", ["--", "Include", "Not Include"],
                                                   index=safe_index(current.get("low_water", "--"), ["--", "Include", "Not Include"]),
                                                   key=f"edit_low_water_{idx_to_edit}_{i}",
                                                   label_visibility="collapsed")
                    with col_source:
                        e_low_water_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                          index=safe_index(current.get("low_water_source", "--"), ["--", "HK", "DG"]),
                                                          key=f"edit_low_water_source_{idx_to_edit}_{i}",
                                                          label_visibility="collapsed")

                    st.markdown("---")

                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Base Frame (底架)**")
                    with col_source:
                        e_base_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                     index=safe_index(current.get("base_source", "--"), ["--", "HK", "DG"]),
                                                     key=f"edit_base_source_{idx_to_edit}_{i}",
                                                     label_visibility="collapsed")

                    col_model, col_sn = st.columns(2)
                    with col_model:
                        e_base_model = st.text_input("Base Frame model(底架型號)", value=current.get("base_model", ""), key=f"edit_base_model_{idx_to_edit}_{i}")
                    with col_sn:
                        e_base_sn = st.text_input("S/N", value=current.get("base_sn", ""), key=f"edit_base_sn_{idx_to_edit}_{i}")

                    col_title, col_include, col_source = st.columns([5, 1, 1])
                    with col_title:
                        st.markdown("**Anti-Vibration Mount**")
                    with col_include:
                        e_avm = st.selectbox("", ["--", "Include", "Not Include"],
                                             index=safe_index(current.get("avm", "--"),
                                                              ["--", "Include", "Not Include"]),
                                             key=f"edit_avm_{idx_to_edit}_{i}",
                                             label_visibility="collapsed")
                    with col_source:
                        e_avm_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                    index=safe_index(current.get("avm_source", "--"),
                                                                     ["--", "HK", "DG"]),
                                                    key=f"edit_avm_source_{idx_to_edit}_{i}",
                                                    label_visibility="collapsed")

                    e_avm_model = st.text_input("Anti-Vibration Mount model(避震器型號)",
                                                value=current.get("avm_model", ""),
                                                key=f"edit_avm_model_{idx_to_edit}_{i}")

                    e_avm_qty = st.number_input("Qty", min_value=0, value=int(current.get("avm_qty", 0)),
                                                key=f"edit_avm_qty_{idx_to_edit}_{i}")

                st.markdown("---")

                # Container & Control & Circuit Breaker
                with st.expander("Container & Control & Circuit Breaker Group(貨櫃&控制器&斷路器)", expanded=False):
                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Container (貨櫃)**")
                    with col_source:
                        e_cont_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                     index=safe_index("--" if is_open_or_marine else current.get("cont_source", "--"), ["--", "HK", "DG"]),
                                                     key=f"edit_cont_source_{idx_to_edit}_{i}",
                                                     label_visibility="collapsed")

                    col_c1, col_c2, col_c3 = st.columns(3)
                    with col_c1:
                        e_cont_size = st.selectbox("Size(呎吋)", ["--", "20'ftHQ", "20'ftGP"],
                                                   index=safe_index("--" if is_open_or_marine else current.get("cont_size", "--"), ["--", "20'ftHQ", "20'ftGP"]),
                                                   key=f"edit_cont_size_{idx_to_edit}_{i}")
                    with col_c2:
                        e_cont_type = st.selectbox("Type(種類)", ["--", "FIEO", "Motorized"],
                                                   index=safe_index("--" if is_open_or_marine else current.get("cont_type", "--"), ["--", "FIEO", "Motorized"]),
                                                   key=f"edit_cont_type_{idx_to_edit}_{i}")
                    with col_c3:
                        e_cont_color = st.text_input("Color(顏色)", value=current.get("cont_color", ""), key=f"edit_cont_color_{idx_to_edit}_{i}")

                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        e_fork_slot = st.selectbox("是否帶叉槽位", ["--", "Yes", "No"],
                                                   index=safe_index("--" if is_open_or_marine else current.get("fork_slot", "--"), ["--", "Yes", "No"]),
                                                   key=f"edit_fork_slot_{idx_to_edit}_{i}")
                    with col_f2:
                        e_anti_noise = st.selectbox("Anti-Noise(78-80Dba @7M 75% loading)", ["--", "Yes", "No"],
                                                    index=safe_index("--" if is_open_or_marine else current.get("anti_noise", "--"), ["--", "Yes", "No"]),
                                                    key=f"edit_anti_noise_{idx_to_edit}_{i}")
                    col_i1, col_i2 = st.columns(2)
                    with col_i1:
                        e_internal_silencer = st.selectbox("Internal Silencer (內部消聲器)", ["--", "Include", "Not Include"],
                                                           index=safe_index("--" if is_open_or_marine else current.get("internal_silencer", "--"), ["--", "Include", "Not Include"]),
                                                           key=f"edit_internal_silencer_{idx_to_edit}_{i}")
                    with col_i2:
                        e_ss_locks = st.selectbox("304 Stainless Steel Door Locks & Hinges", ["--", "Include", "Not Include"],
                                                  index=safe_index("--" if is_open_or_marine else current.get("ss_locks", "--"), ["--", "Include", "Not Include"]),
                                                  key=f"edit_ss_locks_{idx_to_edit}_{i}")
                    e_emergency_stop = st.selectbox("Emergency Stop Button (緊急暫停)", ["--", "Include", "Not Include"],
                                                    index=safe_index("--" if is_open_or_marine else current.get("emergency_stop", "--"), ["--", "Include", "Not Include"]),
                                                    key=f"edit_emergency_stop_{idx_to_edit}_{i}")

                    st.markdown("---")

                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Panel (控制器)**")
                    with col_source:
                        e_panel_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                      index=safe_index(current.get("panel_source", "--"), ["--", "HK", "DG"]),
                                                      key=f"edit_panel_source_{idx_to_edit}_{i}",
                                                      label_visibility="collapsed")

                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        e_panel_model = st.text_input("Panel model", value=current.get("panel_model", ""), key=f"edit_panel_model_{idx_to_edit}_{i}")
                    with col_p2:
                        e_panel_sn = st.text_input("S/N", value=current.get("panel_sn", ""), key=f"edit_panel_sn_{idx_to_edit}_{i}")

                    col_title, col_include, col_source = st.columns([5, 1, 1])
                    with col_title:
                        st.markdown("**CO 探測器 (OLED)**")
                    with col_include:
                        e_co_detector = st.selectbox("", ["--", "Include", "Not Include"],
                                                     index=safe_index(current.get("co_detector", "--"), ["--", "Include", "Not Include"]),
                                                     key=f"edit_co_detector_{idx_to_edit}_{i}",
                                                     label_visibility="collapsed")
                    with col_source:
                        e_co_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                   index=safe_index(current.get("co_source", "--"), ["--", "HK", "DG"]),
                                                   key=f"edit_co_source_{idx_to_edit}_{i}",
                                                   label_visibility="collapsed")

                    st.markdown("---")

                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Circuit Breaker (斷路器)**")
                    with col_source:
                        e_breaker_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                        index=safe_index(current.get("breaker_source", "--"), ["--", "HK", "DG"]),
                                                        key=f"edit_breaker_source_{idx_to_edit}_{i}",
                                                        label_visibility="collapsed")

                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        e_breaker_type = st.selectbox("Breaker Type", ["--", "ACB", "MCCB"], index=safe_index(current.get("breaker_type", "--"), ["--", "ACB", "MCCB"]), key=f"edit_breaker_type_{idx_to_edit}_{i}")
                    with col_b2:
                        e_breaker_rating = st.text_input("Breaker Rating", value=current.get("breaker_rating", ""), key=f"edit_breaker_rating_{idx_to_edit}_{i}")
                    col_p3, col_p4 = st.columns(2)
                    with col_p3:
                        e_poles = st.selectbox("Poles", ["--", "3P", "4P"], index=safe_index(current.get("poles", "--"), ["--", "3P", "4P"]), key=f"edit_poles_{idx_to_edit}_{i}")
                    with col_p4:
                        e_spring_charging = st.selectbox("Spring Charging", ["--", "Motorized", "Single Usage"], index=safe_index(current.get("spring_charging", "--"), ["--", "Motorized", "Single Usage"]), key=f"edit_spring_charging_{idx_to_edit}_{i}")
                    e_control_voltage = st.text_input("Control Voltage", value=current.get("control_voltage", ""), key=f"edit_control_voltage_{idx_to_edit}_{i}")

                st.markdown("---")

                # Parts Group
                with st.expander("Parts (配件) Group", expanded=False):
                    part_key = f"parts_edit_{row_to_edit['Project_Name']}_{i}"
                    if part_key not in st.session_state:
                        old_parts = current.get("parts", [])
                        if not old_parts:
                            old_parts = [{"name": "", "source": "--"}]
                        st.session_state[part_key] = [p.copy() for p in old_parts]

                    parts_list = st.session_state[part_key]

                    for j in range(len(parts_list)):
                        col_name, col_source, col_delete = st.columns([4, 1, 1])
                        with col_name:
                            part_name = st.text_input(
                                f"配件名稱/描述 {j + 1}",
                                value=parts_list[j].get("name", ""),
                                key=f"dlg_part_name_{i}_{j}",
                                label_visibility="collapsed"
                            )
                        with col_source:
                            part_source = st.selectbox(
                                "貨源",
                                ["--", "HK", "DG"],
                                index=safe_index(parts_list[j].get("source", "--"), ["--", "HK", "DG"]),
                                key=f"dlg_part_source_{i}_{j}",
                                label_visibility="collapsed"
                            )
                        with col_delete:
                            if st.button("刪除", key=f"delete_dlg_part_{i}_{j}", type="secondary"):
                                parts_list.pop(j)
                                st.rerun()

                        parts_list[j] = {"name": part_name.strip(), "source": part_source if part_source != "--" else ""}

                    if st.button("+ 新增配件", key=f"add_dlg_part_{i}", type="secondary"):
                        parts_list.append({"name": "", "source": "--"})
                        st.rerun()

                st.markdown("---")

                # Remarks
                e_remarks = st.text_area("Remarks", value=current.get("remarks", ""), height=150, key=f"edit_remarks_{idx_to_edit}_{i}")

                spec_data = {
                    "prime": e_prime.strip(),
                    "standby": e_standby.strip(),
                    "voltage": "" if e_voltage == "--" else e_voltage,
                    "frequency": "" if e_frequency == "--" else e_frequency,
                    "rpm": e_rpm if e_rpm != "--" else "",
                    "genset_model": e_genset_model,
                    "genset_sn": e_genset_sn,
                    "engine_color": e_engine_color,
                    "engine_year": e_engine_year,
                    "engine_heater": e_engine_heater,
                    "engine_source": e_engine_source if e_engine_source != "--" else "",
                    "alt_model": e_alt_model,
                    "alt_sn": e_alt_sn,
                    "alt_color": e_alt_color,
                    "droop": e_droop if e_droop != "--" else "",
                    "pmg": e_pmg,
                    "alt_heater": e_alt_heater if e_alt_heater != "--" else "",
                    "alt_source": e_alt_source if e_alt_source != "--" else "",
                    "rad_model": e_rad_model,
                    "rad_sn": e_rad_sn,
                    "rad_temp": e_rad_temp,
                    "fan_size": e_fan_size,
                    "coolant_sensor": e_coolant_sensor if e_coolant_sensor != "--" else "",
                    "low_water": e_low_water if e_low_water != "--" else "",
                    "radiator_guard": e_radiator_guard if e_radiator_guard != "--" else "",
                    "fuel_cooler": e_fuel_cooler if e_fuel_cooler != "--" else "",
                    "rad_source": e_rad_source if e_rad_source != "--" else "",
                    "fuel_cooler_source": e_fuel_cooler_source if e_fuel_cooler_source != "--" else "",
                    "coolant_sensor_source": e_coolant_sensor_source if e_coolant_sensor_source != "--" else "",
                    "low_water_source": e_low_water_source if e_low_water_source != "--" else "",
                    "base_model": e_base_model,
                    "avm": e_avm if e_avm != "--" else "",
                    "avm_model": e_avm_model,
                    "avm_qty": str(e_avm_qty),
                    "base_source": e_base_source if e_base_source != "--" else "",
                    "avm_source": e_avm_source if e_avm_source != "--" else "",
                    "cont_size": e_cont_size if e_cont_size != "--" else "",
                    "cont_type": e_cont_type if e_cont_type != "--" else "",
                    "cont_color": e_cont_color,
                    "fork_slot": e_fork_slot if e_fork_slot != "--" else "",
                    "anti_noise": e_anti_noise if e_anti_noise != "--" else "",
                    "internal_silencer": e_internal_silencer if e_internal_silencer != "--" else "",
                    "ss_locks": e_ss_locks if e_ss_locks != "--" else "",
                    "emergency_stop": e_emergency_stop if e_emergency_stop != "--" else "",
                    "cont_source": e_cont_source if e_cont_source != "--" else "",
                    "panel_model": e_panel_model,
                    "panel_sn": e_panel_sn,
                    "co_detector": e_co_detector if e_co_detector != "--" else "",
                    "panel_source": e_panel_source if e_panel_source != "--" else "",
                    "co_source": e_co_source if e_co_source != "--" else "",
                    "breaker_type": e_breaker_type if e_breaker_type != "--" else "",
                    "breaker_rating": e_breaker_rating,
                    "poles": e_poles if e_poles != "--" else "",
                    "spring_charging": e_spring_charging if e_spring_charging != "--" else "",
                    "control_voltage": e_control_voltage,
                    "breaker_source": e_breaker_source if e_breaker_source != "--" else "",
                    "parts": [p for p in parts_list if p["name"].strip()],
                    "base_sn": e_base_sn,
                    "remarks": e_remarks.strip()
                }
                new_specs.append(spec_data)

        col_save, col_cancel = st.columns(2)
        with col_save:
            save_disabled = st.session_state.get("edit_saving", False)
            if st.button("Save & Close", type="primary", use_container_width=True, disabled=save_disabled):
                st.session_state.edit_saving = True
                st.rerun()

        with col_cancel:
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state["show_edit_spec_dialog"] = False
                st.session_state.dialog_active = None
                st.rerun()

        if st.session_state.get("edit_saving", False):
            fullscreen_loading("正在儲存規格至 Google Sheets，請稍候...☺️")

            first_spec = new_specs[0] if new_specs else {}
            new_visible = "\n".join([
                f"Genset model: {first_spec.get('genset_model', '—')} | S/N: {first_spec.get('genset_sn', '—')}",
                f"Alternator Model: {first_spec.get('alt_model', '—')} | S/N: {first_spec.get('alt_sn', '—')}",
                f"Panel model: {first_spec.get('panel_model', '—')} | S/N: {first_spec.get('panel_sn', '—')}",
                f"Breaker Type: {first_spec.get('breaker_type', '—')}"
            ])

            extra_json = json.dumps(new_specs, ensure_ascii=False)
            df.at[idx_to_edit, "Project_Spec"] = new_visible + "||EXTRA||" + extra_json

            save_projects()
            st.cache_data.clear()

            st.success("所有規格已成功更新！")
            st.session_state["show_edit_spec_dialog"] = False
            st.session_state.dialog_active = None
            st.session_state.edit_saving = False
            st.rerun()
    edit_spec_dialog()

# ==============================================
# Project Specification Dialog (新增用)
# ==============================================
if st.session_state.get("spec_dialog_open", False):
    if st.session_state.dialog_active != "new_spec":
        st.session_state.dialog_active = "new_spec"
        st.rerun()

    temp_project = st.session_state.temp_project
    qty = temp_project.get("Qty", 1)
    project_type = temp_project["Project_Type"]
    is_open_or_marine = project_type in ["Open Set", "Marine"]

    @st.dialog("Project Specification", width="large")
    def spec_dialog():
        st.markdown(f"**請填寫 {qty} 台機器的規格**")

        st.markdown(
            """
            <style>
            div[data-testid="column"] {
                display: flex !important;
                align-items: center !important;
            }
            div[data-testid="column"] div[data-testid="stTextInput"] > div > div,
            div[data-testid="column"] div[data-testid="stSelectbox"] > div > div {
                width: 100% !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        tabs = st.tabs([f"第 {i+1} 台" for i in range(qty)])

        specs = []
        if qty > 1:
            st.markdown("---")
            if st.button("📋 從第 1 台複製規格 → 所有其他台",
                         type="primary",
                         use_container_width=True,
                         help="點擊後會把目前第1台已填寫的規格，複製到第2台～最後一台"):

                source_i = 0

                static_fields = [
                    "prime", "standby", "voltage", "frequency", "rpm",
                    "genset_model", "engine_color", "engine_year", "engine_heater", "engine_source",
                    "alt_model", "alt_color", "droop", "pmg", "alt_heater", "alt_source",
                    "rad_model", "rad_temp", "fan_size", "rad_source", "radiator_guard",
                    "fuel_cooler", "fuel_cooler_source",
                    "coolant_sensor", "coolant_sensor_source",
                    "low_water", "low_water_source",
                    "base_model", "base_source",
                    "avm", "avm_model", "avm_qty", "avm_source",
                    "cont_size", "cont_type", "cont_color", "fork_slot", "anti_noise",
                    "internal_silencer", "ss_locks", "emergency_stop", "cont_source",
                    "panel_model", "co_detector", "panel_source", "co_source",
                    "breaker_type", "breaker_rating", "poles", "spring_charging", "control_voltage", "breaker_source",
                    "remarks"
                ]

                for field in static_fields:
                    src_key = f"dlg_{field}_{source_i}"
                    if src_key in st.session_state:
                        value = st.session_state[src_key]
                        for target_i in range(1, qty):
                            target_key = f"dlg_{field}_{target_i}"
                            st.session_state[target_key] = value

                src_parts_key = f"dlg_parts_{source_i}"
                if src_parts_key in st.session_state and st.session_state[src_parts_key]:
                    copied_parts = [p.copy() for p in st.session_state[src_parts_key]]
                    for target_i in range(1, qty):
                        st.session_state[f"dlg_parts_{target_i}"] = copied_parts

                st.success("已成功將第 1 台的規格複製到其他所有台！")
                st.rerun()

        for i in range(qty):
            with tabs[i]:
                st.markdown("### Prime & Standby Power")
                col1, col2 = st.columns(2)
                with col1:
                    s_prime = st.text_input("Prime (kW)", key=f"dlg_prime_{i}")
                    s_voltage = st.selectbox("Voltage(電壓)", ["--", "380", "400", "415", "440", "480","Muti-Voltage"], key=f"dlg_voltage_{i}")
                    s_frequency = st.selectbox("Frequency(頻率)", ["--", "50Hz", "60Hz","50Hz&60Hz"], key=f"dlg_frequency_{i}")
                with col2:
                    s_standby = st.text_input("Standby (kW)", key=f"dlg_standby_{i}")
                    s_rpm = st.selectbox("RPM(轉速)", ["--", "1500", "1800","1500&1800"], key=f"dlg_rpm_{i}")

                st.markdown("---")

                with st.expander("Engine & Alternator Group(發動機＆電球)", expanded=True):
                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Engine 發動機**")
                    with col_source:
                        s_engine_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_engine_source_{i}", label_visibility="collapsed")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        s_genset_model = st.text_input("Genset model(發動機型號)", key=f"dlg_genset_model_{i}")
                    with col2:
                        s_genset_sn = st.text_input("S/N", key=f"dlg_genset_sn_{i}")
                    with col3:
                        s_engine_color = st.text_input("Color(顏色)", key=f"dlg_engine_color_{i}")
                    with col4:
                        s_engine_year = st.text_input("Year(年份)", key=f"dlg_engine_year_{i}")
                    s_engine_heater = st.text_input("Engine Heater(發動機加熱器) kW", key=f"dlg_engine_heater_{i}")

                    st.markdown("---")

                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Alternator (電球)**")
                    with col_source:
                        s_alt_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_alt_source_{i}", label_visibility="collapsed")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        s_alt_model = st.text_input("Alternator Model(電球型號)", key=f"dlg_alt_model_{i}")
                    with col2:
                        s_alt_sn = st.text_input("S/N", key=f"dlg_alt_sn_{i}")
                    with col3:
                        s_alt_color = st.text_input("Color(顏色)", key=f"dlg_alt_color_{i}")
                    col_d1, col_d2, col_d3 = st.columns(3)
                    with col_d1:
                        s_droop = st.selectbox("DroopKit", ["--", "Include", "Not Include"], key=f"dlg_droop_{i}")
                    with col_d2:
                        s_pmg = st.text_input("PMG", key=f"dlg_pmg_{i}")
                    with col_d3:
                        s_alt_heater = st.selectbox("Alternator Heater (交流發電機加熱器)", ["--", "Include", "Not Include"], key=f"dlg_alt_heater_{i}")

                st.markdown("---")

                with st.expander("Radiator & Base Frame Group(水箱＆底架)", expanded=False):
                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Radiator (水箱)**")
                    with col_source:
                        s_rad_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_rad_source_{i}", label_visibility="collapsed")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        s_rad_model = st.text_input("Radiator model(水箱型號)", key=f"dlg_rad_model_{i}")
                    with col2:
                        s_rad_sn = st.text_input("S/N", key=f"dlg_rad_sn_{i}")
                    with col3:
                        s_rad_temp = st.text_input("Temperature(温度)", key=f"dlg_rad_temp_{i}")
                    s_fan_size = st.text_input("風扇呎吋", key=f"dlg_fan_size_{i}")

                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        s_radiator_guard = st.selectbox("Radiator Guard (水箱護罩)", ["--", "Include", "Not Include"], key=f"dlg_radiator_guard_{i}")

                    col_title, col_include, col_source = st.columns([5, 1, 1])
                    with col_title:
                        st.markdown("**Fuel Cooler (燃油冷卻器)**")
                    with col_include:
                        s_fuel_cooler = st.selectbox("", ["--", "Include", "Not Include"], key=f"dlg_fuel_cooler_{i}", label_visibility="collapsed")
                    with col_source:
                        s_fuel_cooler_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_fuel_cooler_source_{i}", label_visibility="collapsed")

                    col_title, col_include, col_source = st.columns([5, 1, 1])
                    with col_title:
                        st.markdown("**Coolant temperature sensor**")
                    with col_include:
                        s_coolant_sensor = st.selectbox("", ["--", "Include", "Not Include"], key=f"dlg_coolant_sensor_{i}", label_visibility="collapsed")
                    with col_source:
                        s_coolant_sensor_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_coolant_sensor_source_{i}", label_visibility="collapsed")

                    col_title, col_include, col_source = st.columns([5, 1, 1])
                    with col_title:
                        st.markdown("**Low water level float switch**")
                    with col_include:
                        s_low_water = st.selectbox("", ["--", "Include", "Not Include"], key=f"dlg_low_water_{i}", label_visibility="collapsed")
                    with col_source:
                        s_low_water_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_low_water_source_{i}", label_visibility="collapsed")

                    st.markdown("---")

                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Base Frame (底架)**")
                    with col_source:
                        s_base_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_base_source_{i}", label_visibility="collapsed")

                    col_model, col_sn = st.columns(2)
                    with col_model:
                        s_base_model = st.text_input("Base Frame model(底架型號)", key=f"dlg_base_model_{i}")
                    with col_sn:
                        s_base_sn = st.text_input("S/N", key=f"dlg_base_sn_{i}")

                    col_title, col_include, col_source = st.columns([5, 1, 1])
                    with col_title:
                        st.markdown("**Anti-Vibration Mount**")
                    with col_include:
                        s_avm = st.selectbox("", ["--", "Include", "Not Include"], key=f"dlg_avm_{i}", label_visibility="collapsed")
                    with col_source:
                        s_avm_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_avm_source_{i}", label_visibility="collapsed")
                    s_avm_model = st.text_input("Anti-Vibration Mount model(避震器型號)", key=f"dlg_avm_model_{i}")
                    s_avm_qty = st.number_input("Qty(數量)", min_value=0, value=0, key=f"dlg_avm_qty_{i}")

                st.markdown("---")

                with st.expander("Container & Control & Circuit Breaker Group(貨櫃&控制器&斷路器)", expanded=False):
                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Container (貨櫃)**")
                    with col_source:
                        s_cont_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_cont_source_{i}", label_visibility="collapsed")

                    col_c1, col_c2, col_c3 = st.columns(3)
                    with col_c1:
                        s_cont_size = st.selectbox("Size(呎吋)", ["--", "20'ftHQ", "20'ftGP"], index=0 if is_open_or_marine else 0, key=f"dlg_cont_size_{i}")
                    with col_c2:
                        s_cont_type = st.selectbox("Type(種類)", ["--", "FIEO", "Motorized"], index=0 if is_open_or_marine else 0, key=f"dlg_cont_type_{i}")
                    with col_c3:
                        s_cont_color = st.text_input("Color(顏色)", key=f"dlg_cont_color_{i}")

                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        s_fork_slot = st.selectbox("是否帶叉槽位", ["--", "Yes", "No"], index=0 if is_open_or_marine else 0, key=f"dlg_fork_slot_{i}")
                    with col_f2:
                        s_anti_noise = st.selectbox("Anti-Noise(78-80Dba @7M 75% loading)", ["--", "Yes", "No"], index=0 if is_open_or_marine else 0, key=f"dlg_anti_noise_{i}")
                    col_i1, col_i2 = st.columns(2)
                    with col_i1:
                        s_internal_silencer = st.selectbox("Internal Silencer (內部消聲器)", ["--", "Include", "Not Include"], index=0 if is_open_or_marine else 0, key=f"dlg_internal_silencer_{i}")
                    with col_i2:
                        s_ss_locks = st.selectbox("304 Stainless Steel Door Locks & Hinges", ["--", "Include", "Not Include"], index=0 if is_open_or_marine else 0, key=f"dlg_ss_locks_{i}")
                    s_emergency_stop = st.selectbox("Emergency Stop Button (緊急暫停)", ["--", "Include", "Not Include"], index=0 if is_open_or_marine else 0, key=f"dlg_emergency_stop_{i}")

                    st.markdown("---")

                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Panel (控制器)**")
                    with col_source:
                        s_panel_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_panel_source_{i}", label_visibility="collapsed")

                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        s_panel_model = st.text_input("Panel model(控制器型號)", key=f"dlg_panel_model_{i}")
                    with col_p2:
                        s_panel_sn = st.text_input("S/N", key=f"dlg_panel_sn_{i}")

                    col_title, col_include, col_source = st.columns([5, 1, 1])
                    with col_title:
                        st.markdown("**CO 探測器 (OLED)**")
                    with col_include:
                        s_co_detector = st.selectbox("", ["--", "Include", "Not Include"], key=f"dlg_co_detector_{i}", label_visibility="collapsed")
                    with col_source:
                        s_co_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_co_source_{i}", label_visibility="collapsed")

                    st.markdown("---")

                    col_title, col_source = st.columns([6, 1])
                    with col_title:
                        st.markdown("**Circuit Breaker (斷路器)**")
                    with col_source:
                        s_breaker_source = st.selectbox("貨源", ["--", "HK", "DG"], key=f"dlg_breaker_source_{i}", label_visibility="collapsed")

                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        s_breaker_type = st.selectbox("Breaker Type (斷路器種類)", ["--", "ACB", "MCCB"], key=f"dlg_breaker_type_{i}")
                    with col_b2:
                        s_breaker_rating = st.text_input("Breaker Rating (斷路器容量)", key=f"dlg_breaker_rating_{i}")
                    col_p3, col_p4 = st.columns(2)
                    with col_p3:
                        s_poles = st.selectbox("Poles(極數)", ["--", "3P", "4P"], key=f"dlg_poles_{i}")
                    with col_p4:
                        s_spring_charging = st.selectbox("Spring Charging(斷路器操作)", ["--", "Motorized", "Single Usage"], key=f"dlg_spring_charging_{i}")
                    s_control_voltage = st.text_input("Control Voltage(控制電壓)", key=f"dlg_control_voltage_{i}")

                st.markdown("---")

                with st.expander("Parts (配件) Group", expanded=False):
                    part_key = f"dlg_parts_{i}"
                    if part_key not in st.session_state:
                        st.session_state[part_key] = [{"name": "", "source": "--"}]

                    parts_list = st.session_state[part_key]

                    for j in range(len(parts_list)):
                        col_name, col_source, col_delete = st.columns([4, 1, 1])
                        with col_name:
                            part_name = st.text_input(f"配件名稱/描述 {j+1}", value=parts_list[j].get("name", ""), key=f"dlg_part_name_{i}_{j}", label_visibility="collapsed")
                        with col_source:
                            part_source = st.selectbox("貨源", ["--", "HK", "DG"],
                                                       index=safe_index(parts_list[j].get("source", "--"), ["--", "HK", "DG"]),
                                                       key=f"dlg_part_source_{i}_{j}",
                                                       label_visibility="collapsed")
                        with col_delete:
                            if st.button("刪除", key=f"delete_dlg_part_{i}_{j}", type="secondary"):
                                parts_list.pop(j)
                                st.rerun()

                        parts_list[j] = {"name": part_name.strip(), "source": part_source if part_source != "--" else ""}

                    if st.button("+ 新增配件", key=f"add_dlg_part_{i}", type="secondary"):
                        parts_list.append({"name": "", "source": "--"})
                        st.rerun()

                st.markdown("---")

                s_remarks = st.text_area("Remarks", height=150, key=f"dlg_remarks_{i}")

                spec_data = {
                    "prime": s_prime.strip(),
                    "standby": s_standby.strip(),
                    "voltage": "" if s_voltage == "--" else s_voltage,
                    "frequency": "" if s_frequency == "--" else s_frequency,
                    "rpm": "" if s_rpm == "--" else s_rpm,
                    "genset_model": s_genset_model,
                    "genset_sn": s_genset_sn,
                    "engine_color": s_engine_color,
                    "engine_year": s_engine_year,
                    "engine_heater": s_engine_heater,
                    "engine_source": s_engine_source if s_engine_source != "--" else "",
                    "alt_model": s_alt_model,
                    "alt_sn": s_alt_sn,
                    "alt_color": s_alt_color,
                    "droop": s_droop if s_droop != "--" else "",
                    "pmg": s_pmg,
                    "alt_heater": s_alt_heater if s_alt_heater != "--" else "",
                    "alt_source": s_alt_source if s_alt_source != "--" else "",
                    "rad_model": s_rad_model,
                    "rad_sn": s_rad_sn,
                    "rad_temp": s_rad_temp,
                    "fan_size": s_fan_size,
                    "coolant_sensor": s_coolant_sensor if s_coolant_sensor != "--" else "",
                    "low_water": s_low_water if s_low_water != "--" else "",
                    "radiator_guard": s_radiator_guard if s_radiator_guard != "--" else "",
                    "fuel_cooler": s_fuel_cooler if s_fuel_cooler != "--" else "",
                    "rad_source": s_rad_source if s_rad_source != "--" else "",
                    "fuel_cooler_source": s_fuel_cooler_source if s_fuel_cooler_source != "--" else "",
                    "coolant_sensor_source": s_coolant_sensor_source if s_coolant_sensor_source != "--" else "",
                    "low_water_source": s_low_water_source if s_low_water_source != "--" else "",
                    "base_model": s_base_model,
                    "base_sn": s_base_sn,
                    "base_source": s_base_source if s_base_source != "--" else "",
                    "avm": s_avm if s_avm != "--" else "",
                    "avm_qty": str(s_avm_qty),
                    "avm_source": s_avm_source if s_avm_source != "--" else "",
                    "cont_size": s_cont_size if s_cont_size != "--" else "",
                    "cont_type": s_cont_type if s_cont_type != "--" else "",
                    "cont_color": s_cont_color,
                    "fork_slot": s_fork_slot if s_fork_slot != "--" else "",
                    "anti_noise": s_anti_noise if s_anti_noise != "--" else "",
                    "internal_silencer": s_internal_silencer if s_internal_silencer != "--" else "",
                    "ss_locks": s_ss_locks if s_ss_locks != "--" else "",
                    "emergency_stop": s_emergency_stop if s_emergency_stop != "--" else "",
                    "cont_source": s_cont_source if s_cont_source != "--" else "",
                    "panel_model": s_panel_model,
                    "panel_sn": s_panel_sn,
                    "co_detector": s_co_detector if s_co_detector != "--" else "",
                    "panel_source": s_panel_source if s_panel_source != "--" else "",
                    "co_source": s_co_source if s_co_source != "--" else "",
                    "breaker_type": s_breaker_type if s_breaker_type != "--" else "",
                    "breaker_rating": s_breaker_rating,
                    "poles": s_poles if s_poles != "--" else "",
                    "spring_charging": s_spring_charging if s_spring_charging != "--" else "",
                    "control_voltage": s_control_voltage,
                    "breaker_source": s_breaker_source if s_breaker_source != "--" else "",
                    "remarks": s_remarks.strip(),
                    "parts": [p for p in parts_list if p["name"].strip()],
                    "avm_model": s_avm_model
                }
                specs.append(spec_data)

        col_save, col_cancel = st.columns(2)
        with col_save:
            save_disabled = st.session_state.get("new_spec_saving", False)
            if st.button("Save & Close", type="primary", use_container_width=True, disabled=save_disabled):
                st.session_state.new_spec_saving = True
                st.rerun()

        with col_cancel:
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state.spec_dialog_open = False
                st.session_state.dialog_active = None
                if "temp_project" in st.session_state:
                    del st.session_state.temp_project
                st.rerun()

        if st.session_state.get("new_spec_saving", False):
            fullscreen_loading("正在新增專案並儲存規格，請稍候...")

            first_spec = specs[0] if specs else {}
            visible_lines = [
                f"Genset model: {first_spec.get('genset_model', '—')} | S/N: {first_spec.get('genset_sn', '—')}",
                f"Alternator Model: {first_spec.get('alt_model', '—')} | S/N: {first_spec.get('alt_sn', '—')}",
                f"Panel model: {first_spec.get('panel_model', '—')} | S/N: {first_spec.get('panel_sn', '—')}",
                f"Breaker Type: {first_spec.get('breaker_type', '—')}"
            ]
            extra_json = json.dumps(specs, ensure_ascii=False)
            spec_text = "\n".join(visible_lines) + "||EXTRA||" + extra_json

            new_project = {
                **temp_project,
                "Project_Spec": spec_text,
            }

            global df
            df = pd.concat([df, pd.DataFrame([new_project])], ignore_index=True)

            save_projects()
            st.cache_data.clear()

            st.success(f"已成功新增專案（{qty} 台機器）！")
            if "temp_project" in st.session_state:
                del st.session_state.temp_project
            st.session_state.spec_dialog_open = False
            st.session_state.dialog_active = None
            st.session_state.new_spec_saving = False
            st.rerun()

    spec_dialog()

# ==============================================
# Edit Project Info Dialog
# ==============================================
if st.session_state.get("show_edit_info_dialog", False):
    if st.session_state.dialog_active != "edit_info":
        st.session_state.dialog_active = "edit_info"
        st.rerun()

    idx_to_edit = st.session_state["current_edit_idx"]
    row_to_edit = df.loc[idx_to_edit]

    @st.dialog("Edit Project Info", width="large")
    def edit_info_dialog():
        st.markdown(f"**Editing Basic Info for: {row_to_edit['Project_Name']}**")

        col1, col2 = st.columns(2)
        with col1:
            e_type = st.selectbox("Project Type*", ["Enclosure","Open Set","Scania","Marine","K50G3"],
                                  index=["Enclosure","Open Set","Scania","Marine","K50G3"].index(row_to_edit["Project_Type"]),
                                  key=f"edit_info_type_{idx_to_edit}")
            e_name = st.text_input("Project Name*", value=row_to_edit["Project_Name"], key=f"edit_info_name_{idx_to_edit}")
            e_year = st.selectbox("Year*", [2024,2025,2026], index=[2024,2025,2026].index(row_to_edit["Year"]), key=f"edit_info_year_{idx_to_edit}")
            e_qty = st.number_input("Qty", min_value=1, value=int(row_to_edit["Qty"]), key=f"edit_info_qty_{idx_to_edit}")
        with col2:
            e_customer = st.text_input("Customer", value=row_to_edit.get("Customer", ""), key=f"edit_info_customer_{idx_to_edit}")
            e_supervisor = st.text_input("Supervisor", value=row_to_edit.get("Supervisor", ""), key=f"edit_info_supervisor_{idx_to_edit}")
            e_leadtime = st.date_input("Lead Time*", value=row_to_edit["Lead_Time"], key=f"edit_info_leadtime_{idx_to_edit}")

        st.markdown("**Progress Dates**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            parts_val = None if pd.isna(row_to_edit.get("Parts_Arrival")) else row_to_edit["Parts_Arrival"]
            e_parts_arrival = st.date_input("Parts Arrival", value=parts_val, key=f"edit_info_parts_{idx_to_edit}")

            install_val = None if pd.isna(row_to_edit.get("Installation_Complete")) else row_to_edit["Installation_Complete"]
            e_install_complete = st.date_input("Installation Complete", value=install_val, key=f"edit_info_install_{idx_to_edit}")

            testing_val = None if pd.isna(row_to_edit.get("Testing_Complete")) else row_to_edit["Testing_Complete"]
            e_testing_complete = st.date_input("Testing Complete", value=testing_val, key=f"edit_info_testing_{idx_to_edit}")
        with col_d2:
            cleaning_val = None if pd.isna(row_to_edit.get("Cleaning_Complete")) else row_to_edit["Cleaning_Complete"]
            e_cleaning_complete = st.date_input("Cleaning Complete", value=cleaning_val, key=f"edit_info_cleaning_{idx_to_edit}")

            delivery_val = None if pd.isna(row_to_edit.get("Delivery_Complete")) else row_to_edit["Delivery_Complete"]
            e_delivery_complete = st.date_input("Delivery Complete", value=delivery_val, key=f"edit_info_delivery_{idx_to_edit}")

        e_reminder = st.text_input("Progress Reminder (顯示在進度條中間)", value=row_to_edit.get("Progress_Reminder", ""), key=f"edit_info_reminder_{idx_to_edit}")

        col_save, col_cancel = st.columns(2)
        with col_save:
            save_disabled = st.session_state.get("edit_info_saving", False)
            if st.button("Save & Close", type="primary", use_container_width=True, disabled=save_disabled):
                st.session_state.edit_info_saving = True
                st.rerun()

        with col_cancel:
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state["show_edit_info_dialog"] = False
                st.session_state.edit_info_active = False
                st.rerun()

        if st.session_state.get("edit_info_saving", False):
            fullscreen_loading("正在儲存基本資訊，請稍候...")

            if not e_name.strip():
                st.error("Project Name required!")
            elif e_name != row_to_edit["Project_Name"] and e_name in df["Project_Name"].values:
                st.error("Name exists!")
            else:
                df.at[idx_to_edit, "Project_Type"] = e_type
                df.at[idx_to_edit, "Project_Name"] = e_name
                df.at[idx_to_edit, "Year"] = int(e_year)
                df.at[idx_to_edit, "Lead_Time"] = e_leadtime
                df.at[idx_to_edit, "Customer"] = e_customer
                df.at[idx_to_edit, "Supervisor"] = e_supervisor
                df.at[idx_to_edit, "Qty"] = e_qty
                df.at[idx_to_edit, "Real_Count"] = e_qty
                df.at[idx_to_edit, "Progress_Reminder"] = e_reminder
                df.at[idx_to_edit, "Parts_Arrival"] = e_parts_arrival if e_parts_arrival else None
                df.at[idx_to_edit, "Installation_Complete"] = e_install_complete if e_install_complete else None
                df.at[idx_to_edit, "Testing_Complete"] = e_testing_complete if e_testing_complete else None
                df.at[idx_to_edit, "Cleaning_Complete"] = e_cleaning_complete if e_cleaning_complete else None
                df.at[idx_to_edit, "Delivery_Complete"] = e_delivery_complete if e_delivery_complete else None

                save_projects()
                st.cache_data.clear()

                st.success("基本資訊已成功更新！")
                st.session_state["show_edit_info_dialog"] = False
                st.session_state.edit_info_active = False
                st.session_state.edit_info_saving = False
                st.rerun()
    edit_info_dialog()

# ==============================================
# Sidebar & 主畫面（保持原樣）
# ==============================================
with st.sidebar:
    st.header("View Controls")
    if st.button("All Projects", use_container_width=True, type="primary", key="btn_all"):
        st.session_state.view_mode = "all"
        st.rerun()
    if st.button("Delay Projects", use_container_width=True, type="secondary", key="btn_delay"):
        st.session_state.view_mode = "delay"
        st.rerun()
    if st.button("📅Calendar", use_container_width=True, type="primary", key="btn_calendar"):
        st.session_state.view_mode = "calendar"
        st.rerun()

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

        default_type = st.session_state.get("last_filter_type", "All")
        default_year = st.session_state.get("last_filter_year", date.today().year)
        default_month = st.session_state.get("last_filter_month", "All")

        selected_type = st.selectbox(
            "Project Type",
            project_types,
            index=project_types.index(default_type),
            key="global_filter_type"
        )
        selected_year = st.selectbox(
            "Year",
            years,
            index=years.index(default_year),
            key="global_filter_year"
        )
        selected_month = st.selectbox(
            "Month",
            month_names,
            index=month_names.index(default_month),
            key="global_filter_month"
        )

        st.session_state.last_filter_type = selected_type
        st.session_state.last_filter_year = selected_year
        st.session_state.last_filter_month = selected_month
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
            new_year = st.selectbox("Year*", [2024,2025,2026], index=2, key="new_year")
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
                st.session_state.temp_project = {
                    "Project_Type": new_type,
                    "Project_Name": new_name,
                    "Year": int(new_year),
                    "Lead_Time": new_leadtime,
                    "Customer": new_customer or "",
                    "Supervisor": new_supervisor or "",
                    "Qty": new_qty,
                    "Real_Count": new_qty,
                    "Progress_Reminder": reminder or "",
                    "Parts_Arrival": d1 if d1 else None,
                    "Installation_Complete": d2 if d2 else None,
                    "Testing_Complete": d3 if d3 else None,
                    "Cleaning_Complete": d4 if d4 else None,
                    "Delivery_Complete": d5 if d5 else None
                }
                st.session_state.spec_dialog_open = True
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
    st.title("🗓️ 專案日曆視圖 - 拖曳或點擊即可修改進度日期")

    events = []

    for idx, proj in df.iterrows():
        project_name = proj["Project_Name"]

        if pd.notna(proj["Parts_Arrival"]):
            events.append({
                "id": f"parts_{idx}",
                "title": f"🟢 零件到貨: {project_name}",
                "start": proj["Parts_Arrival"].strftime("%Y-%m-%d"),
                "backgroundColor": "#a8e6cf",
                "borderColor": "#a8e6cf",
                "textColor": "black",
            })

        if pd.notna(proj["Installation_Complete"]):
            events.append({
                "id": f"install_{idx}",
                "title": f"🟡 安裝完成: {project_name}",
                "start": proj["Installation_Complete"].strftime("%Y-%m-%d"),
                "backgroundColor": "#ffd93d",
                "borderColor": "#ffd93d",
                "textColor": "black",
            })

        if pd.notna(proj["Testing_Complete"]):
            events.append({
                "id": f"testing_{idx}",
                "title": f"🟠 測試完成: {project_name}",
                "start": proj["Testing_Complete"].strftime("%Y-%m-%d"),
                "backgroundColor": "#ff9f89",
                "borderColor": "#ff9f89",
                "textColor": "black",
            })

        if pd.notna(proj["Cleaning_Complete"]):
            events.append({
                "id": f"cleaning_{idx}",
                "title": f"🟢 清潔完成: {project_name}",
                "start": proj["Cleaning_Complete"].strftime("%Y-%m-%d"),
                "backgroundColor": "#6bcf7f",
                "borderColor": "#6bcf7f",
                "textColor": "black",
            })

        if pd.notna(proj["Delivery_Complete"]):
            events.append({
                "id": f"delivery_{idx}",
                "title": f"🔴 交付完成: {project_name}",
                "start": proj["Delivery_Complete"].strftime("%Y-%m-%d"),
                "backgroundColor": "#ff6b6b",
                "borderColor": "#ff6b6b",
                "textColor": "white",
            })

    try:
        manpower_raw = conn.read(worksheet="supremacy_manpower", ttl=300)
        if not manpower_raw.empty:
            for _, rec in manpower_raw.iterrows():
                quote_num = rec.get("Quote_Number", "未知專案")
                staff = rec.get("Staff", "未知員工")
                start_date = rec.get("Start_Date", "")
                end_date = rec.get("End_Date", "")

                if start_date:
                    events.append({
                        "title": f"🧑‍🔧 派工開始: {staff} @ {quote_num}",
                        "start": start_date,
                        "backgroundColor": "#9d8aff",
                        "borderColor": "#9d8aff",
                        "textColor": "white",
                    })

                if end_date:
                    events.append({
                        "title": f"🧑‍🔧 派工結束: {staff} @ {quote_num}",
                        "start": end_date,
                        "backgroundColor": "#c0a0ff",
                        "borderColor": "#c0a0ff",
                        "textColor": "black",
                    })
    except Exception as e:
        pass

    calendar_options = {
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        },
        "height": "800px",
        "locale": "zh-hk",
        "editable": "true",
        "selectable": "true",
        "dayMaxEvents": "true",
    }

    state = calendar(events=events, options=calendar_options, key="stable_project_calendar")

    if state.get("eventDrop"):
        event = state["eventDrop"]["event"]
        event_id = event["id"]
        new_date = event["start"][:10]

        if "_" in event_id:
            field_key, idx_str = event_id.split("_", 1)
            idx = int(idx_str)
            field_map = {
                "parts": "Parts_Arrival",
                "install": "Installation_Complete",
                "testing": "Testing_Complete",
                "cleaning": "Cleaning_Complete",
                "delivery": "Delivery_Complete",
            }
            field = field_map.get(field_key)
            if field and idx in df.index:
                df.at[idx, field] = pd.to_datetime(new_date)
                save_projects()
                st.cache_data.clear()
                st.success(f"已拖曳更新「{df.at[idx, 'Project_Name']}」的 {field.replace('_', ' ')} 為 {new_date}")
                st.rerun()

    if state.get("eventClick"):
        event = state["eventClick"]["event"]
        event_id = event["id"]

        if "_" in event_id:
            field_key, idx_str = event_id.split("_", 1)
            idx = int(idx_str)
            field_map = {
                "parts": "零件到貨",
                "install": "安裝完成",
                "testing": "測試完成",
                "cleaning": "清潔完成",
                "delivery": "交付完成",
            }
            field_name = field_map.get(field_key)
            project_name = df.at[idx, "Project_Name"]

            st.subheader(f"修改專案進度：{project_name} - {field_name}")

            current_date = pd.to_datetime(event["start"][:10]).date()
            new_date = st.date_input("選擇新日期", value=current_date, key=f"edit_date_{event_id}")

            if st.button("確認更新", type="primary", key=f"save_date_{event_id}"):
                field_db_map = {
                    "parts": "Parts_Arrival",
                    "install": "Installation_Complete",
                    "testing": "Testing_Complete",
                    "cleaning": "Cleaning_Complete",
                    "delivery": "Delivery_Complete",
                }
                db_field = field_db_map.get(field_key)
                if db_field:
                    old_date = df.at[idx, db_field]
                    df.at[idx, db_field] = pd.to_datetime(new_date)
                    save_projects()
                    st.cache_data.clear()
                    st.success(
                        f"已更新「{project_name}」的 {field_name} 從 {old_date.date() if pd.notna(old_date) else '無'} → {new_date}")
                    st.rerun()

    st.caption("🗓️ 操作說明：拖曳事件直接調整日期 | 點擊事件修改日期 | 所有變更即時儲存到 Google Sheets")
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