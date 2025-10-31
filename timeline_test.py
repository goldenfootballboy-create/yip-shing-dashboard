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


# Load CSV data
def load_data():
    """Load data from CSV file with explicit MM/DD/YYYY format, only parse existing columns"""
    csv_file = "projects.csv"
    if not os.path.exists(csv_file):
        st.error(f"Cannot find {csv_file}! Ensure the file is located in: {script_dir}")
        st.info(f"Current working directory: {os.getcwd()}")
        st.info(
            "Suggestions: 1. Verify projects.csv exists in the same directory as app.py. 2. Check filename (including case and extension). 3. Ensure the file has read permissions.")
        return None

    try:
        # 先讀取一次，取得欄位
        data_df = pd.read_csv(csv_file, encoding='utf-8', sep=',')

        # 定義可能存在的日期欄位
        possible_date_columns = [
            'Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date',
            'Testing_Date', 'Delivery_Date'
        ]

        # 只對存在的欄位解析
        existing_date_columns = [col for col in possible_date_columns if col in data_df.columns]

        if existing_date_columns:
            data_df = pd.read_csv(
                csv_file,
                encoding='utf-8',
                sep=',',
                parse_dates=existing_date_columns,
                date_format='%m/%d/%Y',
                dayfirst=False
            )
            st.info(f"Parsed date columns: {', '.join(existing_date_columns)}")
        else:
            st.warning("No date columns found. Proceeding without date parsing.")

        # 必要欄位檢查
        required_columns = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        missing_required = [col for col in required_columns if col not in data_df.columns]
        if missing_required:
            st.error(f"Missing required columns: {', '.join(missing_required)}")
            return None

        # 補救 Lead_Time
        if 'Lead_Time' in data_df.columns and not pd.api.types.is_datetime64_any_dtype(data_df['Lead_Time']):
            data_df['Lead_Time'] = pd.to_datetime(data_df['Lead_Time'], errors='coerce', format='%m/%d/%Y')

        return data_df

    except Exception as e:
        st.error(f"Error reading CSV: {str(e)}")
        return None

# Load data
df = load_data()

if df is None:
    st.error("Failed to load data. Please check the console or previous messages for details.")
else:
    # Define month options
    month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
    selected_month = st.sidebar.selectbox(
        "Lead Time:",
        month_options,
        index=0,
        help="Select the lead time to view or '--' for all lead times"
    )

    # Filter data
    if selected_project_type == "All":
        filtered_df = df[df['Year'] == int(selected_year)].copy()
    else:
        filtered_df = df[(df['Project_Type'] == selected_project_type) & (df['Year'] == int(selected_year))].copy()

    if selected_month != "--" and 'Lead_Time' in filtered_df.columns:
        if pd.api.types.is_datetime64_any_dtype(filtered_df['Lead_Time']):
            month_index = month_options.index(selected_month)
            if month_index != 0:
                filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_index]

    # Project counts
    total_projects = len(filtered_df)
    project_counts = filtered_df['Project_Type'].value_counts().to_dict()

    # Display project count
    month_str = selected_month if selected_month != "--" else "All Months"
    if selected_project_type == "All":
        st.markdown(f"### All - {selected_year} {month_str} Project Count")
    else:
        st.markdown(f"### {selected_project_type} - {selected_year} {month_str} Project Count")

    col1, col2, *other_cols = st.columns([1] + [1] * (len(project_counts) + 1))
    with col1:
        st.write(f"Total Projects: {total_projects}")
    for i, (ptype, count) in enumerate(project_counts.items()):
        with other_cols[i]:
            st.write(f"{ptype}: {count}")

    # Display projects
    if total_projects > 0:
        st.markdown(f"### {selected_year} {month_str} {selected_project_type} Project Details")

        milestone_columns = [
            'Project_Name', 'Description', 'Parts_Arrival_Date', 'Installation_Complete_Date',
            'Testing_Date', 'Cleaning', 'Delivery_Date', 'Remarks'
        ]
        available_columns = [col for col in milestone_columns if col in filtered_df.columns]
        display_df = filtered_df[available_columns].copy()

        # Format dates for display only
        for col in available_columns:
            if col in ['Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date', 'Lead_Time']:
                if pd.api.types.is_datetime64_any_dtype(display_df[col]):
                    display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')

        # Calculate progress using original datetime columns
        current_date = datetime.now()
        progress_data = []

        for idx, row in filtered_df.iterrows():
            progress = 0

            # Parts Arrival (30%)
            parts_arrival_met = False
            if 'Parts_Arrival_Date' in filtered_df.columns and pd.notna(row['Parts_Arrival_Date']):
                if row['Parts_Arrival_Date'].date() < current_date.date():
                    parts_arrival_met = True
                    progress += 30

            # Installation (40%)
            install_met = False
            if 'Installation_Complete_Date' in filtered_df.columns and pd.notna(row['Installation_Complete_Date']):
                if row['Installation_Complete_Date'].date() < current_date.date():
                    install_met = True
                    progress += 40

            # Testing (10%)
            testing_met = False
            if 'Testing_Date' in filtered_df.columns and pd.notna(row['Testing_Date']):
                if row['Testing_Date'].date() < current_date.date():
                    testing_met = True
                    progress += 10

            # Cleaning (10%)
            cleaning_met = False
            if 'Cleaning' in filtered_df.columns and pd.notna(row['Cleaning']):
                cleaning_met = str(row['Cleaning']).strip().upper() == 'YES'
                if cleaning_met:
                    progress += 10

            # Delivery (10%)
            delivery_met = False
            if 'Delivery_Date' in filtered_df.columns and pd.notna(row['Delivery_Date']):
                if row['Delivery_Date'].date() < current_date.date():
                    delivery_met = True
                    progress += 10

            # Force 100% if all met
            all_met = (
                ('Parts_Arrival_Date' not in filtered_df.columns or parts_arrival_met) and
                ('Installation_Complete_Date' not in filtered_df.columns or install_met) and
                ('Testing_Date' not in filtered_df.columns or testing_met) and
                ('Cleaning' not in filtered_df.columns or cleaning_met) and
                ('Delivery_Date' not in filtered_df.columns or delivery_met)
            )
            if all_met:
                progress = 100
            progress = min(progress, 100)

            # Color gradient
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

            # Explanation
            explanation = "Not Start"
            if parts_arrival_met:
                explanation = "Parts Arrived"
            if install_met:
                explanation = "Installation Completed"
            if testing_met:
                explanation = "Testing Completed"
            if cleaning_met:
                explanation = "Cleaning Completed"
            if delivery_met:
                explanation = "Project Completed"
            elif progress > 0:
                explanation = f"{progress}% In Progress"

            # KTA icons
            has_kta38 = False
            has_kta50 = False
            if 'Description' in filtered_df.columns and pd.notna(row['Description']):
                desc = str(row['Description']).upper()
                has_kta38 = 'KTA38' in desc
                has_kta50 = 'KTA50' in desc

            progress_data.append({
                'index': idx,
                'Project_Name': row['Project_Name'],
                'progress': progress,
                'explanation': explanation,
                'color': color,
                'has_kta38': has_kta38,
                'has_kta50': has_kta50
            })

        # Render progress bars
        for item in progress_data:
            disp_row = display_df.loc[item['index']]
            col1, col2, col3 = st.columns([1, 0.2, 6])
            with col1:
                st.write(disp_row['Project_Name'])
            with col2:
                if item['has_kta38']:
                    st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
                elif item['has_kta50']:
                    st.image("https://i.imgur.com/3Cb2Nqj.png", width=30)
            with col3:
                st.markdown(
                    f'<div class="custom-progress"><div class="custom-progress-fill" style="width: {item["progress"]}%; background-color: {item["color"]};"></div></div>',
                    unsafe_allow_html=True
                )
                pcol1, pcol2 = st.columns([1, 20])
                with pcol1:
                    st.write(f"{item['progress']}%")
                with pcol2:
                    st.write(item['explanation'])

        # Display table
        st.markdown('<div class="milestone-table">', unsafe_allow_html=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.warning(f"No {selected_project_type} projects found in {selected_year} {month_str}.")

    # Reminder
    if 'Delivery_Date' in df.columns and 'Lead_Time' in df.columns:
        reminder_df = df[
            (df['Delivery_Date'].isna()) |
            (df['Delivery_Date'] > df['Lead_Time'])
        ][['Project_Name', 'Lead_Time', 'Delivery_Date', 'Remarks']].dropna(how='all')
        if not reminder_df.empty:
            st.markdown(f"""
            <div class="reminder-section">
                <h3>Reminder: Delivery Date Issues</h3>
                <p>The following projects have Delivery Date either blank or later than Lead Time:</p>
                {reminder_df.to_html(index=False)}
            </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("**YIP SHING Project Management System** | Real-time Project Status Monitoring")