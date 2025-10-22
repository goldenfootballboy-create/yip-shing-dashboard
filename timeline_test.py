import streamlit as st
import pandas as pd
import os
from datetime import datetime
import streamlit.components.v1 as components
import math


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
        margin-bottom: 1rem; /* 減少下方的留白 */
        margin-top: -4rem; /* 向上移動標題 */
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
        align-items: center;
        justify-content: space-between;
        width: 100%;
        max-width: 600px;
    }
    .project-name {
        font-weight: bold;
        margin-right: 30px;
        flex-shrink: 0;
    }
    .progress-wrapper {
        flex-grow: 1;
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

# 標題（標題居中）
st.markdown('<div class="main-header"><div class="title">YIP SHING Project Status Dashboard</div></div>',
            unsafe_allow_html=True)

st.markdown("---")

# 側邊欄設置
st.sidebar.title("📊 Dashboard Controls")
st.sidebar.markdown("### Project Type Selection")
project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
selected_project_type = st.sidebar.selectbox(
    "Select Project Type:",
    project_types,
    index=0,
    help="Select the project type status to view"
)

# Year selection
years = ["2024", "2025", "2026"]
selected_year = st.sidebar.selectbox(
    "Select Year:",
    years,
    index=years.index("2025"),  # Default to current year 2025
    help="Select the year to view"
)

# Load CSV data
def load_data():
    """Load data from CSV file"""
    csv_file = "projects.csv"
    if not os.path.exists(csv_file):
        st.error(f"Cannot find {csv_file}! Ensure the file is located in: {script_dir}")
        st.info(f"Current working directory: {os.getcwd()}")
        st.info(
            "Suggestions: 1. Verify projects.csv exists in the same directory as app.py. 2. Check filename (including case and extension). 3. Ensure the file has read permissions.")
        return None

    try:
        # 嘗試使用 UTF-8 讀取，並支援日/月/年格式
        data_df = pd.read_csv(csv_file, encoding='utf-8', sep=',', dayfirst=True)
        required_columns = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        missing_columns = [col for col in required_columns if col not in data_df.columns]
        if missing_columns:
            st.error(f"CSV file is missing the following required columns: {', '.join(missing_columns)}")
            st.info("Ensure the CSV file contains: Project_Type, Project_Name, Year, Lead_Time")
            return None

        date_columns = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
        for col in date_columns:
            if col in data_df.columns:
                data_df[col] = pd.to_datetime(data_df[col], errors='coerce', dayfirst=True)
                if data_df[col].isna().all():
                    st.warning(f"Column {col} contains no valid dates and may be ignored.")
            else:
                st.warning(f"Column {col} is missing in the CSV file.")
        return data_df
    except UnicodeDecodeError:
        st.error("Failed to read CSV file with UTF-8 encoding. Ensure the file uses UTF-8 encoding.")
        st.info("Suggestion: Save the file as 'CSV UTF-8' in Excel or use a text editor to ensure UTF-8 encoding.")
        return None
    except pd.errors.ParserError:
        st.error("CSV file format error, possibly due to incorrect delimiter (should be comma). Check the file content.")
        st.info("Suggestion: Verify the CSV uses comma separation or try a different delimiter (e.g., semicolon).")
        return None

# Load data
df = load_data()

# 檢查 df 是否為 None，並顯示錯誤訊息
if df is None:
    st.error("Failed to load data. Please check the console or previous messages for details.")
else:
    # Define fixed month options for Lead Time (中文月份)
    month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
    selected_month = st.sidebar.selectbox(
        "Lead Time:",
        month_options,
        index=0,
        help="Select the lead time to view or '--' for all lead times"
    )

    # Filter by selected project type and year/month based on Lead_Time
    if selected_project_type == "All":
        if 'Year' in df.columns and 'Lead_Time' in df.columns:
            filtered_df = df[df['Year'] == int(selected_year)].copy()
            if selected_month != "--":
                # 從 Lead_Time 提取月份並與 selected_month 匹配
                if pd.api.types.is_datetime64_any_dtype(filtered_df['Lead_Time']):
                    month_index = month_options.index(selected_month)  # 獲取 selected_month 的索引（0-12）
                    if month_index == 0:  # "--" 不篩選
                        filtered_df = filtered_df
                    else:
                        filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_index]  # 直接比較月份
                else:
                    st.warning("Lead_Time column is not in datetime format. Skipping month filter.")
        else:
            st.error("Columns 'Year' or 'Lead_Time' not found in the data. Please check your CSV file.")
            filtered_df = pd.DataFrame()
    else:
        filtered_df = df[df['Project_Type'] == selected_project_type].copy()
        if 'Year' in df.columns and 'Lead_Time' in df.columns:
            filtered_df = filtered_df[filtered_df['Year'] == int(selected_year)].copy()
            if selected_month != "--":
                if pd.api.types.is_datetime64_any_dtype(filtered_df['Lead_Time']):
                    month_index = month_options.index(selected_month)  # 獲取 selected_month 的索引（0-12）
                    if month_index == 0:  # "--" 不篩選
                        filtered_df = filtered_df
                    else:
                        filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_index]  # 直接比較月份
                else:
                    st.warning("Lead_Time column is not in datetime format. Skipping month filter.")
        else:
            st.error("Columns 'Year' or 'Lead_Time' not found in the data. Please check your CSV file.")
            filtered_df = pd.DataFrame()

    # Calculate project counts by Project_Type
    total_projects = len(filtered_df)
    project_counts = filtered_df['Project_Type'].value_counts().to_dict()

    # Display project count
    if selected_project_type == "All":
        if selected_month == "--":
            st.markdown(f"### All - {selected_year} All Months Project Count")
        else:
            st.markdown(f"### All - {selected_year} {selected_month} Project Count")
    else:
        if selected_month == "--":
            st.markdown(f"### {selected_project_type} - {selected_year} All Months Project Count")
        else:
            st.markdown(f"### {selected_project_type} - {selected_year} {selected_month} Project Count")

    # Use columns for horizontal layout
    col1, col2, *other_cols = st.columns([1] + [1] * (len(project_counts) + 1))
    with col1:
        st.write(f"Total Projects: {total_projects}")
    index = 0
    for project_type, count in project_counts.items():
        with other_cols[index]:
            st.write(f"{project_type}: {count}")
        index += 1

    # Display projects and milestones with progress bar
    if total_projects > 0:
        if selected_project_type == "All":
            if selected_month == "--":
                st.markdown(f"### {selected_year} All Months {selected_project_type} Project Details")
            else:
                st.markdown(f"### {selected_year} {selected_month} {selected_project_type} Project Details")
        else:
            if selected_month == "--":
                st.markdown(f"### {selected_year} All Months {selected_project_type} Project Details")
            else:
                st.markdown(f"### {selected_year} {selected_month} {selected_project_type} Project Details")
        milestone_columns = [
            'Project_Name', 'Description', 'Parts_Arrival_Date', 'Installation_Complete_Date',
            'Testing_Date', 'Cleaning', 'Delivery_Date', 'Remarks'
        ]
        available_columns = [col for col in milestone_columns if col in filtered_df.columns]
        if not any(col in filtered_df.columns for col in milestone_columns[1:]):
            st.warning("No date-related, Description, or Remarks columns found in the data.")
        display_df = filtered_df[available_columns].copy()

        # Format date columns
        for col in available_columns[1:]:  # Skip Project_Name
            if pd.api.types.is_datetime64_any_dtype(display_df[col]):
                display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')

        # Calculate progress for each project
        current_date = datetime.now() # Current date
        for index, row in display_df.iterrows():
            progress = 0
            parts_arrival_met = pd.notna(row['Parts_Arrival_Date']) and pd.to_datetime(row['Parts_Arrival_Date']).date() <= current_date.date()
            install_met = pd.notna(row['Installation_Complete_Date']) and pd.to_datetime(row['Installation_Complete_Date']).date() <= current_date.date()
            testing_met = pd.notna(row['Testing_Date']) and pd.to_datetime(row['Testing_Date']).date() <= current_date.date()
            delivery_met = pd.notna(row['Delivery_Date']) and pd.to_datetime(row['Delivery_Date']).date() <= current_date.date()
            cleaning_met = row['Cleaning'] == 'YES'

            if parts_arrival_met:
                progress += 30
            if install_met:
                progress += 40
            if testing_met:
                progress += 10
            if cleaning_met:
                progress += 10
            if delivery_met:
                progress += 10
            progress = min(progress, 100)  # Cap at 100%

            # Use columns to align project name and progress bar
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(row['Project_Name'])
            with col2:
                st.progress(progress / 100, text=f"{progress}%")

        # Display table with styling
        st.markdown('<div class="milestone-table">', unsafe_allow_html=True)
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning(f"No {selected_project_type} projects found in {selected_year} {selected_month}.")

    # Reminder section for Delivery_Date issues (across all data, not filtered by year/month)
    if 'Delivery_Date' in df.columns and 'Lead_Time' in df.columns:
        reminder_df = df[
            (df['Delivery_Date'].isna()) |
            (df['Delivery_Date'] > df['Lead_Time'])
        ].copy()
        # 移除無效行並重置索引，僅保留指定列
        reminder_df = reminder_df[['Project_Name', 'Lead_Time', 'Delivery_Date', 'Remarks']].dropna(how='all').reset_index(drop=True)
        if not reminder_df.empty:
            # 使用 HTML 創建獨立滾動容器
            reminder_html = f"""
            <div class="reminder-section">
                <h3>Reminder: Delivery Date Issues</h3>
                <p>The following projects have Delivery Date either blank or later than Lead Time:</p>
                {reminder_df.to_html(index=False)}
            </div>
            """
            st.markdown(reminder_html, unsafe_allow_html=True)

# Footer information
st.markdown("---")
st.markdown("**YIP SHING Project Management System** | Real-time Project Status Monitoring")
