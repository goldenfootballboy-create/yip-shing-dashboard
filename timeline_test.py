import streamlit as st
import pandas as pd
import os
import json
from datetime import date

# ==============================================
# 永久儲存
# ==============================================
PROJECTS_FILE = "projects_data.json"
CHECKLIST_FILE = "checklist_data.json"

if not os.path.exists(PROJECTS_FILE):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

if not os.path.exists(CHECKLIST_FILE):
    with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

def load_projects():
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    required = ["Project_Type","Project_Name","Year","Lead_Time","Customer","Supervisor",
                "Qty","Real_Count","Project_Spec","Description","Progress_Reminder",
                "Parts_Arrival","Installation_Complete","Testing_Complete","Cleaning_Complete","Delivery_Complete"]
    for c in required:
        if c not in df.columns: df[c] = ""
    date_cols = ["Lead_Time","Parts_Arrival","Installation_Complete","Testing_Complete","Cleaning_Complete","Delivery_Complete"]
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").fillna(2025).astype(int)
    if "Real_Count" not in df.columns:
        df["Real_Count"] = df.get("Qty", 1)
    return df

def save_projects(df):
    df2 = df.copy()
    date_cols = ["Lead_Time","Parts_Arrival","Installation_Complete","Testing_Complete","Cleaning_Complete","Delivery_Complete"]
    for c in date_cols:
        if c in df2.columns:
            df2[c] = df2[c].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) and hasattr(x, "strftime") else None)
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(df2.to_dict("records"), f, ensure_ascii=False, indent=2)

def load_checklist():
    with open(CHECKLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_checklist(data):
    with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

df = load_projects()
checklist_db = load_checklist()

# ==============================================
# 進度計算 + 顏色
# ==============================================
def calculate_progress(row):
    p = 0
    today = date.today()
    # 只有日期不為空且已過今天才計分
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
# 左側側邊欄：三大篩選 + 頁面切換 + New Project
# ==============================================
with st.sidebar:
    st.header("View Controls")

    # 頁面切換按鈕
    if st.button("All Projects", use_container_width=True, type="primary", key="btn_all"):
        st.session_state.view_mode = "all"
    if st.button("Delay Projects", use_container_width=True, type="secondary", key="btn_delay"):
        st.session_state.view_mode = "delay"

    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "all"

    st.markdown("---")

    # 三大篩選（只在 All Projects 時顯示）
    if st.session_state.view_mode == "all":
        st.markdown("### Filters")
        project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
        selected_type = st.selectbox("Project Type", project_types, index=0, key="filter_type")

        years = ["2024", "2025", "2026"]
        selected_year = st.selectbox("Year", years, index=1, key="filter_year")

        month_names = ["All", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        selected_month = st.selectbox("Month", month_names, index=0, key="filter_month")

        st.markdown("---")

    # New Project
    st.header("New Project")

    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_type = st.selectbox("Project Type*", ["Enclosure","Open Set","Scania","Marine","K50G3"], key="new_type")
            new_name = st.text_input("Project Name*", key="new_name")
            new_year = st.selectbox("Year*", [2024,2025,2026], index=1, key="new_year")
            new_qty  = st.number_input("Qty", min_value=1, value=1, key="new_qty")
        with c2:
            new_customer = st.text_input("Customer", key="new_customer")
            new_supervisor = st.text_input("Supervisor", key="new_supervisor")
            new_leadtime = st.date_input("Lead Time*", value=date.today(), key="new_leadtime")

        with st.expander("Project Specification & Progress Dates", expanded=False):
            st.markdown("**Specification**")
            s1 = st.text_input("Genset model", key="s1")
            s2 = st.text_input("Alternator Model", key="s2")
            s3 = st.text_input("Controller", key="s3")
            s4 = st.text_input("Circuit breaker Size", key="s4")
            s5 = st.text_input("Charger", key="s5")

            # Description 已移到 Specification
            desc = st.text_area("Description", height=100, key="desc")

            st.markdown("**Progress Dates**")
            d1 = st.date_input("Parts Arrival", value=None, key="d1")
            d2 = st.date_input("Installation Complete", value=None, key="d2")
            d3 = st.date_input("Testing Complete", value=None, key="d3")
            d4 = st.date_input("Cleaning Complete", value=None, key="d4")
            d5 = st.date_input("Delivery Complete", value=None, key="d5")

            reminder = st.text_input("Progress Reminder (顯示在進度條中間)", placeholder="例如：等緊報價 / 生產中 / 已發貨", key="reminder")

        if st.form_submit_button("Add", type="primary", use_container_width=True):
            if not new_name.strip():
                st.error("Project Name required!")
            elif new_name in df["Project_Name"].values:
                st.error("Name exists!")
            else:
                spec_lines = [
                    f"Genset model: {s1 or '—'}",
                    f"Alternator Model: {s2 or '—'}",
                    f"Controller: {s3 or '—'}",
                    f"Circuit breaker Size: {s4 or '—'}",
                    f"Charger: {s5 or '—'}"
                ]
                spec_text = "\n".join(spec_lines)

                new_project = {
                    "Project_Type": new_type, "Project_Name": new_name, "Year": int(new_year),
                    "Lead_Time": new_leadtime.strftime("%Y-%m-%d"), "Customer": new_customer or "",
                    "Supervisor": new_supervisor or "", "Qty": new_qty, "Real_Count": new_qty,
                    "Project_Spec": spec_text, "Description": desc or "",
                    "Progress_Reminder": reminder or "",
                    "Parts_Arrival": d1.strftime("%Y-%m-%d") if d1 else None,
                    "Installation_Complete": d2.strftime("%Y-%m-%d") if d2 else None,
                    "Testing_Complete": d3.strftime("%Y-%m-%d") if d3 else None,
                    "Cleaning_Complete": d4.strftime("%Y-%m-%d") if d4 else None,
                    "Delivery_Complete": d5.strftime("%Y-%m-%d") if d5 else None,
                }
                df = pd.concat([df, pd.DataFrame([new_project])], ignore_index=True)
                save_projects(df)
                st.success(f"Added: {new_name}")
                st.rerun()

# ==============================================
# 篩選邏輯 + 頁面切換
# ==============================================
today = date.today()
all_df = df.copy()

if st.session_state.view_mode == "delay":
    filtered_df = all_df[
        (all_df["Lead_Time"].dt.date < today) &
        (all_df.apply(calculate_progress, axis=1) < 100)
    ].copy()
    page_title = "Delay Projects"
else:
    filtered_df = all_df.copy()
    # 三大篩選
    if selected_type != "All":
        filtered_df = filtered_df[filtered_df["Project_Type"] == selected_type]
    filtered_df = filtered_df[filtered_df["Year"] == int(selected_year)]
    if selected_month != "All":
        month_map = {"Jan":1, "Feb":2, "Mar":3, "Apr":4, "May":5, "Jun":6,
                     "Jul":7, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dec":12}
        filtered_df = filtered_df[filtered_df["Lead_Time"].dt.month == month_map[selected_month]]
    page_title = "YIP SHING Project Dashboard"

# ==============================================
# 右上角 Counter + 進度卡片
# ==============================================
st.title(page_title)

# 右上角小方塊 Project Counter
if len(filtered_df) > 0:
    counter = filtered_df.groupby("Project_Type")["Qty"].sum().astype(int).sort_index()
    total_qty = int(filtered_df["Qty"].sum())
    st.markdown(f"""
    <div style="position:fixed; top:70px; right:20px; background:#1e3a8a; color:white; padding:12px 18px; 
                border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.3); z-index:1000; font-size:0.9rem; text-align:center;">
        <strong style="font-size:1.1rem;">Total: {total_qty}</strong><br>
        {"<br>".join([f"<strong>{k}:</strong> {v}" for k, v in counter.items()])}
    </div>
    """, unsafe_allow_html=True)

if len(filtered_df) == 0:
    if st.session_state.view_mode == "delay":
        st.success("No delay projects! All on time!")
    else:
        st.info("No projects match the selected filters.")
else:
    for idx, row in filtered_df.iterrows():
        pct = calculate_progress(row)
        color = get_color(pct)

        # 判斷 Checklist 狀態
        project_name = row["Project_Name"]
        current_check = checklist_db.get(project_name, {"purchase": [], "done_p": [], "drawing": [], "done_d": []})
        all_items = current_check["purchase"] + current_check["drawing"]
        done_items = set(current_check["done_p"]) | set(current_check["done_d"])
        real_items = [item for item in all_items if item and str(item).strip()]
        has_missing = any(str(item).strip() and str(item) not in done_items for item in real_items)
        all_done = len(real_items) > 0 and not has_missing
        is_empty = len(real_items) == 0

        # 狀態標籤
        status_tag = ""
        if is_empty:
            status_tag = '<span style="background:#888888; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:0.8rem; margin-left:10px;">Please add checklist</span>'
        elif all_done:
            status_tag = '<span style="background:#00aa00; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:0.8rem; margin-left:10px;">Check</span>'
        elif has_missing:
            status_tag = '<span style="background:#ff4444; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:0.8rem; margin-left:10px;">Missing Submission</span>'

        # Progress Reminder
        reminder_text = str(row.get("Progress_Reminder", "")).strip()
        if not reminder_text:
            reminder_text = "In Progress"
        reminder_display = f'<div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); font-weight:bold; font-size:1.1rem; color:white; text-shadow:1px 1px 3px black; pointer-events:none; z-index:10;">{reminder_text}</div>'

        # 進度卡片
        st.markdown(f"""
        <div style="background: linear-gradient(to right, {color} {pct}%, #f0f0f0 {pct}%); 
                    border-radius: 8px; padding: 10px 15px; margin: 6px 0; 
                    box-shadow: 0 2px 6px rgba(0,0,0,0.1); position: relative; overflow:hidden;">
            {reminder_display}
            <div style="display: flex; justify-content: space-between; align-items: center; position:relative; z-index:5;">
                <div style="font-weight: bold;">
                    {row['Project_Name']} • {row['Project_Type']}
                </div>
                <div>
                    {status_tag}
                    <span style="color:white; background:{color}; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:1rem; margin-left:10px;">
                        {pct}%
                    </span>
                </div>
            </div>
            <div style="font-size:0.85rem; color:#555; margin-top:6px; position:relative; z-index:5;">
                {row.get('Customer','—')} | {row.get('Supervisor','—')} | Qty:{row.get('Qty',0)} | 
                Lead Time: {fmt(row['Lead_Time'])}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 展開內容
        with st.expander(f"Details • {row['Project_Name']}", expanded=False):
            st.markdown(f"**Year:** {row['Year']} | **Lead Time:** {fmt(row['Lead_Time'])}")
            st.markdown(f"**Customer:** {row.get('Customer','—')} | **Supervisor:** {row.get('Supervisor','—')} | **Qty:** {row.get('Qty',0)}")

            if row.get("Project_Spec"):
                st.markdown("**Project Specification:**")
                for line in row["Project_Spec"].split("\n"):
                    if line.strip():
                        key, val = line.split(": ",1) if ": " in line else ("", line)
                        st.markdown(f"• **{key}:** {val}")

            # Description 已移到 Specification 區塊上方（在展開內容也顯示）
            if row.get("Description"):
                st.markdown(f"**Description:** {row['Description']}")

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
                    save_checklist(checklist_db)
                    st.success("Checklist 已儲存！")
                    st.rerun()

            # Edit
            if st.button("Edit", key=f"edit_{idx}", use_container_width=True):
                st.session_state[f"editing_{idx}"] = not st.session_state.get(f"editing_{idx}", False)

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

                    with st.expander("Project Specification & Progress Dates", expanded=True):
                        curr_spec = row.get("Project_Spec","")
                        lines = [line.split(": ",1)[1] if ": " in line else "" for line in curr_spec.split("\n")] if curr_spec else ["","","","",""]
                        e_s1 = st.text_input("Genset model", value=lines[0] if len(lines)>0 else "")
                        e_s2 = st.text_input("Alternator Model", value=lines[1] if len(lines)>1 else "")
                        e_s3 = st.text_input("Controller", value=lines[2] if len(lines)>2 else "")
                        e_s4 = st.text_input("Circuit breaker Size", value=lines[3] if len(lines)>3 else "")
                        e_s5 = st.text_input("Charger", value=lines[4] if len(lines)>4 else "")

                        # Description 移到 Specification 區塊
                        e_desc = st.text_area("Description", value=row.get("Description",""), height=100)

                        st.markdown("**Progress Dates**")
                        e_d1 = st.date_input("Parts Arrival", value=pd.to_datetime(row["Parts_Arrival"]).date() if pd.notna(row["Parts_Arrival"]) else None, key=f"d1e{idx}")
                        e_d2 = st.date_input("Installation Complete", value=pd.to_datetime(row["Installation_Complete"]).date() if pd.notna(row["Installation_Complete"]) else None, key=f"d2e{idx}")
                        e_d3 = st.date_input("Testing Complete", value=pd.to_datetime(row["Testing_Complete"]).date() if pd.notna(row["Testing_Complete"]) else None, key=f"d3e{idx}")
                        e_d4 = st.date_input("Cleaning Complete", value=pd.to_datetime(row["Cleaning_Complete"]).date() if pd.notna(row["Cleaning_Complete"]) else None, key=f"d4e{idx}")
                        e_d5 = st.date_input("Delivery Complete", value=pd.to_datetime(row["Delivery_Complete"]).date() if pd.notna(row["Delivery_Complete"]) else None, key=f"d5e{idx}")

                        e_reminder = st.text_input("Progress Reminder (顯示在進度條中間)", value=row.get("Progress_Reminder",""), placeholder="例如：等緊報價 / 生產中 / 已發貨")

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.form_submit_button("Save Changes", type="primary"):
                            if not e_name.strip():
                                st.error("Project Name required!")
                            else:
                                new_spec = "\n".join([
                                    f"Genset model: {e_s1 or '—'}",
                                    f"Alternator Model: {e_s2 or '—'}",
                                    f"Controller: {e_s3 or '—'}",
                                    f"Circuit breaker Size: {e_s4 or '—'}",
                                    f"Charger: {e_s5 or '—'}"
                                ])
                                df.at[idx, "Project_Type"] = e_type
                                df.at[idx, "Project_Name"] = e_name
                                df.at[idx, "Year"] = int(e_year)
                                df.at[idx, "Lead_Time"] = e_leadtime.strftime("%Y-%m-%d")
                                df.at[idx, "Customer"] = e_customer or ""
                                df.at[idx, "Supervisor"] = e_supervisor or ""
                                df.at[idx, "Qty"] = e_qty
                                df.at[idx, "Real_Count"] = e_qty
                                df.at[idx, "Project_Spec"] = new_spec
                                df.at[idx, "Description"] = e_desc or ""
                                df.at[idx, "Progress_Reminder"] = e_reminder or ""
                                df.at[idx, "Parts_Arrival"] = e_d1.strftime("%Y-%m-%d") if e_d1 else None
                                df.at[idx, "Installation_Complete"] = e_d2.strftime("%Y-%m-%d") if e_d2 else None
                                df.at[idx, "Testing_Complete"] = e_d3.strftime("%Y-%m-%d") if e_d3 else None
                                df.at[idx, "Cleaning_Complete"] = e_d4.strftime("%Y-%m-%d") if e_d4 else None
                                df.at[idx, "Delivery_Complete"] = e_d5.strftime("%Y-%m-%d") if e_d5 else None
                                save_projects(df)
                                del st.session_state[f"editing_{idx}"]
                                st.success("Updated!")
                                st.rerun()
                    with col_cancel:
                        if st.form_submit_button("Cancel"):
                            del st.session_state[f"editing_{idx}"]
                            st.rerun()

            # Delete + 確認視窗
            if st.button("Delete", key=f"del_{idx}", type="secondary", use_container_width=True):
                st.session_state[f"confirm_delete_{idx}"] = True

            if st.session_state.get(f"confirm_delete_{idx}", False):
                st.markdown("---")
                st.warning(f"確定要刪除專案 **{row['Project_Name']}** 嗎？")
                col_yes, col_no = st.columns(2)
                if col_yes.button("Yes, Delete", type="primary", key=f"yes_del_{idx}"):
                    df = df.drop(idx).reset_index(drop=True)
                    save_projects(df)
                    if project_name in checklist_db:
                        del checklist_db[project_name]
                        save_checklist(checklist_db)
                    del st.session_state[f"confirm_delete_{idx}"]
                    st.success("已刪除！")
                    st.rerun()
                if col_no.button("No, Cancel", key=f"no_del_{idx}"):
                    del st.session_state[f"confirm_delete_{idx}"]
                    st.rerun()

st.markdown("---")
st.caption("Progress only counts when date has passed today • All functions perfect • 永久儲存")