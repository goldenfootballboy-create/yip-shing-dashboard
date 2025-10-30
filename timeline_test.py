import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 動態設置工作目錄
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# 設置頁面配置
st.set_page_config(page_title="YIP SHING Project Status Dashboard", layout="wide", initial_sidebar_state="expanded")

# CSS
st.markdown("""
<style>
    .main-header {font-size: 3rem; color: #1fb429; margin: -4rem 0 1rem; font-weight: bold; text-align: center;}
    .custom-progress {height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; width: 150px;}
    .custom-progress-fill {height: 100%; transition: width 0.3s ease; border-radius: 10px;}
    .kta38-icon, .kta50-icon {width: 30px; height: auto; margin: 0 2px; vertical-align: middle;}
</style>
""", unsafe_allow_html=True)

# 標題
st.markdown('<div class="main-header">YIP SHING Project Status Dashboard</div>', unsafe_allow_html=True)
st.markdown("---")

# 側邊欄
st.sidebar.title("Dashboard Controls")
project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
selected_project_type = st.sidebar.selectbox("Project Type:", project_types)
selected_year = st.sidebar.selectbox("Year:", ["2024", "2025", "2026"], index=1)

# Load CSV（關鍵修正）
def load_data():
    csv_file = "projects.csv"
    if not os.path.exists(csv_file):
        st.error("CSV not found!")
        return None
    try:
        df = pd.read_csv(csv_file, encoding='utf-8', sep=',')
        # 關鍵：將 "None" 字串轉為 NaN
        df = df.replace(["None", "none", "NONE", ""], pd.NA)
        date_cols = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')  # 移除 dayfirst
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

df = load_data()
if df is None:
    st.stop()

# Filter
filtered_df = df[df['Year'] == int(selected_year)].copy()
if selected_project_type != "All":
    filtered_df = filtered_df[filtered_df['Project_Type'] == selected_project_type]

# Count
total = len(filtered_df)
counts = filtered_df['Project_Type'].value_counts().to_dict()
st.markdown(f"### {selected_project_type} - {selected_year} Project Count")
c1, c2, *rest = st.columns([1] + [1]*len(counts))
with c1: st.write(f"Total: {total}")
for i, (k, v) in enumerate(counts.items()):
    with rest[i]: st.write(f"{k}: {v}")

# Details
if total > 0:
    st.markdown(f"### {selected_year} Project Details")
    cols = ['Project_Name', 'Description', 'Parts_Arrival_Date', 'Installation_Complete_Date',
            'Testing_Date', 'Cleaning', 'Delivery_Date', 'Remarks']
    cols = [c for c in cols if c in filtered_df.columns]
    display_df = filtered_df[cols].copy()

    # Format dates
    for c in cols[2:]:
        if pd.api.types.is_datetime64_any_dtype(display_df[c]):
            display_df[c] = display_df[c].dt.strftime('%Y-%m-%d')

    now = datetime.now().date()

    for _, row in display_df.iterrows():
        progress = 0
        met = {}

        # Parts (30%)
        if pd.notna(row['Parts_Arrival_Date']):
            d = pd.to_datetime(row['Parts_Arrival_Date']).date()
            met['parts'] = d <= now
            if met['parts']: progress += 30

        # Installation (40%)
        if pd.notna(row['Installation_Complete_Date']):
            d = pd.to_datetime(row['Installation_Complete_Date']).date()
            met['install'] = d <= now
            if met['install']: progress += 40

        # Testing (10%)
        if pd.notna(row['Testing_Date']):
            d = pd.to_datetime(row['Testing_Date']).date()
            met['testing'] = d <= now
            if met['testing']: progress += 10

        # Cleaning (10%) - 加強判斷
        cleaning_str = str(row['Cleaning']).strip()
        met['cleaning'] = cleaning_str.upper() == 'YES' if cleaning_str else False
        if met['cleaning']: progress += 10

        # Delivery (10%)
        if pd.notna(row['Delivery_Date']):
            d = pd.to_datetime(row['Delivery_Date']).date()
            met['delivery'] = d <= now
            if met['delivery']: progress += 10

        # Force 100%
        if all(met.get(k, False) for k in ['parts', 'install', 'testing', 'cleaning', 'delivery']):
            progress = 100
        progress = min(progress, 100)

        # Color
        if progress == 0: color = '#e0e0e0'
        elif progress < 30: color = f'rgb({int(224+(255-224)*(progress/30))}, {int(224+(69-224)*(progress/30))}, {int(224+(0-224)*(progress/30))})'
        elif progress < 70: color = f'rgb(255, {int(69+(255-69)*((progress-30)/40))}, 0)'
        elif progress < 80: color = f'rgb({int(255+(154-255)*((progress-70)/10))}, 255, {int(0+(50-0)*((progress-70)/10))})'
        elif progress < 90: color = f'rgb({int(154+(0-154)*((progress-80)/10))}, {int(205+(255-205)*((progress-80)/10))}, {int(50+(0-50)*((progress-80)/10))})'
        elif progress < 100: color = f'rgb(0, {int(255+(0-255)*((progress-90)/10))}, {int(0+(255-0)*((progress-90)/10))})'
        else: color = '#0000ff'

        # Explanation
        exp_map = {0: "Not Start", 30: "Parts Arrived", 70: "Installation Completed",
                   80: "Testing Completed", 90: "Cleaning Completed", 100: "Project Completed"}
        explanation = exp_map.get(progress, f"{progress}% Progress")

        # Icon
        desc = str(row['Description']) if pd.notna(row['Description']) else ""
        kta38 = 'KTA38' in desc.upper()
        kta50 = 'KTA50' in desc.upper()

        # Layout
        c1, c2, c3 = st.columns([1, 0.2, 6])
        with c1: st.write(row['Project_Name'])
        with c2:
            if kta38: st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
            elif kta50: st.image("https://i.imgur.com/3Cb2Nqj.png", width=30)
        with c3:
            st.markdown(f'<div class="custom-progress"><div class="custom-progress-fill" style="width: {progress}%; background-color: {color};"></div></div>', unsafe_allow_html=True)
            cp, ce = st.columns([1, 20])
            with cp: st.write(f"{progress}%")
            with ce: st.write(explanation)

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.warning("No projects found.")

# Reminder
if 'Delivery_Date' in df.columns and 'Lead_Time' in df.columns:
    reminder = df[(df['Delivery_Date'].isna()) | (df['Delivery_Date'] > df['Lead_Time'])]
    if not reminder.empty:
        st.markdown(f"""
        <div style="background:#fff3cd; padding:1rem; border-radius:5px; border:1px solid #ffeeba;">
            <h3>Reminder: Delivery Date Issues</h3>
            <p>Delivery Date blank or later than Lead Time:</p>
            {reminder[['Project_Name', 'Lead_Time', 'Delivery_Date', 'Remarks']].to_html(index=False)}
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("**YIP SHING Project Management System** | Real-time Project Status Monitoring")