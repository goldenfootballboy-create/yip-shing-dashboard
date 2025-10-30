import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 動態設置工作目錄為腳本所在目錄
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# 設置頁面配置
st.set_page_config(
    page_title="YIP SHING Project Status Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 設置自定義 CSS 樣式
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
    .main-header .title {
        flex-grow: 1;
        text-align: center;
    }
    .project-type-selector {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1fb429;
    }
    .stButton > button {
        background-color: #1f77b4;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #155799;
    }
    .milestone-table {
        font-size: 14px;
        width: 100%;
    }
    .progress-container {
        margin: 10px 0;
        display: flex;
        width: 100%;
        align-items: center;
    }
    .project-name {
        font-weight: bold;
        padding-right: 0px;
        vertical-align: top;
        padding-top: 5px;
        word-wrap: break-word;
    }
    .custom-progress {
        height: 20px;
        background-color: #e0e0e0;
        border-radius: 10px;
        overflow: hidden;
        width: 150px;
        padding: 0;
    }
    .custom-progress-fill {
        height: 100%;
        transition: width 0.3s ease;
        border-radius: 10px;
    }
    .progress-text {
        margin-top: 5px;
        vertical-align: middle;
    }
    .progress-explanation {
        margin-left: 0px;
        vertical-align: middle;
        font-size: 12px;
        color: #333;
    }
    .kta38-icon, .kta50-icon {
        width: 30px;
        height: auto;
        margin: 0 2px;
        vertical-align: middle;
    }
    .reminder-section {
        background-color: #fff3cd;
        padding: 1rem;
        border: 1px solid #ffeeba;
        border-radius: 5px;
        color: #856404;
        max-height: 200px;
        overflow-y: auto;
    }
    .reminder-section table {
        width: 100%;
        border-collapse: collapse;
    }
    .reminder-section th, .reminder-section td {
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

# 標題
st.markdown('<div class="main-header"><div class="title">YIP SHING Project Status Dashboard</div></div>',
            unsafe_allow_html=True)
st.markdown("---")

# 側邊欄
st.sidebar.title("Dashboard Controls")
st.sidebar.markdown("### Project Type Selection")
project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
selected_project_type = st.sidebar.selectbox("Select Project Type:", project_types, index=0)

years = ["2024", "2025", "2026"]
selected_year = st.sidebar.selectbox("Select Year:", years, index=years.index("2025"))

# Load CSV data（移除 dayfirst=True）
def load_data():
    csv_file = "projects.csv"
    if not os.path.exists(csv_file):
        st.error(f"Cannot find {csv_file}! Ensure it's in: {script_dir}")
        return None

    try:
        df = pd.read_csv(csv_file, encoding='utf-8', sep=',')  # 移除 dayfirst
        required = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        if not all(col in df.columns for col in required):
            st.error(f"Missing columns: {set(required) - set(df.columns)}")
            return None

        date_cols = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')  # 移除 dayfirst
            else:
                st.warning(f"Missing column: {col}")
        return df
    except Exception as e:
        st.error(f"CSV Error: {e}")
        return None

df = load_data()
if df is None:
    st.stop()

# Month filter
month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
selected_month = st.sidebar.selectbox("Lead Time:", month_options, index=0)

# Filter data
if selected_project_type == "All":
    filtered_df = df[df['Year'] == int(selected_year)].copy()
else:
    filtered_df = df[(df['Project_Type'] == selected_project_type) & (df['Year'] == int(selected_year))].copy()

if selected_month != "--":
    month_idx = month_options.index(selected_month)
    filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_idx]

# Project count
total_projects = len(filtered_df)
project_counts = filtered_df['Project_Type'].value_counts().to_dict()

# Display count
title = f"### All - {selected_year} {selected_month} Project Count" if selected_project_type == "All" else f"### {selected_project_type} - {selected_year} {selected_month} Project Count"
st.markdown(title)

col1, col2, *other_cols = st.columns([1] + [1] * (len(project_counts) + 1))
with col1:
    st.write(f"Total Projects: {total_projects}")
for i, (pt, cnt) in enumerate(project_counts.items()):
    with other_cols[i]:
        st.write(f"{pt}: {cnt}")

# Project details
if total_projects > 0:
    title = f"### {selected_year} {selected_month} {selected_project_type} Project Details"
    st.markdown(title)

    display_cols = ['Project_Name', 'Description', 'Parts_Arrival_Date', 'Installation_Complete_Date',
                    'Testing_Date', 'Cleaning', 'Delivery_Date', 'Remarks']
    display_cols = [c for c in display_cols if c in filtered_df.columns]
    display_df = filtered_df[display_cols].copy()

    # Format dates
    for col in display_cols[2:]:
        if pd.api.types.is_datetime64_any_dtype(display_df[col]):
            display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')

    current_date = datetime.now().date()

    for _, row in display_df.iterrows():
        progress = 0

        # Parts Arrival (30%)
        parts_arrival_met = False
        if pd.notna(row['Parts_Arrival_Date']):
            try:
                parts_date = pd.to_datetime(row['Parts_Arrival_Date']).date()
                parts_arrival_met = parts_date <= current_date
                if parts_arrival_met:
                    progress += 30
            except:
                pass

        # Installation (40%)
        install_met = False
        if pd.notna(row['Installation_Complete_Date']):
            try:
                install_date = pd.to_datetime(row['Installation_Complete_Date']).date()
                install_met = install_date <= current_date
                if install_met:
                    progress += 40
            except:
                pass

        # Testing (10%)
        testing_met = False
        if pd.notna(row['Testing_Date']):
            try:
                testing_date = pd.to_datetime(row['Testing_Date']).date()
                testing_met = testing_date <= current_date
                if testing_met:
                    progress += 10
            except:
                pass

        # Cleaning (10%)
        cleaning_met = str(row['Cleaning']).strip().upper() == 'YES' if pd.notna(row['Cleaning']) else False
        if cleaning_met:
            progress += 10

        # Delivery (10%)
        delivery_met = False
        if pd.notna(row['Delivery_Date']):
            try:
                delivery_date = pd.to_datetime(row['Delivery_Date']).date()
                delivery_met = delivery_date <= current_date
                if delivery_met:
                    progress += 10
            except:
                pass

        # Force 100% if all met
        all_met = parts_arrival_met and install_met and testing_met and cleaning_met and delivery_met
        if all_met:
            progress = 100
        progress = min(progress, 100)

        # 動態計算進度條顏色（移到 progress 之後）
        if progress == 0:
            color = '#e0e0e0'
        elif progress < 30:
            r = int(224 + (255 - 224) * (progress / 30))
            g = int(224 + (69 - 224) * (progress / 30))
            b = int(224 + (0 - 224) * (progress / 30))
            color = f'rgb({r}, {g}, {b})'
        elif progress < 70:
            r = 255
            g = int(69 + (255 - 69) * ((progress - 30) / 40))
            b = 0
            color = f'rgb({r}, {g}, {b})'
        elif progress < 80:
            r = int(255 + (154 - 255) * ((progress - 70) / 10))
            g = 255
            b = int(0 + (50 - 0) * ((progress - 70) / 10))
            color = f'rgb({r}, {g}, {b})'
        elif progress < 90:
            r = int(154 + (0 - 154) * ((progress - 80) / 10))
            g = int(205 + (255 - 205) * ((progress - 80) / 10))
            b = int(50 + (0 - 50) * ((progress - 80) / 10))
            color = f'rgb({r}, {g}, {b})'
        elif progress < 100:
            r = 0
            g = int(255 + (0 - 255) * ((progress - 90) / 10))
            b = int(0 + (255 - 0) * ((progress - 90) / 10))
            color = f'rgb({r}, {g}, {b})'
        else:
            color = '#0000ff'

        # 設置說明
        if progress == 0:
            explanation = "Not Start"
        elif progress == 30:
            explanation = "Parts Arrived"
        elif progress == 70:
            explanation = "Installation Completed"
        elif progress == 80:
            explanation = "Testing Completed"
        elif progress == 90:
            explanation = "Cleaning Completed"
        elif progress == 100:
            explanation = "Project Completed"
        else:
            explanation = f"{progress}% Progress"

        # KTA38 / KTA50 icon
        desc = str(row['Description']) if pd.notna(row['Description']) else ""
        has_kta38 = 'KTA38' in desc.upper()
        has_kta50 = 'KTA50' in desc.upper()

        # Layout
        col1, col2, col3 = st.columns([1, 0.2, 6])
        with col1:
            st.write(row['Project_Name'])
        with col2:
            if has_kta38:
                st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
            elif has_kta50:
                st.image("https://i.imgur.com/3Cb2Nqj.png", width=30)
        with col3:
            st.markdown(
                f'<div class="custom-progress"><div class="custom-progress-fill" style="width: {progress}%; background-color: {color};"></div></div>',
                unsafe_allow_html=True
            )
            col_p, col_e = st.columns([1, 20])
            with col_p:
                st.write(f"{progress}%")
            with col_e:
                st.write(explanation)

    # Table
    st.markdown('<div class="milestone-table">', unsafe_allow_html=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.warning("No projects found.")

# Reminder
if 'Delivery_Date' in df.columns and 'Lead_Time' in df.columns:
    reminder_df = df[(df['Delivery_Date'].isna()) | (df['Delivery_Date'] > df['Lead_Time'])]
    reminder_df = reminder_df[['Project_Name', 'Lead_Time', 'Delivery_Date', 'Remarks']].dropna(how='all')
    if not reminder_df.empty:
        st.markdown(f"""
        <div class="reminder-section">
            <h3>Reminder: Delivery Date Issues</h3>
            <p>The following projects have Delivery Date either blank or later than Lead Time:</p>
            {reminder_df.to_html(index=False)}
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("**YIP SHING Project Management System** | Real-time Project Status Monitoring")