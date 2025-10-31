import streamlit as st
import pandas as pd
import os
from datetime import datetime

# -------------------------------------------------
# 1. 基本設定
# -------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

st.set_page_config(
    page_title="YIP SHING Project Status Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# 2. 完整 CSS
# -------------------------------------------------
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

# -------------------------------------------------
# 3. 標題
# -------------------------------------------------
st.markdown('<div class="main-header"><div class="title">YIP SHING Project Status Dashboard</div></div>',
            unsafe_allow_html=True)
st.markdown("---")

# -------------------------------------------------
# 4. 側邊欄
# -------------------------------------------------
st.sidebar.title("Dashboard Controls")
st.sidebar.markdown("### Project Type Selection")
project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
selected_project_type = st.sidebar.selectbox(
    "Select Project Type:",
    project_types,
    index=0,
    help="Select the project type status to view"
)

years = ["2024", "2025", "2026"]
selected_year = st.sidebar.selectbox(
    "Select Year:",
    years,
    index=years.index("2025"),
    help="Select the year to view"
)

month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
selected_month = st.sidebar.selectbox(
    "Lead Time:",
    month_options,
    index=0,
    help="Select the lead time to view or '--' for all lead times"
)

# -------------------------------------------------
# 5. 讀取 CSV（支援 YYYY-MM-DD）
# -------------------------------------------------
def load_data():
    csv_file = "projects.csv"
    if not os.path.exists(csv_file):
        st.error(f"Cannot find {csv_file}! Ensure it's in the same directory.")
        return None
    try:
        df = pd.read_csv(csv_file, encoding='utf-8', sep=',')
        required = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        if not all(col in df.columns for col in required):
            st.error(f"Missing required columns: {', '.join([c for c in required if c not in df.columns])}")
            return None

        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')

        date_cols = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            else:
                st.info(f"Optional column '{col}' is missing. It will be ignored.")

        return df
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return None

df = load_data()
if df is None:
    st.stop()

# -------------------------------------------------
# 6. 篩選（僅影響左側）
# -------------------------------------------------
filtered_df = df[df['Year'] == int(selected_year)].copy()

if selected_project_type != "All":
    filtered_df = filtered_df[filtered_df['Project_Type'] == selected_project_type]

if selected_month != "--" and 'Lead_Time' in filtered_df.columns:
    if pd.api.types.is_datetime64_any_dtype(filtered_df['Lead_Time']):
        month_idx = month_options.index(selected_month)
        if month_idx > 0:
            filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_idx]

# -------------------------------------------------
# 7. 統計
# -------------------------------------------------
total_projects = len(filtered_df)
project_counts = filtered_df['Project_Type'].value_counts().to_dict()

month_str = selected_month if selected_month != "--" else "All Months"
st.markdown(f"### {selected_project_type} - {selected_year} {month_str} Project Count")
col1, *rest = st.columns([1] + [1]*len(project_counts))
with col1: st.write(f"**Total: {total_projects}**")
for i, (pt, cnt) in enumerate(project_counts.items()):
    with rest[i]: st.write(f"**{pt}: {cnt}**")

# -------------------------------------------------
# 8. 主畫面：左側 + 右側延誤進度條（全局）
# -------------------------------------------------
if total_projects > 0:
    col_left, col_right = st.columns([3, 0.5])

    with col_left:
        st.markdown(f"### {selected_year} {month_str} {selected_project_type} Project Details")

        # 顯示用 DataFrame
        milestone_cols = ['Project_Name', 'Description', 'Parts_Arrival_Date', 'Installation_Complete_Date',
                          'Testing_Date', 'Cleaning', 'Delivery_Date', 'Remarks']
        avail_cols = [c for c in milestone_cols if c in filtered_df.columns]
        display_df = filtered_df[avail_cols].copy()
        for c in avail_cols[1:]:
            if pd.api.types.is_datetime64_any_dtype(display_df[c]):
                display_df[c] = display_df[c].dt.strftime('%Y-%m-%d')

        current_date = datetime.now()

        # 左側：原始進度條
        for _, row in filtered_df.iterrows():
            progress = 0
            if 'Parts_Arrival_Date' in filtered_df.columns and pd.notna(row['Parts_Arrival_Date']):
                if row['Parts_Arrival_Date'].date() < current_date.date():
                    progress += 30
            if 'Installation_Complete_Date' in filtered_df.columns and pd.notna(row['Installation_Complete_Date']):
                if row['Installation_Complete_Date'].date() < current_date.date():
                    progress += 40
            if 'Testing_Date' in filtered_df.columns and pd.notna(row['Testing_Date']):
                if row['Testing_Date'].date() < current_date.date():
                    progress += 10
            if 'Cleaning' in filtered_df.columns and str(row.get('Cleaning','')).strip().upper() == 'YES':
                progress += 10
            if 'Delivery_Date' in filtered_df.columns and pd.notna(row['Delivery_Date']):
                if row['Delivery_Date'].date() < current_date.date():
                    progress += 10
            progress = min(progress, 100)

            # 顏色
            if progress == 0: color = '#e0e0e0'
            elif progress < 30: color = f'rgb({int(224+(255-224)*(progress/30))}, {int(224+(69-224)*(progress/30))}, {int(224+(0-224)*(progress/30))})'
            elif progress < 70: color = f'rgb(255, {int(69+(255-69)*((progress-30)/40))}, 0)'
            elif progress < 80: color = f'rgb({int(255+(154-255)*((progress-70)/10))}, 255, {int(0+(50-0)*((progress-70)/10))})'
            elif progress < 90: color = f'rgb({int(154+(0-154)*((progress-80)/10))}, {int(205+(255-205)*((progress-80)/10))}, {int(50+(0-50)*((progress-80)/10))})'
            elif progress < 100: color = f'rgb(0, {int(255+(0-255)*((progress-90)/10))}, {int(0+(255-0)*((progress-90)/10))})'
            else: color = '#0000ff'

            # 說明
            exp_map = {0:"Not Start",30:"Parts Arrived",70:"Installation Completed",
                       80:"Testing Completed",90:"Cleaning Completed",100:"Project Completed"}
            explanation = exp_map.get(progress, f"{progress}% In Progress")

            # 圖示
            desc = str(row.get('Description','')).upper()
            k38 = 'KTA38' in desc
            k50 = 'KTA50' in desc

            # 進度條
            c1, c2, c3 = st.columns([1, 0.2, 6])
            with c1: st.write(row['Project_Name'])
            with c2:
                if k38: st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
                elif k50: st.image("https://i.imgur.com/oJNLgDG.png", width=30)
            with c3:
                st.markdown(f'<div class="custom-progress"><div class="custom-progress-fill" style="width:{progress}%;background:{color};"></div></div>', unsafe_allow_html=True)
                pc1, pc2 = st.columns([1, 20])
                with pc1: st.write(f"{progress}%")
                with pc2: st.write(explanation)

        # 表格
        st.markdown('<div class="milestone-table">', unsafe_allow_html=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------------------------------------
        # 右側：延誤提醒（全局）—— 進度 100% 不顯示
        # -------------------------------------------------
        with col_right:
            st.markdown("### Delivery Delay Alert")
            delay_projects = []

            for _, row in df.iterrows():
                prog = 0
                if 'Parts_Arrival_Date' in df.columns and pd.notna(row['Parts_Arrival_Date']):
                    if row['Parts_Arrival_Date'].date() < datetime.now().date():
                        prog += 30
                if 'Installation_Complete_Date' in df.columns and pd.notna(row['Installation_Complete_Date']):
                    if row['Installation_Complete_Date'].date() < datetime.now().date():
                        prog += 40
                if 'Testing_Date' in df.columns and pd.notna(row['Testing_Date']):
                    if row['Testing_Date'].date() < datetime.now().date():
                        prog += 10
                if 'Cleaning' in df.columns and str(row.get('Cleaning', '')).strip().upper() == 'YES':
                    prog += 10
                if 'Delivery_Date' in df.columns and pd.notna(row['Delivery_Date']):
                    if row['Delivery_Date'].date() < datetime.now().date():
                        prog += 10
                prog = min(prog, 100)

                # 條件 1: Delivery > Lead_Time
                condition1 = ('Delivery_Date' in df.columns and 'Lead_Time' in df.columns and
                              pd.notna(row['Delivery_Date']) and pd.notna(row['Lead_Time']) and
                              row['Delivery_Date'] > row['Lead_Time'])

                # 條件 2: 進度未100% 且 今天 > Lead_Time
                condition2 = (prog < 100 and 'Lead_Time' in df.columns and pd.notna(row['Lead_Time']) and
                              datetime.now().date() > row['Lead_Time'].date())

                # 關鍵修正：必須 prog < 100 才顯示
                if (condition1 or condition2) and prog < 100:
                    if condition1:
                        days_late = (row['Delivery_Date'] - row['Lead_Time']).days
                        delay_msg = f"{days_late} days late"
                    else:
                        delay_msg = "Overdue"

                    delay_projects.append({
                        'name': row['Project_Name'],
                        'progress': prog,
                        'delay': delay_msg,
                        'explanation': exp_map.get(prog, f"{prog}% In Progress")
                    })

        if delay_projects:
            st.markdown(f'<div style="color:#721c24; font-weight:bold; margin-bottom:0.5rem;">{len(delay_projects)} delayed!</div>', unsafe_allow_html=True)
            for item in delay_projects:
                # 紅色漸層
                r = 255
                g = int(69 * (1 - item['progress']/100))
                b = 0
                color = f'rgb({r},{g},{b})'

                c1, c2, c3 = st.columns([2, 0.1, 8])
                with c1:
                    st.write(f"**{item['name']}**")
                with c2:
                    pass
                with c3:
                    st.markdown(
                        f'<div class="custom-progress"><div class="custom-progress-fill" style="width:{item["progress"]}%;background:{color};"></div></div>',
                        unsafe_allow_html=True
                    )
                    pc1, pc2 = st.columns([1, 18])
                    with pc1: st.write(f"{item['progress']}%")
                    with pc2:
                        st.markdown(f"<span style='color:red; font-weight:bold; font-size:13px;'>{item['delay']}</span>", unsafe_allow_html=True)
                        st.markdown(f"<span style='color:#555; font-size:12px;'>{item['explanation']}</span>", unsafe_allow_html=True)
        else:
            st.success("No delays!")

else:
    st.warning(f"No {selected_project_type} projects found in {selected_year} {selected_month}.")

# -------------------------------------------------
# 9. 全局提醒（Delivery > Lead_Time）
# -------------------------------------------------
if 'Delivery_Date' in df.columns and 'Lead_Time' in df.columns:
    df_remind = df[['Project_Name', 'Lead_Time', 'Delivery_Date', 'Remarks']].copy()
    df_remind['Delivery_Date'] = pd.to_datetime(df_remind['Delivery_Date'], errors='coerce')
    df_remind['Lead_Time'] = pd.to_datetime(df_remind['Lead_Time'], errors='coerce')

    reminder_df = df_remind[
        (df_remind['Delivery_Date'].isna()) |
        (df_remind['Delivery_Date'] > df_remind['Lead_Time'])
    ].copy()

    if not reminder_df.empty:
        reminder_df = reminder_df.dropna(how='all').reset_index(drop=True)
        for col in ['Lead_Time', 'Delivery_Date']:
            if col in reminder_df.columns:
                reminder_df[col] = pd.to_datetime(reminder_df[col], errors='coerce').dt.strftime('%Y-%m-%d')

        st.markdown(f"""
        <div class="reminder-section">
            <h3>Reminder: Delivery Date Issues</h3>
            <p>The following projects have Delivery Date either blank or later than Lead Time:</p>
            {reminder_df.to_html(index=False, escape=False)}
        </div>
        """, unsafe_allow_html=True)

# -------------------------------------------------
# 10. Footer
# -------------------------------------------------
st.markdown("---")
st.markdown("**YIP SHING Project Management System** | Real-time Project Status Monitoring")