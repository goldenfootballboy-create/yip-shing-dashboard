import streamlit as st
import pandas as pd
import os
from datetime import datetime

# === 動態設置工作目錄 ===
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# === 頁面配置 ===
st.set_page_config(
    page_title="YIP SHING Project Status Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === CSS 樣式優化 ===
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1fb429;
        margin-bottom: 1rem;
        margin-top: -4rem;
        font-weight: bold;
        text-align: center;
    }
    .project-name {
        font-weight: bold;
        padding-right: 0px;
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
        margin-top: 4px;
        font-weight: bold;
    }
    .progress-explanation {
        margin-left: 8px;
        font-size: 12px;
        color: #555;
        margin-top: 4px;
    }
    .kta38-icon {
        width: 30px;
        height: auto;
        margin: 0 3px;
        vertical-align: middle;
    }
    .milestone-table {
        font-size: 14px;
        width: 100%;
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
</style>
""", unsafe_allow_html=True)

# === 標題 ===
st.markdown('<div class="main-header">YIP SHING Project Status Dashboard</div>', unsafe_allow_html=True)
st.markdown("---")

# === 側邊欄 ===
st.sidebar.title("Dashboard Controls")
st.sidebar.markdown("### Project Type Selection")
project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
selected_project_type = st.sidebar.selectbox("Select Project Type:", project_types, index=0)

years = ["2024", "2025", "2026"]
selected_year = st.sidebar.selectbox("Select Year:", years, index=years.index("2025"))

month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
selected_month = st.sidebar.selectbox("Lead Time:", month_options, index=0)

# === 調試資訊：確認 CSV 狀態 ===
csv_file = "projects.csv"
st.sidebar.markdown("---")
if os.path.exists(csv_file):
    st.sidebar.success(f"CSV found: `{csv_file}`")
else:
    st.sidebar.error(f"CSV NOT found: `{csv_file}`")

# === 載入 CSV 數據（加強錯誤處理）===
def load_data():
    if not os.path.exists(csv_file):
        st.error(f"Cannot find `{csv_file}`! Please upload it to the same folder as this app.")
        st.info(f"Current directory: `{os.getcwd()}`")
        return None

    try:
        df = pd.read_csv(csv_file, encoding='utf-8', sep=',', dayfirst=True)
        required = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        missing = [col for col in required if col not in df.columns]
        if missing:
            st.error(f"Missing columns: {', '.join(missing)}")
            return None

        date_cols = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

        st.success(f"Loaded {len(df)} projects from `{csv_file}`")
        return df
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return None

df = load_data()

if df is None:
    st.stop()

# === 篩選數據 ===
filtered_df = df.copy()
if selected_project_type != "All":
    filtered_df = filtered_df[filtered_df['Project_Type'] == selected_project_type]

filtered_df = filtered_df[filtered_df['Year'] == int(selected_year)]

if selected_month != "--":
    month_idx = month_options.index(selected_month)
    if pd.notna(filtered_df['Lead_Time']).any():
        filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_idx]

# === 顯示項目計數 ===
total_projects = len(filtered_df)
project_counts = filtered_df['Project_Type'].value_counts().to_dict()

title = f"### {selected_project_type} - {selected_year}"
title += f" {selected_month}" if selected_month != "--" else " All Months"
title += " Project Count"
st.markdown(title)

cols = st.columns([1] + [1] * len(project_counts))
with cols[0]:
    st.write(f"**Total Projects: {total_projects}**")
for i, (ptype, count) in enumerate(project_counts.items()):
    with cols[i + 1]:
        st.write(f"**{ptype}: {count}**")

# === 顯示項目詳情 ===
if total_projects > 0:
    st.markdown(f"### {selected_year} {selected_month if selected_month != '--' else 'All Months'} {selected_project_type} Project Details")

    current_date = datetime.now().date()

    for _, row in filtered_df.iterrows():
        # 計算進度
        progress = 0
        parts_arrival_met = install_met = testing_met = cleaning_met = delivery_met = False

        if pd.notna(row.get('Parts_Arrival_Date')):
            try:
                if pd.to_datetime(row['Parts_Arrival_Date']).date() <= current_date:
                    progress += 30
                    parts_arrival_met = True
            except: pass
        if pd.notna(row.get('Installation_Complete_Date')):
            try:
                if pd.to_datetime(row['Installation_Complete_Date']).date() <= current_date:
                    progress += 40
                    install_met = True
            except: pass
        if pd.notna(row.get('Testing_Date')):
            try:
                if pd.to_datetime(row['Testing_Date']).date() <= current_date:
                    progress += 10
                    testing_met = True
            except: pass
        if row.get('Cleaning') == 'YES':
            progress += 10
            cleaning_met = True
        if pd.notna(row.get('Delivery_Date')):
            try:
                if pd.to_datetime(row['Delivery_Date']).date() <= current_date:
                    progress += 10
                    delivery_met = True
            except: pass
        if all([parts_arrival_met, install_met, testing_met, cleaning_met, delivery_met]):
            progress = 100
        progress = min(progress, 100)

        # 進度顏色
        if progress == 0:
            color = '#e0e0e0'
        elif progress < 30:
            r = int(224 + (255-224)*(progress/30))
            g = int(224 + (69-224)*(progress/30))
            b = int(224 + (0-224)*(progress/30))
            color = f'rgb({r},{g},{b})'
        elif progress < 70:
            r = 255
            g = int(69 + (255-69)*((progress-30)/40))
            b = 0
            color = f'rgb({r},{g},{b})'
        elif progress < 80:
            r = int(255 + (154-255)*((progress-70)/10))
            g = 255
            b = int(0 + (50-0)*((progress-70)/10))
            color = f'rgb({r},{g},{b})'
        elif progress < 90:
            r = int(154 + (0-154)*((progress-80)/10))
            g = int(205 + (255-205)*((progress-80)/10))
            b = int(50 + (0-50)*((progress-80)/10))
            color = f'rgb({r},{g},{b})'
        elif progress < 100:
            r = 0
            g = int(255 + (0-255)*((progress-90)/10))
            b = int(0 + (255-0)*((progress-90)/10))
            color = f'rgb({r},{g},{b})'
        else:
            color = '#0000ff'

        # 進度說明
        explanation = {
            0: "Not Start",
            30: "Parts Arrived",
            70: "Installation Completed",
            80: "Testing Completed",
            90: "Cleaning Completed",
            100: "Project Completed"
        }.get(progress, f"{progress}% Progress")

        # 圖片判斷
        desc = str(row.get('Description', '')).upper()
        has_kta38 = 'KTA38' in desc
        has_kta50 = 'KTA50' in desc

        # === 布局：Project Name + 圖片 + 進度條 + % + 說明 ===
        col1, col2, col3 = st.columns([2, 0.4, 5])
        with col1:
            st.write(row['Project_Name'])
        with col2:
            if has_kta38:
                st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
            elif has_kta50:
                st.image("https://i.imgur.com/3Cb2Nqj.png", width=30)
        with col3:
            # 進度條
            st.markdown(
                f'<div class="custom-progress"><div class="custom-progress-fill" style="width: {progress}%; background-color: {color};"></div></div>',
                unsafe_allow_html=True
            )
            # 百分比 + 說明（水平平排）
            pcol1, pcol2 = st.columns([1, 3])
            with pcol1:
                st.markdown(f"<div class='progress-text'>{progress}%</div>", unsafe_allow_html=True)
            with pcol2:
                st.markdown(f"<div class='progress-explanation'>{explanation}</div>", unsafe_allow_html=True)

    # === 顯示表格 ===
    display_cols = ['Project_Name', 'Description', 'Parts_Arrival_Date', 'Installation_Complete_Date',
                    'Testing_Date', 'Cleaning', 'Delivery_Date', 'Remarks']
    available_cols = [c for c in display_cols if c in filtered_df.columns]
    display_df = filtered_df[available_cols].copy()
    for col in available_cols[2:]:
        if pd.api.types.is_datetime64_any_dtype(display_df[col]):
            display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')
    st.markdown('<div class="milestone-table">', unsafe_allow_html=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.warning(f"No projects found for {selected_project_type} in {selected_year} {selected_month}.")

# === 提醒區 ===
if 'Delivery_Date' in df.columns and 'Lead_Time' in df.columns:
    reminder_df = df[(df['Delivery_Date'].isna()) | (df['Delivery_Date'] > df['Lead_Time'])][['Project_Name', 'Lead_Time', 'Delivery_Date', 'Remarks']]
    if not reminder_df.empty:
        st.markdown(f"""
        <div class="reminder-section">
            <h3>Reminder: Delivery Date Issues</h3>
            <p>The following projects have Delivery Date blank or later than Lead Time:</p>
            {reminder_df.to_html(index=False)}
        </div>
        """, unsafe_allow_html=True)

# === 頁腳 ===
st.markdown("---")
st.markdown("**YIP SHING Project Management System** | Real-time Project Status Monitoring")