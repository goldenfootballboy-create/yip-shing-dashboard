import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

# -------------------------------------------------
# 1. 基本設定 + Checklist 持久化
# -------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

st.set_page_config(page_title="YIP SHING Project Status Dashboard", layout="wide", initial_sidebar_state="expanded")

# Checklist 狀態
CHECKLIST_FILE = "checklist.json"
if os.path.exists(CHECKLIST_FILE):
    with open(CHECKLIST_FILE, "r", encoding="utf-8") as f:
        st.session_state.checklist = json.load(f)
else:
    st.session_state.checklist = {}

def save_checklist():
    with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.checklist, f, ensure_ascii=False, indent=2)

# -------------------------------------------------
# 2. CSS
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
# 4. 讀取 CSV + 篩選 + 統計
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
# 5. 主畫面 + 右側側邊欄 Checklist（左右收合，像左邊一樣）
# -------------------------------------------------
if total_real_count > 0:
    # 左邊主內容
    main_container = st.container()
    with main_container:
        current_date = datetime.now()
        left_rows = filtered_df.to_dict('records')

        # 延誤專案計算（保持你原本邏輯）
        delay_projects = []
        # （你原本的延誤計算邏輯，省略）

        for i, row in enumerate(left_rows):
            # 你的左側專案顯示（完全不變）
            # ...（保持你原本的 c1 c2 c3 c4 顯示）...

    # -------------------------------------------------
    # 右側側邊欄 Checklist（左右收合）
    # -------------------------------------------------
    with st.sidebar("Checklist Panel", key="checklist_sidebar"):
        st.title("Checklist Panel")
        if st.button("保存所有狀態", use_container_width=True):
            save_checklist()
            st.success("已保存！")

        for row in filtered_df.itertuples():
            with st.expander(f"{row.Project_Name}", expanded=False):
                order_items = [x.strip() for x in str(row.get('Order_List', '')).split(',') if x.strip()]
                submit_items = [x.strip() for x in str(row.get('Submit_List', '')).split(',') if x.strip()]

                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("需要訂購")
                    for item in order_items:
                        key = f"order_{row.Project_Name}_{item}"
                        checked = st.checkbox(item, value=st.session_state.checklist.get(key, False), key=key)
                        st.session_state.checklist[key] = checked

                with col_b:
                    st.subheader("需要提交")
                    for item in submit_items:
                        key = f"submit_{row.Project_Name}_{item}"
                        checked = st.checkbox(item, value=st.session_state.checklist.get(key, False), key=key)
                        st.session_state.checklist[key] = checked

                total = len(order_items) + len(submit_items)
                completed = sum(st.session_state.checklist.get(k, False) for k in st.session_state.checklist if k.startswith(f"order_{row.Project_Name}_") or k.startswith(f"submit_{row.Project_Name}_"))
                st.progress(completed / total if total else 0)
                st.write(f"**完成度：{completed}/{total}**")

else:
    st.warning("No projects found.")

# -------------------------------------------------
# Memo Pad & Footer
# -------------------------------------------------
st.markdown("---")
with st.expander("Memo Pad", expanded=True):
    # （你原本的 Memo Pad）
    pass

st.markdown("**YIP SHING Project Management System** | Real-time Status + Checklist")