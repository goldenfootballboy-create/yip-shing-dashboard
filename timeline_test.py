import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

# -------------------------------------------------
# 1. 基本設定
# -------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

st.set_page_config(page_title="YIP SHING Project Status Dashboard", layout="wide", initial_sidebar_state="expanded")

# -------------------------------------------------
# 2. CSS
# -------------------------------------------------
st.markdown("""
<style>
    .main-header {font-size: 3rem; color: #1fb429; margin-bottom: 1rem; margin-top: -4rem; font-weight: bold; text-align: center;}
    .custom-progress {height: 20px; background-color: #e0e0e0; border-radius: 10px; overflow: hidden; width: 150px;}
    .custom-progress-fill {height: 100%; transition: width 0.3s ease; border-radius: 10px;}
    .reminder-section {background-color: #fff3cd; padding: 1rem; border: 1px solid #ffeeba; border-radius: 5px; color: #856404;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">YIP SHING Project Status Dashboard</div>', unsafe_allow_html=True)
st.markdown("---")

# -------------------------------------------------
# 3. 側邊欄
# -------------------------------------------------
st.sidebar.title("Dashboard Controls")
project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
selected_project_type = st.sidebar.selectbox("Select Project Type:", project_types, index=0)

years = ["2024", "2025", "2026"]
selected_year = st.sidebar.selectbox("Select Year:", years, index=years.index("2025"))

month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
selected_month = st.sidebar.selectbox("Lead Time:", month_options, index=0)

# -------------------------------------------------
# 4. 讀取 CSV
# -------------------------------------------------
def load_data():
    if not os.path.exists("projects.csv"):
        st.error("Cannot find `projects.csv`!")
        return None
    try:
        df = pd.read_csv("projects.csv", encoding='utf-8')
        required = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        if not all(col in df.columns for col in required):
            st.error(f"Missing columns: {', '.join([c for c in required if c not in df.columns])}")
            return None
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        date_cols = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

df = load_data()
if df is None:
    st.stop()

# -------------------------------------------------
# 5. 載入/儲存 Checklist 狀態（持久化）
# -------------------------------------------------
CHECKLIST_FILE = "checklist.json"

if os.path.exists(CHECKLIST_FILE):
    with open(CHECKLIST_FILE, "r", encoding="utf-8") as f:
        saved_checklist = json.load(f)
else:
    saved_checklist = {}

if 'checklist' not in st.session_state:
    st.session_state.checklist = saved_checklist

def save_checklist():
    with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.checklist, f, ensure_ascii=False, indent=2)

# -------------------------------------------------
# 6. 篩選 + Real_Count 統計
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

st.markdown(f"### Total: **{total_real_count}** | {'  '.join([f'{k}: {int(v)}' for k, v in project_counts.items()])}")

# -------------------------------------------------
# 7. 主畫面 + Checklist
# -------------------------------------------------
if total_real_count > 0:
    current_date = datetime.now()
    left_rows = filtered_df.to_dict('records')

    for i, row in enumerate(left_rows):
        col_left, col_right = st.columns([5, 5])

        with col_left:
            # 點擊展開的 Expander
            with st.expander(f"**{row['Project_Name']}** | {row.get('Brand', '')} | Qty: {row.get('Qty', '')}", expanded=False):
                st.write(f"**Description:** {row.get('Description', '')}")

                # 解析 Checklist
                order_items = [x.strip() for x in str(row.get('Need_Order', '')).split(',') if x.strip()]
                submit_items = [x.strip() for x in str(row.get('Need_Submit', '')).split(',') if x.strip()]  # ← 已改

                col_a, col_b = st.columns(2)

                with col_a:
                    st.subheader("需要訂購")
                    for item in order_items:
                        key = f"order_{row['Project_Name']}_{item}"
                        checked = st.checkbox(item, value=st.session_state.checklist.get(key, False), key=key)
                        st.session_state.checklist[key] = checked

                with col_b:
                    st.subheader("需要提交")  # ← 已改
                    for item in submit_items:
                        key = f"submit_{row['Project_Name']}_{item}"  # ← key 也改成 submit_
                        checked = st.checkbox(item, value=st.session_state.checklist.get(key, False), key=key)
                        st.session_state.checklist[key] = checked

                # 完成度
                total = len(order_items) + len(submit_items)
                completed = sum(st.session_state.checklist.get(k, False) for k in st.session_state.checklist
                                if k.startswith(f"order_{row['Project_Name']}") or k.startswith(f"submit_{row['Project_Name']}"))
                st.progress(completed / total if total else 0)
                st.write(f"**完成度：{completed}/{total}**")

                # 進度條（你原本的邏輯）
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

                color = '#0000ff' if progress == 100 else f'rgb(255, {int(255*(1-progress/100))}, 0)'
                st.markdown(f'<div class="custom-progress"><div class="custom-progress-fill" style="width:{progress}%;background:{color};"></div></div>', unsafe_allow_html=True)
                st.write(f"**{progress}%** - {['Not Start', 'Parts Arrived', 'Installation Completed', 'Testing Completed', 'Cleaning Completed', 'Completed'][progress//20]}")

    # 保存按鈕
    if st.button("保存所有 Checklist 狀態", use_container_width=True):
        save_checklist()
        st.success("所有打勾狀態已保存！")

else:
    st.info("No projects found.")

# -------------------------------------------------
# 8. Memo Pad & Footer
# -------------------------------------------------
st.markdown("---")
with st.expander("Memo Pad", expanded=True):
    # (你原本的 Memo Pad 程式碼，保持不變)
    pass

st.markdown("**YIP SHING Project Management System** | Real-time Status + Checklist")