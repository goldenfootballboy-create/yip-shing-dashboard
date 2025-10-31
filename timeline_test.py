import streamlit as st
import pandas as pd
import os
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

st.set_page_config(page_title="YIP SHING Project Status Dashboard", layout="wide", initial_sidebar_state="expanded")

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

st.sidebar.title("Dashboard Controls")
project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
selected_project_type = st.sidebar.selectbox("Select Project Type:", project_types, index=0)
years = ["2024", "2025", "2026"]
selected_year = st.sidebar.selectbox("Select Year:", years, index=years.index("2025"))
month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
selected_month = st.sidebar.selectbox("Lead Time:", month_options, index=0)

def safe_date(val):
    if pd.isna(val): return None
    try:
        if isinstance(val, str):
            return pd.to_datetime(val, format='%m/%d/%Y').date()
        return val.date()
    except:
        return None

def load_data():
    csv_file = "projects.csv"
    if not os.path.exists(csv_file):
        st.error(f"Cannot find {csv_file}!")
        return None
    try:
        df = pd.read_csv(csv_file, encoding='utf-8', sep=',')
        date_cols = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
        existing = [c for c in date_cols if c in df.columns]
        if existing:
            df = pd.read_csv(csv_file, encoding='utf-8', sep=',', parse_dates=existing, date_format='%m/%d/%Y')
        for c in date_cols:
            if c in df.columns and not pd.api.types.is_datetime64_any_dtype(df[c]):
                df[c] = pd.to_datetime(df[c], errors='coerce', format='%m/%d/%Y')
        required = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        if not all(c in df.columns for c in required):
            st.error("Missing required columns.")
            return None
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
if selected_month != "--" and 'Lead_Time' in filtered_df.columns:
    month_idx = month_options.index(selected_month)
    if month_idx > 0:
        filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_idx]

total_projects = len(filtered_df)
project_counts = filtered_df['Project_Type'].value_counts().to_dict()

month_str = selected_month if selected_month != "--" else "All Months"
st.markdown(f"### {selected_project_type} - {selected_year} {month_str} Project Count")
col1, *cols = st.columns([1] + [1]*len(project_counts))
with col1: st.write(f"Total: {total_projects}")
for i, (k, v) in enumerate(project_counts.items()):
    with cols[i]: st.write(f"{k}: {v}")

if total_projects > 0:
    st.markdown(f"### Project Details")
    display_cols = ['Project_Name', 'Description', 'Parts_Arrival_Date', 'Installation_Complete_Date',
                    'Testing_Date', 'Cleaning', 'Delivery_Date', 'Remarks']
    avail_cols = [c for c in display_cols if c in filtered_df.columns]
    display_df = filtered_df[avail_cols].copy()
    for c in avail_cols:
        if c in ['Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']:
            display_df[c] = pd.to_datetime(display_df[c], errors='coerce').dt.strftime('%Y-%m-%d')

    current_date = datetime.now()
    progress_data = []

    for idx, row in filtered_df.iterrows():
        progress = 0
        parts_met = install_met = test_met = clean_met = delivery_met = False

        if 'Parts_Arrival_Date' in filtered_df.columns:
            d = safe_date(row['Parts_Arrival_Date'])
            if d and d < current_date.date():
                parts_met = True
                progress += 30
        if 'Installation_Complete_Date' in filtered_df.columns:
            d = safe_date(row['Installation_Complete_Date'])
            if d and d < current_date.date():
                install_met = True
                progress += 40
        if 'Testing_Date' in filtered_df.columns:
            d = safe_date(row['Testing_Date'])
            if d and d < current_date.date():
                test_met = True
                progress += 10
        if 'Cleaning' in filtered_df.columns and pd.notna(row['Cleaning']):
            if str(row['Cleaning']).strip().upper() == 'YES':
                clean_met = True
                progress += 10
        if 'Delivery_Date' in filtered_df.columns:
            d = safe_date(row['Delivery_Date'])
            if d and d < current_date.date():
                delivery_met = True
                progress += 10

        if all([parts_met, install_met, test_met, clean_met, delivery_met]):
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
        exp = "Not Start"
        if parts_met: exp = "Parts Arrived"
        if install_met: exp = "Installation Completed"
        if test_met: exp = "Testing Completed"
        if clean_met: exp = "Cleaning Completed"
        if delivery_met: exp = "Project Completed"
        elif progress > 0: exp = f"{progress}% In Progress"

        # Icons
        k38 = k50 = False
        if 'Description' in filtered_df.columns and pd.notna(row['Description']):
            desc = str(row['Description']).upper()
            k38 = 'KTA38' in desc
            k50 = 'KTA50' in desc

        progress_data.append({
            'index': idx, 'name': row['Project_Name'], 'progress': progress,
            'exp': exp, 'color': color, 'k38': k38, 'k50': k50
        })

    for item in progress_data:
        disp_row = display_df.loc[item['index']]
        c1, c2, c3 = st.columns([1, 0.2, 6])
        with c1: st.write(disp_row['Project_Name'])
        with c2:
            if item['k38']: st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
            elif item['k50']: st.image("https://i.imgur.com/3Cb2Nqj.png", width=30)
        with c3:
            st.markdown(f'<div class="custom-progress"><div class="custom-progress-fill" style="width: {item["progress"]}%; background-color: {item["color"]};"></div></div>', unsafe_allow_html=True)
            pc1, pc2 = st.columns([1, 20])
            with pc1: st.write(f"{item['progress']}%")
            with pc2: st.write(item['exp'])

    st.markdown('<div class="milestone-table">', unsafe_allow_html=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.warning("No projects found.")

if 'Delivery_Date' in df.columns and 'Lead_Time' in df.columns:
    reminder = df[df['Delivery_Date'].isna() | (df['Delivery_Date'] > df['Lead_Time'])][['Project_Name', 'Lead_Time', 'Delivery_Date', 'Remarks']]
    if not reminder.empty:
        st.markdown(f"<div class='reminder-section'><h3>Delivery Date Issues</h3>{reminder.to_html(index=False)}</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("**YIP SHING Project Management System**")