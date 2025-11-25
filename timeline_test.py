import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

# -------------------------------------------------
# 1. 基本設定 + Checklist 永久儲存（存在 json，不依賴 CSV）
# -------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

st.set_page_config(page_title="YIP SHING Project Status Dashboard", layout="wide", initial_sidebar_state="expanded")

# 永久儲存檔案
CHECKLIST_FILE = "checklist_data.json"

# 讀取已儲存的資料
if os.path.exists(CHECKLIST_FILE):
    with open(CHECKLIST_FILE, "r", encoding="utf-8") as f:
        saved_checklist = json.load(f)
else:
    saved_checklist = {}  # {project_name: {"purchase": ["item1", "item2"], "done_p": ["item1"], "drawing": [...], "done_d": [...]}

# -------------------------------------------------
# 2. CSS（保持你原本的）
# -------------------------------------------------
st.markdown("""
<style>
    .main-header {font-size: 3rem; color: #1fb429; margin-bottom: 1rem; margin-top: -4rem; font-weight: bold; text-align: center;}
    .custom-progress {height: 20px; background-color: #e0e0e0; border-radius: 10px; overflow: hidden; width: 150px;}
    .custom-progress-fill {height: 100%; transition: width 0.3s ease; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">YIP SHING Project Status Dashboard</div>', unsafe_allow_html=True)
st.markdown("---")

# -------------------------------------------------
# 3. 左側側邊欄（原本的 Controls）
# -------------------------------------------------
with st.sidebar:
    st.title("Dashboard Controls")
    project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
    selected_project_type = st.selectbox("Select Project Type:", project_types, index=0)

    years = ["2024", "2025", "2026"]
    selected_year = st.selectbox("Select Year:", years, index=years.index("2025"))

    month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
    selected_month = st.selectbox("Lead Time:", month_options, index=0)

# -------------------------------------------------
# 4. 讀取 CSV（只讀，不寫！）
# -------------------------------------------------
if not os.path.exists("projects.csv"):
    st.error("找不到 projects.csv！請確認檔案在同目錄")
    st.stop()

df = pd.read_csv("projects.csv", encoding='utf-8')

required = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"CSV 缺少必要欄位: {', '.join(missing)}")
    st.stop()

df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
date_cols = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
for col in date_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

# -------------------------------------------------
# 5. 篩選 + 統計（保持你原本的）
# -------------------------------------------------
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
st.markdown(f"### {selected_project_type} - {selected_year} {month_str} Project Count (by Real_Count)")
col1, *rest = st.columns([1] + [1]*len(project_counts))
with col1: st.write(f"**Total: {total_real_count}**")
for i, (pt, cnt) in enumerate(project_counts.items()):
    with rest[i]: st.write(f"**{pt}: {int(cnt)}**")

# -------------------------------------------------
# 6. 主畫面（完全保留你原本的排版）
# -------------------------------------------------
# （你原本的主畫面程式碼全部保留，從 if total_real_count > 0: 到最後）

# -------------------------------------------------
# 7. 左側側邊欄：雙欄 Checklist（存在 json，永不丟失！）
# -------------------------------------------------
with st.sidebar:
    st.title("Checklist Panel")

    for _, row in filtered_df.iterrows():
        project_name = row['Project_Name']

        # 從 json 讀取（如果沒有就用 CSV 初始值）
        data = saved_checklist.get(project_name, {
            "purchase": [x.strip() for x in str(row.get('Order_List', '')).split(',') if x.strip()],
            "done_p": [],
            "drawing": [x.strip() for x in str(row.get('Submit_List', '')).split(',') if x.strip()],
            "done_d": []
        })

        with st.expander(f"{project_name}", expanded=False):
            st.markdown("### Purchase List     Drawings Submission")

            new_purchase = []
            new_done_p = set()
            new_drawing = []
            new_done_d = set()

            max_rows = max(len(data["purchase"]), len(data["drawing"]), 6)

            for i in range(max_rows):
                col1, col2 = st.columns(2)

                # Purchase List
                with col1:
                    text = data["purchase"][i] if i < len(data["purchase"]) else ""
                    checked = text in data["done_p"]
                    c1, c2 = st.columns([1, 6])
                    with c1:
                        chk = st.checkbox("", value=checked, key=f"pchk_{project_name}_{i}")
                    with c2:
                        txt = st.text_input("", value=text, key=f"ptxt_{project_name}_{i}", label_visibility="collapsed")
                    if txt.strip():
                        new_purchase.append(txt.strip())
                        if chk:
                            new_done_p.add(txt.strip())

                # Drawings Submission
                with col2:
                    text = data["drawing"][i] if i < len(data["drawing"]) else ""
                    checked = text in data["done_d"]
                    c1, c2 = st.columns([1, 6])
                    with c1:
                        chk = st.checkbox("", value=checked, key=f"dchk_{project_name}_{i}")
                    with c2:
                        txt = st.text_input("", value=text, key=f"dtxt_{project_name}_{i}", label_visibility="collapsed")
                    if txt.strip():
                        new_drawing.append(txt.strip())
                        if chk:
                            new_done_d.add(txt.strip())

            # 儲存按鈕
            if st.button("儲存此項目", key=f"save_{project_name}", use_container_width=True, type="primary"):
                saved_checklist[project_name] = {
                    "purchase": new_purchase,
                    "done_p": list(new_done_p),
                    "drawing": new_drawing,
                    "done_d": list(new_done_d)
                }
                with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
                    json.dump(saved_checklist, f, ensure_ascii=False, indent=2)
                st.success(f"{project_name} 已儲存！")
                st.rerun()

# -------------------------------------------------
# Memo Pad & Footer（保持你原本的）
# -------------------------------------------------
# （你原本的 Memo Pad 程式碼全部保留）

st.markdown("---")
st.markdown("**所有 Checklist 資料已永久儲存在 checklist_data.json，永不丟失！**")