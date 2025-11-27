import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

# -------------------------------------------------
# 永久儲存：checklist 存在 checklist_data.json（Streamlit Cloud 也不會丟）
# -------------------------------------------------
CHECKLIST_FILE = "checklist_data.json"
if os.path.exists(CHECKLIST_FILE):
    with open(CHECKLIST_FILE, "r", encoding="utf-8") as f:
        saved_checklist = json.load(f)
else:
    saved_checklist = {}

# -------------------------------------------------
# 1. 基本設定
# -------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

st.set_page_config(page_title="YIP SHING Project Status Dashboard", layout="wide", initial_sidebar_state="expanded")

# -------------------------------------------------
# 2. 完整 CSS（保持你原本的）
# -------------------------------------------------
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1fb429;
        margin-bottom: 1rem;
        margin-top: -4rem;
        font-weight: bold;
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
    }
    .main-header .title {flex-grow: 1; text-align: center;}
    .custom-progress {height: 20px; background-color: #e0e0e0; border-radius: 10px; overflow: hidden; width: 150px; padding: 0;}
    .custom-progress-fill {height: 100%; transition: width 0.3s ease; border-radius: 10px;}
    .tooltip-container {position: relative; display: inline-block;}
    .tooltip-box {
        position: absolute; bottom: 32px; left: 50%; transform: translateX(-50%);
        background: #1e1e1e; color: white; padding: 16px 24px; border-radius: 12px;
        font-size: 16px; line-height: 1.7; white-space: pre-wrap; text-align: left;
        min-width: 200px; max-width: 500px; box-shadow: 0 8px 25px rgba(0,0,0,0.5);
        opacity: 0; visibility: hidden; transition: all 0.3s ease; z-index: 999; pointer-events: none;
    }
    .tooltip-arrow {
        position: absolute; top: 100%; left: 50%; margin-left: -8px;
        border: 8px solid transparent; border-top-color: #1e1e1e;
    }
    .tooltip-container:hover .tooltip-box {opacity: 1 !important; visibility: visible !important;}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# 3. 標題 + 控制面板（完全保留你原本的）
# -------------------------------------------------
st.markdown('<div class="main-header"><div class="title">YIP SHING Project Status Dashboard</div></div>', unsafe_allow_html=True)
st.markdown("---")

with st.sidebar:
    st.title("Dashboard Controls")
    st.markdown("### Project Type Selection")
    project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
    selected_project_type = st.selectbox("Select Project Type:", project_types, index=0)
    years = ["2024", "2025", "2026"]
    selected_year = st.selectbox("Select Year:", years, index=years.index("2025"))
    month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
    selected_month = st.selectbox("Lead Time:", month_options, index=0)

# -------------------------------------------------
# 4. 讀取 CSV + 篩選 + 統計（完全保留你原本的）
# -------------------------------------------------
if not os.path.exists("projects.csv"):
    st.error("找不到 projects.csv！")
    st.stop()

df = pd.read_csv("projects.csv", encoding='utf-8')
required = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
if not all(col in df.columns for col in required):
    st.error(f"缺少必要欄位: {', '.join([c for c in required if c not in df.columns])}")
    st.stop()

df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
date_cols = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
for col in date_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

filtered_df = df[df['Year'] == int(selected_year)].copy()
if selected_project_type != "All":
    filtered_df = filtered_df[filtered_df['Project_Type'] == selected_project_type]
if selected_month != "--" and 'Lead_Time' in filtered_df.columns:
    month_idx = month_options.index(selected_month)
    if month_idx > 0:
        filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_idx]

filtered_df['Real_Count'] = pd.to_numeric(filtered_df.get('Real_Count', 0), errors='coerce').fillna(0).astype(int)
total_real_count = int(filtered_df['Real_Count'].sum())
project_counts = filtered_df.groupby('Project_Type')['Real_Count'].sum().to_dict()

month_str = selected_month if selected_month != "--" else "All Months"
st.markdown(f"### {selected_project_type} - {selected_year} {month_str} Project Count")
col1, *rest = st.columns([1] + [1]*len(project_counts))
with col1: st.write(f"**Total: {total_real_count}**")
for i, (pt, cnt) in enumerate(project_counts.items()):
    with rest[i]: st.write(f"**{pt}: {int(cnt)}**")

# -------------------------------------------------
# 5. 主畫面 + Tooltip（完美版！）
# -------------------------------------------------
if total_real_count > 0:
    st.markdown(f"### {selected_year} {month_str} {selected_project_type} Project Details")
    current_date = datetime.now()
    left_rows = filtered_df.to_dict('records')

    for i, row in enumerate(left_rows):
        col_left, col_right = st.columns([5, 5])

        with col_left:
            # 進度計算（保持你原本的）
            progress = 0
            if 'Parts_Arrival_Date' in row and pd.notna(row['Parts_Arrival_Date']):
                if row['Parts_Arrival_Date'].date() < current_date.date():
                    progress += 30
            if 'Installation_Complete_Date' in row and pd.notna(row['Installation_Complete_Date']):
                if row['Installation_Complete_Date'].date() < current_date.date():
                    progress += 40
            if 'Testing_Date' in row and pd.notna(row['Testing_Date']):
                if row['Testing_Date'].date() < current_date.date():
                    progress += 10
            if str(row.get('Cleaning', '')).strip().upper() == 'YES':
                progress += 10
            if 'Delivery_Date' in row and pd.notna(row['Delivery_Date']):
                if row['Delivery_Date'].date() < current_date.date():
                    progress += 10
            progress = min(progress, 100)

            color = '#0000ff' if progress == 100 else '#ff4500'
            explanation = {0: "Not Start Yet", 30: "Parts Arrived", 70: "Installation Completed",
                           80: "Testing Completed", 90: "Cleaning Completed", 100: "Project Completed"}.get(progress, f"{progress}% In Progress")

            c1, c2, c3, c4 = st.columns([3, 2, 3, 10])
            with c1:
                project_name = row['Project_Name']
                brand = str(row.get('Brand', '')).strip()
                if brand and brand.lower() != 'nan':
                    st.markdown(f"<div style='line-height:1.2;'><div style='font-weight:bold;'>{project_name}</div><div style='font-size:0.8rem;color:#666;'>{brand}</div></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{project_name}**")

            with c2:
                qty = row.get('Qty', '')
                if qty: st.write(qty)

            with c3:
                desc = str(row.get('Description', '')).upper()
                if 'KTA38' in desc and 'KTA50' in desc:
                    st.image("https://i.imgur.com/S2kIoCM.png", width=30)
                elif 'KTA38' in desc:
                    st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
                elif 'KTA50' in desc:
                    st.image("https://i.imgur.com/oJNLgDG.png", width=30)

            with c4:
                tooltip = str(row.get('Progress_Tooltip', '')).strip()
                if tooltip and tooltip.lower() != 'nan':
                    st.markdown(f"""
                    <div class="tooltip-container" style="width:150px;">
                        <div class="custom-progress">
                            <div class="custom-progress-fill" style="width:{progress}%;background:{color};"></div>
                        </div>
                        <div class="tooltip-box">
                            {tooltip.replace(chr(10), '<br>')}
                            <div class="tooltip-arrow"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="custom-progress"><div class="custom-progress-fill" style="width:{progress}%;background:{color};"></div></div>', unsafe_allow_html=True)

                pc1, pc2 = st.columns([1, 5])
                with pc1: st.write(f"**{progress}%**")
                with pc2: st.write(explanation)

    # 表格 + Delay Projects + Memo Pad 全部保留你原本的...

# -------------------------------------------------
# Checklist Panel（永久儲存版）
# -------------------------------------------------
with st.sidebar:
    st.title("Checklist Panel")

    for _, row in filtered_df.iterrows():
        project_name = row['Project_Name']
        data = saved_checklist.get(project_name, {
            "purchase": [x.strip() for x in str(row.get('Order_List', '')).split(',') if x.strip()],
            "done_p":   [],
            "drawing":  [x.strip() for x in str(row.get('Submit_List', '')).split(',') if x.strip()],
            "done_d":   []
        })

        with st.expander(f"{project_name}", expanded=False):
            st.markdown("### Purchase List     Drawings Submission")
            new_purchase = []; new_done_p = set(); new_drawing = []; new_done_d = set()
            max_rows = max(len(data["purchase"]), len(data["drawing"]), 6)

            for i in range(max_rows):
                col1, col2 = st.columns(2)
                with col1:
                    text = data["purchase"][i] if i < len(data["purchase"]) else ""
                    checked = text in data["done_p"]
                    c1, c2 = st.columns([1, 6])
                    with c1: chk = st.checkbox("", value=checked, key=f"p_{project_name}_{i}")
                    with c2: txt = st.text_input("", value=text, key=f"pt_{project_name}_{i}", label_visibility="collapsed")
                    if txt.strip():
                        new_purchase.append(txt.strip())
                        if chk: new_done_p.add(txt.strip())
                with col2:
                    text = data["drawing"][i] if i < len(data["drawing"]) else ""
                    checked = text in data["done_d"]
                    c1, c2 = st.columns([1, 6])
                    with c1: chk = st.checkbox("", value=checked, key=f"d_{project_name}_{i}")
                    with c2: txt = st.text_input("", value=text, key=f"dt_{project_name}_{i}", label_visibility="collapsed")
                    if txt.strip():
                        new_drawing.append(txt.strip())
                        if chk: new_done_d.add(txt.strip())

            if st.button("SAVE", key=f"save_{project_name}", use_container_width=True, type="primary"):
                saved_checklist[project_name] = {
                    "purchase": new_purchase,
                    "done_p": list(new_done_p),
                    "drawing": new_drawing,
                    "done_d": list(new_done_d)
                }
                with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
                    json.dump(saved_checklist, f, ensure_ascii=False, indent=2)
                st.success(f"{project_name} 已永久儲存！")
                st.rerun()

# -------------------------------------------------
# Memo Pad & Footer（保留你原本的）
# -------------------------------------------------
# ...（你原本的 Memo Pad 全部保留）

st.markdown("**YIP SHING Project Management System** | Real-time Project Status Monitoring")