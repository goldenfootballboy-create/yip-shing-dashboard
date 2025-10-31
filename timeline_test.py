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
# 9. 右側可收合 Weekly Remarks 面板（安全版）
# -------------------------------------------------
if df is not None:  # 必須加這層保護！
    st.markdown("---")

    # 右側浮動可收合面板 CSS
    st.markdown("""
    <style>
        .right-panel {
            position: fixed;
            right: 0;
            top: 0;
            height: 100%;
            width: 400px;
            background-color: white;
            box-shadow: -5px 0 15px rgba(0,0,0,0.1);
            z-index: 999;
            padding: 1rem;
            overflow-y: auto;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        }
        .right-panel.open {
            transform: translateX(0);
        }
        .toggle-btn {
            position: fixed;
            right: 10px;
            top: 50%;
            transform: translateY(-50%) rotate(180deg);
            background: #1fb429;
            color: white;
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            font-size: 20px;
            cursor: pointer;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            transition: right 0.3s ease, transform 0.3s ease;
        }
        .toggle-btn.open {
            right: 390px;
            transform: translateY(-50%) rotate(0deg);
        }
    </style>
    """, unsafe_allow_html=True)

    # 檢查是否有 Weekly_Remarks 欄位
    has_weekly_remarks = 'Weekly_Remarks' in df.columns
    remarks_data = []

    if has_weekly_remarks:
        for _, row in df.iterrows():
            remark = row.get('Weekly_Remarks', '')
            if pd.notna(remark) and str(remark).strip():
                remarks_data.append({
                    'Project': row['Project_Name'],
                    'Remark': str(remark).strip()
                })

    # 使用 session_state 控制面板開關
    if 'right_panel_open' not in st.session_state:
        st.session_state.right_panel_open = False

    # 切換按鈕（放在畫面中間偏右）
    if st.button("→", key="toggle_right_panel", help="Toggle Weekly Remarks Panel"):
        st.session_state.right_panel_open = not st.session_state.right_panel_open

    # 建立面板 HTML
    panel_class = "right-panel open" if st.session_state.right_panel_open else "right-panel"
    btn_class = "toggle-btn open" if st.session_state.right_panel_open else "toggle-btn"
    arrow = "←" if st.session_state.right_panel_open else "→"

    panel_html = f"""
    <div id="rightPanel" class="{panel_class}">
        <h3 style="color:#1fb429; margin-top:0; border-bottom:2px solid #1fb429; padding-bottom:8px;">Weekly Remarks</h3>
        <button onclick="togglePanel()" style="position:absolute; top:10px; right:10px; background:none; border:none; font-size:24px; cursor:pointer; color:#666;">×</button>
    """

    if remarks_data:
        panel_html += '<table style="width:100%; font-size:14px; border-collapse:collapse; margin-top:10px;">'
        panel_html += '<tr><th style="text-align:left; border-bottom:2px solid #ddd; padding:8px; background:#f8f9fa;">Project</th><th style="text-align:left; border-bottom:2px solid #ddd; padding:8px; background:#f8f9fa;">Remark</th></tr>'
        for item in remarks_data:
            safe_remark = item["Remark"].replace('"', '&quot;').replace("'", '&#39;')
            panel_html += f'<tr><td style="padding:8px; border-bottom:1px solid #eee; vertical-align:top;"><strong>{item["Project"]}</strong></td><td style="padding:8px; border-bottom:1px solid #eee; white-space: pre-wrap;">{safe_remark}</td></tr>'
        panel_html += '</table>'
    else:
        panel_html += "<p style='color:#666; font-style:italic; margin-top:10px;'>No weekly remarks available.</p>"

    panel_html += """
    </div>
    <button id="toggleBtn" class="{btn_class}" onclick="togglePanel()">{arrow}</button>

    <script>
        function togglePanel() {
            const panel = document.getElementById('rightPanel');
            const btn = document.getElementById('toggleBtn');
            panel.classList.toggle('open');
            btn.classList.toggle('open');
            btn.innerHTML = panel.classList.contains('open') ? '←' : '→';
        }
    </script>
    """.format(panel_class=panel_class, btn_class=btn_class, arrow=arrow)

    st.markdown(panel_html, unsafe_allow_html=True)

else:
    # df is None → 什麼都不顯示
    pass

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
# 8. 主畫面：左側正常 + 右側延誤（進度條平排）
# -------------------------------------------------
if total_projects > 0:
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

    # 準備延誤專案（全局）
    delay_projects = []
    for _, row in df.iterrows():
        prog = 0
        if 'Parts_Arrival_Date' in df.columns and pd.notna(row['Parts_Arrival_Date']):
            if row['Parts_Arrival_Date'].date() < current_date.date():
                prog += 30
        if 'Installation_Complete_Date' in df.columns and pd.notna(row['Installation_Complete_Date']):
            if row['Installation_Complete_Date'].date() < current_date.date():
                prog += 40
        if 'Testing_Date' in df.columns and pd.notna(row['Testing_Date']):
            if row['Testing_Date'].date() < current_date.date():
                prog += 10
        if 'Cleaning' in df.columns and str(row.get('Cleaning','')).strip().upper() == 'YES':
            prog += 10
        if 'Delivery_Date' in df.columns and pd.notna(row['Delivery_Date']):
            if row['Delivery_Date'].date() < current_date.date():
                prog += 10
        prog = min(prog, 100)

        condition1 = ('Delivery_Date' in df.columns and 'Lead_Time' in df.columns and
                     pd.notna(row['Delivery_Date']) and pd.notna(row['Lead_Time']) and
                     row['Delivery_Date'] > row['Lead_Time'])

        condition2 = (prog < 100 and 'Lead_Time' in df.columns and pd.notna(row['Lead_Time']) and
                     current_date.date() > row['Lead_Time'].date())

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
                'remarks': row['Remarks'],
                'explanation': {0:"Not Start",30:"Parts Arrived",70:"Installation Completed",
                               80:"Testing Completed",90:"Cleaning Completed",100:"Project Completed"}.get(prog, f"{prog}% In Progress")
            })


    # 建立左側 + 右側進度條（平排）
    left_rows = filtered_df.to_dict('records')
    right_rows = delay_projects

    max_rows = max(len(left_rows), len(right_rows)) if right_rows else len(left_rows)

    for i in range(max_rows):
        col_left, col_right = st.columns([5, 5])

        # 左側：正常專案
        if i < len(left_rows):
            row = left_rows[i]
            with col_left:
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

                exp_map = {0:"Not Start",30:"Parts Arrived",70:"Installation Completed",
                           80:"Testing Completed",90:"Cleaning Completed",100:"Project Completed"}
                explanation = exp_map.get(progress, f"{progress}% In Progress")

                desc = str(row.get('Description','')).upper()
                k38 = 'KTA38' in desc
                k50 = 'KTA50' in desc

                c1, c2, c3 = st.columns([3, 2, 8])
                with c1: st.write(row['Project_Name'])
                with c2:
                    if k38: st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
                    elif k50: st.image("https://i.imgur.com/oJNLgDG.png", width=30)
                with c3:
                    st.markdown(f'<div class="custom-progress"><div class="custom-progress-fill" style="width:{progress}%;background:{color};"></div></div>', unsafe_allow_html=True)
                    pc1, pc2 = st.columns([1, 5])
                    with pc1: st.write(f"{progress}%")
                    with pc2: st.write(explanation)

        # 右側：延誤專案
        if i == 0 and delay_projects:
            with col_right:
                st.markdown("### Delay Projects")

        if i < len(delay_projects):
            item = delay_projects[i]
            with col_right:
                r = 255
                g = int(69 * (1 - item['progress']/100))
                b = 0
                color = f'rgb({r},{g},{b})'

                c1, c2, c3 = st.columns([4, 8, 10])
                with c1:
                    st.write(f"**{item['name']}**")
                with c2:
                    st.markdown(
                        f'<div class="custom-progress"><div class="custom-progress-fill" style="width:{item["progress"]}%;background:{color};"></div></div>',
                        unsafe_allow_html=True
                    )
                    pc1, pc2 = st.columns([1, 5])
                    with pc1: st.write(f"{item['progress']}%")
                    with pc2: st.write(explanation)
                    with c3: st.markdown(f"<div style='font-size:12px; color:#d00;'><strong>{item['remarks']}</strong></div>", unsafe_allow_html=True)


    # 表格（左側下方）
    st.markdown('<div class="milestone-table">', unsafe_allow_html=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning(f"No {selected_project_type} projects found in {selected_year} {selected_month}.")


# -------------------------------------------------
# 10. Footer
# -------------------------------------------------
st.markdown("---")
st.markdown("**YIP SHING Project Management System** | Real-time Project Status Monitoring")
