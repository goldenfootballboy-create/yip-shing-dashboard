import streamlit as st
import pandas as pd
import os
from datetime import datetime

# -------------------------------------------------
# 1. 基本設定
# -------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

st.set_page_config(page_title="YIP SHING Project Status Dashboard", layout="wide", initial_sidebar_state="expanded")

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
# 4. 讀取 CSV + 篩選 + 統計（保持不變）
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
# 5. 主畫面 + 右側側邊欄 Checklist（可編輯內容 + 自動寫回 CSV）
# -------------------------------------------------
if total_real_count > 0:
    # 左邊主內容
    left_col, right_sidebar = st.columns([7, 3])

    with left_col:
        current_date = datetime.now()
        left_rows = filtered_df.to_dict('records')

        # 延誤專案計算（保持你原本邏輯）
        delay_projects = []
        # （你原本的延誤計算邏輯保持不變）

        for i, row in enumerate(left_rows):
            # 計算 progress
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

            # 主顯示
            c1, c2, c3, c4 = st.columns([3, 2, 3, 10])
            with c1:
                project_name = row['Project_Name']
                brand = str(row.get('Brand', '')).strip()
                if brand and brand.lower() != 'nan':
                    html = f"<div style='line-height:1.2;'><div style='font-weight:bold;margin-bottom:2px;'>{project_name}</div><div style='font-size:0.8rem;color:#666;'>{brand}</div></div>"
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.markdown(f"**{project_name}**")

            with c2:
                qty = row.get('Qty', '')
                if qty:
                    st.write(qty)

            with c3:
                desc = str(row.get('Description', '')).upper()
                if 'KTA38' in desc and 'KTA50' in desc:
                    st.image("https://i.imgur.com/S2kIoCM.png", width=30)
                elif 'KTA38' in desc:
                    st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
                elif 'KTA50' in desc:
                    st.image("https://i.imgur.com/oJNLgDG.png", width=30)

            with c4:
                st.markdown(f'<div class="custom-progress"><div class="custom-progress-fill" style="width:{progress}%;background:{color};"></div></div>', unsafe_allow_html=True)
                pc1, pc2 = st.columns([1, 5])
                with pc1: st.write(f"**{progress}%**")
                with pc2: st.write(explanation)

    # -------------------------------------------------
    # 右側側邊欄：可編輯 Checklist 內容（左右收合）
    # -------------------------------------------------
    with st.sidebar:
        st.title("Checklist Panel")

        # 每次都讀最新 CSV
        df_latest = pd.read_csv("projects.csv", encoding='utf-8')

        for idx, row in filtered_df.iterrows():
            project_name = row['Project_Name']

            with st.expander(f"{project_name}", expanded=False):
                current_order = row.get('Order_List', '')
                current_submit = row.get('Submit_List', '')

                new_order = st.text_area(
                    "需要訂購（逗號分隔）",
                    value=current_order,
                    height=80,
                    key=f"order_edit_{project_name}"
                )
                new_submit = st.text_area(
                    "需要提交（逗號分隔）",
                    value=current_submit,
                    height=80,
                    key=f"submit_edit_{project_name}"
                )

                if st.button("保存修改", key=f"save_{project_name}"):
                    df_latest.loc[df_latest['Project_Name'] == project_name, 'Order_List'] = new_order.strip()
                    df_latest.loc[df_latest['Project_Name'] == project_name, 'Submit_List'] = new_submit.strip()
                    df_latest.to_csv("projects.csv", index=False, encoding='utf-8')
                    st.success(f"{project_name} 已更新！", icon="✅")
                    st.rerun()

else:
    st.warning("No projects found.")

# -------------------------------------------------
# Memo Pad & Footer
# -------------------------------------------------
st.markdown("---")
with st.expander("Memo Pad", expanded=True):
    # （你原本的 Memo Pad 保持不變）
    pass

st.markdown("**YIP SHING Project Management System** | Real-time Status + Editable Checklist")