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
    .progress-wrapper {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        flex-grow: 1;
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
    }
    .progress-explanation {
        margin-left: 0px;
        font-size: 12px;
        color: #333;
    }
    .kta38-icon {
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

# 標題（居中）
st.markdown('<div class="main-header"><div class="title">YIP SHING Project Status Dashboard</div></div>',
            unsafe_allow_html=True)

st.markdown("---")

# 側邊欄設置
st.sidebar.title("Dashboard Controls")
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
    index=years.index("2025"),
    help="Select the year to view"
)

# Load CSV data with strict YYYY-MM-DD format
def load_data():
    """Load data from CSV file with YYYY-MM-DD date format"""
    csv_file = "projects.csv"
    if not os.path.exists(csv_file):
        st.error(f"Cannot find {csv_file}! Ensure the file is located in: {script_dir}")
        st.info(f"Current working directory: {os.getcwd()}")
        st.info(
            "Suggestions: 1. Verify projects.csv exists in the same directory as app.py. "
            "2. Check filename (including case and extension). 3. Ensure the file has read permissions.")
        return None

    try:
        # 定義日期欄位與解析函數（強制 YYYY-MM-DD）
        date_columns = [
            'Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date',
            'Testing_Date', 'Delivery_Date'
        ]

        # 使用 parse_dates 並指定格式
        data_df = pd.read_csv(
            csv_file,
            encoding='utf-8',
            sep=',',
            parse_dates=date_columns,
            date_format='%Y-%m-%d',  # 強制 YYYY-MM-DD
            dayfirst=False
        )

        # 檢查必要欄位
        required_columns = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        missing_columns = [col for col in required_columns if col not in data_df.columns]
        if missing_columns:
            st.error(f"CSV file is missing the following required columns: {', '.join(missing_columns)}")
            st.info("Ensure the CSV file contains: Project_Type, Project_Name, Year, Lead_Time")
            return None

        # 驗證日期欄位是否成功解析
        for col in date_columns:
            if col in data_df.columns:
                if data_df[col].isna().all():
                    st.warning(f"Column '{col}' contains no valid dates (all NaT). Check format: YYYY-MM-DD")
                elif not pd.isna(data_df[col]).all():
                    # 確保是 datetime
                    data_df[col] = pd.to_datetime(data_df[col], errors='coerce')
            else:
                st.warning(f"Column '{col}' is missing in the CSV file.")

        return data_df

    except Exception as e:
        st.error(f"Error reading CSV file: {str(e)}")
        st.info("Ensure all date columns use format: YYYY-MM-DD (e.g., 2025-06-15)")
        return None

# Load data
df = load_data()

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
        filtered_df = df[df['Year'] == int(selected_year)].copy()
        if selected_month != "--" and pd.api.types.is_datetime64_any_dtype(filtered_df['Lead_Time']):
            month_index = month_options.index(selected_month)
            if month_index != 0:
                filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_index]
    else:
        filtered_df = df[df['Project_Type'] == selected_project_type].copy()
        filtered_df = filtered_df[filtered_df['Year'] == int(selected_year)].copy()
        if selected_month != "--" and pd.api.types.is_datetime64_any_dtype(filtered_df['Lead_Time']):
            month_index = month_options.index(selected_month)
            if month_index != 0:
                filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_index]

    # Calculate project counts by Project_Type
    total_projects = len(filtered_df)
    project_counts = filtered_df['Project_Type'].value_counts().to_dict()

    # Display project count
    title_suffix = f"{selected_year} {selected_month} Project Count" if selected_month != "--" else f"{selected_year} All Months Project Count"
    st.markdown(f"### {selected_project_type} - {title_suffix}")

    col1, col2, *other_cols = st.columns([1] + [1] * len(project_counts))
    with col1:
        st.write(f"**Total Projects:** {total_projects}")
    for i, (project_type, count) in enumerate(project_counts.items()):
        with other_cols[i]:
            st.write(f"**{project_type}:** {count}")

    # Display projects and milestones with progress bar
    if total_projects > 0:
        details_title = f"{selected_year} {selected_month} {selected_project_type} Project Details" if selected_month != "--" else f"{selected_year} All Months {selected_project_type} Project Details"
        st.markdown(f"### {details_title}")

        milestone_columns = [
            'Project_Name', 'Description', 'Parts_Arrival_Date', 'Installation_Complete_Date',
            'Testing_Date', 'Cleaning', 'Delivery_Date', 'Remarks'
        ]
        available_columns = [col for col in milestone_columns if col in filtered_df.columns]
        display_df = filtered_df[available_columns].copy()

        # Format date columns to string for display
        for col in available_columns:
            if col != 'Project_Name' and pd.api.types.is_datetime64_any_dtype(display_df[col]):
                display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')

        # Calculate progress for each project
        current_date = datetime.now().date()

        for index, row in display_df.iterrows():
            progress = 0
            parts_arrival_met = install_met = testing_met = cleaning_met = delivery_met = False

            # Parts Arrival (30%)
            if pd.notna(row.get('Parts_Arrival_Date')):
                try:
                    parts_date = pd.to_datetime(row['Parts_Arrival_Date']).date()
                    if parts_date <= current_date:
                        progress += 30
                        parts_arrival_met = True
                except:
                    pass

            # Installation Complete (40%)
            if pd.notna(row.get('Installation_Complete_Date')):
                try:
                    install_date = pd.to_datetime(row['Installation_Complete_Date']).date()
                    if install_date <= current_date:
                        progress += 40
                        install_met = True
                except:
                    pass

            # Testing (10%)
            if pd.notna(row.get('Testing_Date')):
                try:
                    testing_date = pd.to_datetime(row['Testing_Date']).date()
                    if testing_date <= current_date:
                        progress += 10
                        testing_met = True
                except:
                    pass

            # Cleaning (10%)
            cleaning_met = str(row.get('Cleaning', '')).strip().upper() == 'YES'
            if cleaning_met:
                progress += 10

            # Delivery (10%)
            if pd.notna(row.get('Delivery_Date')):
                try:
                    delivery_date = pd.to_datetime(row['Delivery_Date']).date()
                    if delivery_date <= current_date:
                        progress += 10
                        delivery_met = True
                except:
                    pass

            # Force 100% if all milestones met
            if parts_arrival_met and install_met and testing_met and cleaning_met and delivery_met:
                progress = 100
            progress = min(progress, 100)

            # Dynamic color
            if progress == 0:
                color = '#e0e0e0'
            elif progress < 30:
                ratio = progress / 30
                r = int(224 + (255 - 224) * ratio)
                g = int(224 + (69 - 224) * ratio)
                b = int(224 + (0 - 224) * ratio)
                color = f'rgb({r},{g},{b})'
            elif progress < 70:
                ratio = (progress - 30) / 40
                g = int(69 + (255 - 69) * ratio)
                color = f'rgb(255,{g},0)'
            elif progress < 80:
                ratio = (progress - 70) / 10
                r = int(255 + (154 - 255) * ratio)
                b = int(0 + 50 * ratio)
                color = f'rgb({r},255,{b})'
            elif progress < 90:
                ratio = (progress - 80) / 10
                r = int(154 + (0 - 154) * ratio)
                g = int(205 + (255 - 205) * ratio)
                b = int(50 + (0 - 50) * ratio)
                color = f'rgb({r},{g},{b})'
            elif progress < 100:
                ratio = (progress - 90) / 10
                g = int(255 + (0 - 255) * ratio)
                b = int(0 + 255 * ratio)
                color = f'rgb(0,{g},{b})'
            else:
                color = '#0000ff'

            # Progress explanation
            explanation_map = {
                0: "Not Start",
                30: "Parts Arrived",
                70: "Installation Completed",
                80: "Testing Completed",
                90: "Cleaning Completed",
                100: "Project Completed"
            }
            explanation = explanation_map.get(progress, f"{progress}% Progress")

            # Check for KTA38/KTA50 in Description
            desc = str(row.get('Description', '')).upper()
            has_kta38 = 'KTA38' in desc
            has_kta50 = 'KTA50' in desc

            # Render row
            col1, col2, col3 = st.columns([2, 0.4, 6])
            with col1:
                st.markdown(f"**{row['Project_Name']}**")
            with col2:
                if has_kta38:
                    st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
                elif has_kta50:
                    st.image("https://i.imgur.com/oJNLgDG.png", width=30)
            with col3:
                st.markdown(
                    f'<div class="custom-progress"><div class="custom-progress-fill" style="width: {progress}%; background-color: {color};"></div></div>',
                    unsafe_allow_html=True
                )
                pcol1, pcol2 = st.columns([1, 5])
                with pcol1:
                    st.write(f"**{progress}%**")
                with pcol2:
                    st.write(explanation)

        # Display milestone table
        st.markdown('<div class="milestone-table">', unsafe_allow_html=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.warning(f"No {selected_project_type} projects found in {selected_year} {selected_month}.")

    # Reminder section
    if 'Delivery_Date' in df.columns and 'Lead_Time' in df.columns:
        reminder_df = df[
            (df['Delivery_Date'].isna()) |
            (df['Delivery_Date'] > df['Lead_Time'])
        ][['Project_Name', 'Lead_Time', 'Delivery_Date', 'Remarks']].copy()

        if not reminder_df.empty:
            reminder_df['Lead_Time'] = reminder_df['Lead_Time'].dt.strftime('%Y-%m-%d')
            reminder_df['Delivery_Date'] = reminder_df['Delivery_Date'].dt.strftime('%Y-%m-%d')
            reminder_html = f"""
            <div class="reminder-section">
                <h3>Reminder: Delivery Date Issues</h3>
                <p>The following projects have Delivery Date blank or later than Lead Time:</p>
                {reminder_df.to_html(index=False, escape=False)}
            </div>
            """
            st.markdown(reminder_html, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("**YIP SHING Project Management System** | Real-time Project Status Monitoring")