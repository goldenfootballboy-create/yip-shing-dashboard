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
        padding-right: 0px; /* 減小與圖片的間距 */
        vertical-align: top;
        padding-top: 5px;
        word-wrap: break-word;
    }
    .progress-wrapper {
        display: flex;
        flex-direction: column; /* 垂直排列進度條和說明 */
        align-items: flex-start;
        flex-grow: 1;
    }
    .custom-progress {
        height: 20px;
        background-color: #e0e0e0;
        border-radius: 10px;
        overflow: hidden;
        width: 150px; /* 保持收窄的進度條 */
        padding: 0; /* 移除內部填充 */
    }
    .custom-progress-fill {
        height: 100%;
        transition: width 0.3s ease;
        border-radius: 10px; /* 與外框一致 */
    }
    .progress-text {
        margin-top: 5px; /* 百分比與進度條的間距 */
        vertical-align: middle;
    }
    .progress-explanation {
        margin-left: 0px; /* 說明與百分比的間距 */
        vertical-align: middle;
        font-size: 12px;
        color: #333;
    }
    .kta38-icon {
        width: 30px; /* 保持圖片大小 */
        height: auto; /* 自動調整高度以保持比例 */
        margin: 0 2px; /* 減小與 Project Name 和進度條的間距 */
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
    index=years.index("2025"),
    help="Select the year to view"
)

# Load CSV data
def load_data():
    csv_file = "projects.csv"
    if not os.path.exists(csv_file):
        st.error(f"Cannot find {csv_file}! Ensure the file is located in: {script_dir}")
        return None

    try:
        data_df = pd.read_csv(csv_file, encoding='utf-8', sep=',')  # 移除 dayfirst=True
        required_columns = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        missing_columns = [col for col in required_columns if col not in data_df.columns]
        if missing_columns:
            st.error(f"CSV file is missing required columns: {', '.join(missing_columns)}")
            return None

        date_columns = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
        for col in date_columns:
            if col in data_df.columns:
                data_df[col] = pd.to_datetime(data_df[col], errors='coerce')  # 移除 dayfirst=True
            else:
                st.warning(f"Column {col} is missing.")
        return data_df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
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
        if 'Year' in df.columns and 'Lead_Time' in df.columns:
            filtered_df = df[df['Year'] == int(selected_year)].copy()
            if selected_month != "--":
                if pd.api.types.is_datetime64_any_dtype(filtered_df['Lead_Time']):
                    month_index = month_options.index(selected_month)
                    if month_index != 0:
                        filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_index]
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
                    month_index = month_options.index(selected_month)
                    if month_index != 0:
                        filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_index]
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
        for col in available_columns[1:]:
            if pd.api.types.is_datetime64_any_dtype(display_df[col]):
                display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')

        # Calculate progress for each project
        current_date = datetime.now()
        for index, row in display_df.iterrows():
            progress = 0

            # Check Parts_Arrival_Date (30%)
            parts_arrival_met = False
            if pd.notna(row['Parts_Arrival_Date']):
                try:
                    parts_arrival_date = pd.to_datetime(row['Parts_Arrival_Date'], dayfirst=True).date()
                    parts_arrival_met = parts_arrival_date <= current_date.date()
                    if parts_arrival_met:
                        progress += 30
                except ValueError:
                    pass

            # Check Installation_Complete_Date (40%)
            install_met = False
            if pd.notna(row['Installation_Complete_Date']):
                try:
                    install_date = pd.to_datetime(row['Installation_Complete_Date'], dayfirst=True).date()
                    install_met = install_date <= current_date.date()
                    if install_met:
                        progress += 40
                except ValueError:
                    pass

            # Check Testing_Date (10%)
            testing_met = False
            if pd.notna(row['Testing_Date']):
                try:
                    testing_date = pd.to_datetime(row['Testing_Date'], dayfirst=True).date()
                    testing_met = testing_date <= current_date.date()
                    if testing_met:
                        progress += 10
                except ValueError:
                    pass

            # Check Cleaning (10%)
            cleaning_met = row['Cleaning'] == 'YES' if pd.notna(row['Cleaning']) else False
            if cleaning_met:
                progress += 10

            # Check Delivery_Date (10%, and set to 100% if all other conditions met)
            delivery_met = False
            if pd.notna(row['Delivery_Date']):
                try:
                    delivery_date = pd.to_datetime(row['Delivery_Date'], dayfirst=True).date()
                    delivery_met = delivery_date <= current_date.date()
                    if delivery_met:
                        progress += 10
                except ValueError:
                    pass

            # Ensure 100% if all milestones are met
            all_milestones_met = parts_arrival_met and install_met and testing_met and cleaning_met and delivery_met
            if all_milestones_met:
                progress = 100
            progress = min(progress, 100)

            # 動態計算進度條顏色（根據 0%、30%、70%、80%、90%、100% 設置）
            if progress == 0:
                color = '#e0e0e0'  # 0% 無色（灰色，與背景接近）
            elif progress < 30:
                # 0% 到 30%：從 #e0e0e0 漸變到橙紅 #ff4500
                r = int(224 + (255 - 224) * (progress / 30))
                g = int(224 + (69 - 224) * (progress / 30))
                b = int(224 + (0 - 224) * (progress / 30))
                color = f'rgb({r}, {g}, {b})'
            elif progress < 70:
                # 30% 到 70%：從橙紅 #ff4500 漸變到黃 #ffff00
                r = 255
                g = int(69 + (255 - 69) * ((progress - 30) / 40))
                b = int(0 + (0 - 0) * ((progress - 30) / 40))
                color = f'rgb({r}, {g}, {b})'
            elif progress < 80:
                # 70% 到 80%：從黃 #ffff00 漸變到黃綠 #9acd32
                r = int(255 + (154 - 255) * ((progress - 70) / 10))
                g = 255
                b = int(0 + (50 - 0) * ((progress - 70) / 10))
                color = f'rgb({r}, {g}, {b})'
            elif progress < 90:
                # 80% 到 90%：從黃綠 #9acd32 漸變到綠 #00ff00
                r = int(154 + (0 - 154) * ((progress - 80) / 10))
                g = int(205 + (255 - 205) * ((progress - 80) / 10))
                b = int(50 + (0 - 50) * ((progress - 80) / 10))
                color = f'rgb({r}, {g}, {b})'
            elif progress < 100:
                # 90% 到 100%：從綠 #00ff00 漸變到藍 #0000ff
                r = int(0 + (0 - 0) * ((progress - 90) / 10))
                g = int(255 + (0 - 255) * ((progress - 90) / 10))
                b = int(0 + (255 - 0) * ((progress - 90) / 10))
                color = f'rgb({r}, {g}, {b})'
            else:
                color = '#0000ff'  # 100% 藍

            # 設置固定進度說明
            explanation = ""
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

            # 檢查 Description 是否包含 KTA38，決定是否添加圖片
            description_text = str(row['Description']).strip().replace('\n', '').replace('\r', '') if pd.notna(row['Description']) else ""
            has_kta38 = 'KTA38' in description_text.upper()
            has_kta50 = 'KTA50' in description_text.upper()

            # 使用 Streamlit 原生組件渲染進度條，圖片放在中間
            col1, col2, col3 = st.columns([1, 0.2, 6])  # 收窄整體寬度比例
            with col1:
                st.write(row['Project_Name'], unsafe_allow_html=False)
            with col2:
                if has_kta38:
                    st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)  # 圖片在中間
                elif has_kta50:
                    st.image("https://i.imgur.com/3Cb2Nqj.png", width=30)  # 圖片在中間
            with col3:
                progress_value = progress / 100
                st.markdown(
                    f'<div class="custom-progress"><div class="custom-progress-fill" style="width: {progress_value * 100}%; background-color: {color};"></div></div>',
                    unsafe_allow_html=True
                )
                col_percent, col_explain = st.columns([1, 20])  # 百分比和說明平排
                with col_percent:
                    st.write(f"{progress}%", unsafe_allow_html=False)
                with col_explain:
                    st.write(explanation, unsafe_allow_html=False)

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

    # Reminder section for Delivery_Date issues
    if 'Delivery_Date' in df.columns and 'Lead_Time' in df.columns:
        reminder_df = df[
            (df['Delivery_Date'].isna()) |
            (df['Delivery_Date'] > df['Lead_Time'])
        ].copy()
        reminder_df = reminder_df[['Project_Name', 'Lead_Time', 'Delivery_Date', 'Remarks']].dropna(how='all').reset_index(drop=True)
        if not reminder_df.empty:
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
