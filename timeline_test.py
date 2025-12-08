import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

# -------------------------------------------------
# 1. 基本設定 + Checklist 持久化
# -------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

st.set_page_config(page_title="YIP SHING Project Status Dashboard", layout="wide", initial_sidebar_state="expanded")

# Checklist 狀態
CHECKLIST_FILE = "checklist_data.json"
if os.path.exists(CHECKLIST_FILE):
    with open(CHECKLIST_FILE, "r", encoding="utf-8") as f:
        saved_checklist = json.load(f)
else:
    saved_checklist = {}

def save_checklist():
    with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.checklist, f, ensure_ascii=False, indent=2)

# -------------------------------------------------
# 2. 完整 CSS（保持你原本的）
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
    .0 {
        background-color: #fff3cd;
        padding: 1rem;
        border: 1px solid #ffeeba;
        border-radius: 5px;
        color: #856404;
        max-height: 300px;
        overflow-y: auto;
        white-space: pre-wrap;
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
st.markdown('<div class="main-header"><div class="title">YIP SHING Project Status Dashboard</div></div>', unsafe_allow_html=True)
st.markdown("---")

# -------------------------------------------------
# 4. 左側側邊欄（原本的 Controls）
# -------------------------------------------------
with st.sidebar:
    st.title("Dashboard Controls")
    st.markdown("### Project Type Selection")
    project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
    selected_project_type = st.selectbox("Select Project Type:", project_types, index=0, help="Select the project type status to view")

    years = ["2024", "2025", "2026"]
    selected_year = st.selectbox("Select Year:", years, index=years.index("2025"), help="Select the year to view")

    month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
    selected_month = st.selectbox("Lead Time:", month_options, index=0, help="Select the lead time to view or '--' for all lead times")

# -------------------------------------------------
# 5. 讀取 CSV（保持你原本的）
# -------------------------------------------------
def load_data():
    csv_file = "projects.csv"
    if not os.path.exists(csv_file):
        st.error(f"Cannot find `{csv_file}`! Please upload it to the app folder.")
        return None
    try:
        df = pd.read_csv(csv_file, encoding='utf-8', sep=',')
        required = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        if not all(col in df.columns for col in required):
            missing = [c for c in required if c not in df.columns]
            st.error(f"Missing required columns: {', '.join(missing)}")
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
# 6. 篩選
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
# 7. 統計（改用 Real_Count 總和）
# -------------------------------------------------
if 'Real_Count' in filtered_df.columns:
    filtered_df['Real_Count'] = pd.to_numeric(filtered_df['Real_Count'], errors='coerce').fillna(0).astype(int)
else:
    filtered_df['Real_Count'] = 0

project_counts = filtered_df.groupby('Project_Type')['Real_Count'].sum().to_dict()
total_real_count = int(filtered_df['Real_Count'].sum())

month_str = selected_month if selected_month != "--" else "All Months"
st.markdown(f"### {selected_project_type} - {selected_year} {month_str} Project Count (by Real_Count)")

col1, *rest = st.columns([1] + [1] * len(project_counts))
with col1:
    st.write(f"**Total: {total_real_count}**")
for i, (pt, cnt) in enumerate(project_counts.items()):
    with rest[i]:
        st.write(f"**{pt}: {int(cnt)}**")

# -------------------------------------------------
# 8. 主畫面：左側正常 + 右側延誤（完全保留你原本的排版）
# -------------------------------------------------
if total_real_count > 0:
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
        if 'Cleaning' in df.columns and str(row.get('Cleaning', '')).strip().upper() == 'YES':
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
                'remarks': row.get('Remarks', ''),
                'explanation': {0: "Not Start Yet", 30: "Parts Arrived", 70: "Installation Completed",
                                80: "Testing Completed", 90: "Cleaning Completed", 100: "Project Completed"}.get(prog,
                                                                                                                 f"{prog}% In Progress")
            })

    # 建立左側 + 右側進度條（平排）—— 完全保留你原本的排版
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
                if 'Cleaning' in filtered_df.columns and str(row.get('Cleaning', '')).strip().upper() == 'YES':
                    progress += 10
                if 'Delivery_Date' in filtered_df.columns and pd.notna(row['Delivery_Date']):
                    if row['Delivery_Date'].date() < current_date.date():
                        progress += 10
                progress = min(progress, 100)

                # 顏色
                if progress == 0:
                    color = '#e0e0e0'
                elif progress < 30:
                    color = f'rgb({int(224 + (255 - 224) * (progress / 30))}, {int(224 + (69 - 224) * (progress / 30))}, {int(224 + (0 - 224) * (progress / 30))})'
                elif progress < 70:
                    color = f'rgb(255, {int(69 + (255 - 69) * ((progress - 30) / 40))}, 0)'
                elif progress < 80:
                    color = f'rgb({int(255 + (154 - 255) * ((progress - 70) / 10))}, 255, {int(0 + (50 - 0) * ((progress - 70) / 10))})'
                elif progress < 90:
                    color = f'rgb({int(154 + (0 - 154) * ((progress - 80) / 10))}, {int(205 + (255 - 205) * ((progress - 80) / 10))}, {int(50 + (0 - 50) * ((progress - 80) / 10))})'
                elif progress < 100:
                    color = f'rgb(0, {int(255 + (0 - 255) * ((progress - 90) / 10))}, {int(0 + (255 - 0) * ((progress - 90) / 10))})'
                else:
                    color = '#0000ff'

                exp_map = {0: "Not Start Yet", 30: "Parts Arrived", 70: "Installation Completed",
                           80: "Testing Completed", 90: "Cleaning Completed", 100: "Project Completed"}
                explanation = exp_map.get(progress, f"{progress}% In Progress")

                desc = str(row.get('Description', '')).upper()
                k38 = 'KTA38' in desc
                k50 = 'KTA50' in desc
                K3850 = 'KTA38 & KTA50' in desc

                c1, c2, c3, c4 = st.columns([3, 2, 3, 10])

                # ── c1：Project_Name (上) + Brand (下) ──
                with c1:
                    project_name = row['Project_Name']
                    brand_raw = row.get('Brand', '')
                    brand = str(brand_raw).strip() if brand_raw is not None else ''

                    if brand and brand.lower() != 'nan':
                        html = f"""
                        <div style="line-height: 1.2;">
                            <div style="font-weight: bold; margin-bottom: 2px;">{project_name}</div>
                            <div style="font-size: 0.8rem; color: #666;">{brand}</div>
                        </div>
                        """
                        st.markdown(html, unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{project_name}**")

                # ── c2：Qty ──
                with c2:
                    qty = row.get('Qty', '')
                    if qty:
                        st.write(qty)

                # ── c3：圖示 ──
                with c3:
                    if k38:
                        st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
                    if K3850:
                        st.image("https://i.imgur.com/S2kIoCM.png", width=30)
                    elif k50:
                        st.image("https://i.imgur.com/oJNLgDG.png", width=30)

                with c4:
                    tooltip = str(row.get('Progress_Tooltip', '')).strip()
                    if tooltip and tooltip.lower() != 'nan':
                        # 1. 先寫 style（獨立出來！千萬別放進 f-string）
                        st.markdown("""
                        <style>
                        .tooltip-container { position: relative; display: inline-block; }
                        .tooltip-box {
                            position: absolute; bottom: 32px; left: 50%; transform: translateX(-50%);
                            background: #1e1e1e; color: white; padding: 16px 24px; border-radius: 12px;
                            font-size: 16px; line-height: 1.7; white-space: pre-wrap; text-align: left;
                            min-width: 200px; max-width: 500px; box-shadow: 0 8px 25px rgba(0,0,0,0.5);
                            opacity: 0; visibility: hidden; transition: all 0.3s ease; z-index: 999;
                            pointer-events: none;
                        }
                        .tooltip-arrow {
                            position: absolute; top: 100%; left: 50%; margin-left: -8px;
                            border: 8px solid transparent; border-top-color: #1e1e1e;
                        }
                        .tooltip-container:hover .tooltip-box {
                            opacity: 1 !important; visibility: visible !important;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                        # 2. 再寫真正的 HTML（不再包含 <style>）
                        st.markdown(f"""
                        <div class="tooltip-container" style="width:150px;">
                            <div class="custom-progress">
                                <div class="custom-progress-fill" style="width:{progress}%;background:{color};"></div>
                            </div>
                            <div class="tooltip-box">
                                {tooltip.replace(chr(10), '<br>')}
                                <div class="tooltip-arrow"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div class="custom-progress"><div class="custom-progress-fill" style="width:{progress}%;background:{color};"></div></div>',
                            unsafe_allow_html=True
                        )

                    pc1, pc2 = st.columns([1, 5])
                    with pc1: st.write(f"**{progress}%**")
                    with pc2: st.write(explanation)
        # 右側：延誤專案
        if i == 0 and delay_projects:
            with col_right:
                st.markdown("### Delay Projects")

        if i < len(delay_projects):
            item = delay_projects[i]
            with col_right:
                r = 255
                g = int(69 * (1 - item['progress'] / 100))
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
                    with pc2: st.write(item['explanation'])
                with c3:
                    st.markdown(
                        f"<div style='font-size:12px; color:#d00;'><strong>{item['remarks']}</strong></div>",
                        unsafe_allow_html=True)

    # 表格（左側下方）
    st.markdown('<div class="milestone-table">', unsafe_allow_html=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning(f"No {selected_project_type} projects found in {selected_year} {selected_month}.")


# -------------------------------------------------
# 永久記住 Checklist
# -------------------------------------------------
with st.sidebar:
    st.title("Checklist Panel")

    # 永久儲存檔案
    CHECKLIST_FILE = "yipshing_checklist.json"
    if os.path.exists(CHECKLIST_FILE):
        with open(CHECKLIST_FILE, "r", encoding="utf-8") as f:
            saved_checklist = json.load(f)
    else:
        saved_checklist = {}

    for _, row in filtered_df.iterrows():
        project_name = row['Project_Name']

        # 從 JSON 讀取（沒有就用 CSV 原始值）
        data = saved_checklist.get(project_name, {
            "purchase": [x.strip() for x in str(row.get('Order_List', '')).split(',') if x.strip()],
            "done_p":   [],
            "drawing":  [x.strip() for x in str(row.get('Submit_List', '')).split(',') if x.strip()],
            "done_d":   []
        })

        # === 永遠正確版：用已儲存的資料判斷紅色 ❗️（永不閃爍、永不消失！）===
        # 從已永久儲存的資料判斷（最準確、最穩定！）
        current_data = saved_checklist.get(project_name, {
            "purchase": [x.strip() for x in str(row.get('Order_List', '')).split(',') if x.strip()],
            "done_p":   [],
            "drawing":  [x.strip() for x in str(row.get('Submit_List', '')).split(',') if x.strip()],
            "done_d":   []
        })

        has_unchecked = False
        # 檢查 Purchase 是否有未完成
        for item in current_data["purchase"]:
            if item and item not in current_data["done_p"]:
                has_unchecked = True
                break
        # 檢查 Drawing 是否有未完成
        if not has_unchecked:
            for item in current_data["drawing"]:
                if item and item not in current_data["done_d"]:
                    has_unchecked = True
                    break

        # 用 session_state 控制展開
        if f"open_{project_name}" not in st.session_state:
            st.session_state[f"open_{project_name}"] = False

        # 標題列
        col_title, col_btn = st.columns([8, 1])
        with col_title:
            if has_unchecked:
                st.markdown(f"**<span style='color:red'>{project_name} ❗️</span>**", unsafe_allow_html=True)
            else:
                st.markdown(f"**{project_name}**", unsafe_allow_html=True)
        with col_btn:
            if st.button("↓" if st.session_state[f"open_{project_name}"] else "→",
                         key=f"toggle_{project_name}", help="展開/收合"):
                st.session_state[f"open_{project_name}"] = not st.session_state[f"open_{project_name}"]
                st.rerun()

        # 內容區（展開才顯示）
        if st.session_state[f"open_{project_name}"]:
            with st.container():
                st.markdown("### Purchase List     Drawings Submission")

                new_purchase = []
                new_done_p   = set()
                new_drawing  = []
                new_done_d   = set()

                max_rows = max(len(data["purchase"]), len(data["drawing"]), 6)

                for i in range(max_rows):
                    col1, col2 = st.columns(2)

                    # Purchase List
                    with col1:
                        text = data["purchase"][i] if i < len(data["purchase"]) else ""
                        checked = text in data["done_p"]
                        c1, c2 = st.columns([1, 6])
                        with c1:
                            chk = st.checkbox("", value=checked, key=f"p_{project_name}_{i}")
                        with c2:
                            txt = st.text_input("", value=text, key=f"pt_{project_name}_{i}", label_visibility="collapsed")
                        if txt.strip():
                            new_purchase.append(txt.strip())
                            if chk:
                                new_done_p.add(txt.strip())

                    # Drawings Submission
                    with col2:
                        text = data["drawing"][i] if i < len(data["drawing"]) else ""
                        checked = text in data["done_d"]
                        c1, c2 = st.columns([1, 6])
                        with c1:
                            chk = st.checkbox("", value=checked, key=f"d_{project_name}_{i}")
                        with c2:
                            txt = st.text_input("", value=text, key=f"dt_{project_name}_{i}", label_visibility="collapsed")
                        if txt.strip():
                            new_drawing.append(txt.strip())
                            if chk:
                                new_done_d.add(txt.strip())

                # SAVE 按鈕
                if st.button("SAVE", key=f"save_{project_name}", use_container_width=True, type="primary"):
                    saved_checklist[project_name] = {
                        "purchase": new_purchase,
                        "done_p": list(new_done_p),
                        "drawing": new_drawing,
                        "done_d": list(new_done_d)
                    }
                    with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
                        json.dump(saved_checklist, f, ensure_ascii=False, indent=2)
                    st.success(f"{project_name} 已永久儲存！")
                    st.rerun()
# -------------------------------------------------
# Memo Pad & Footer
# -------------------------------------------------
st.markdown("---")
with st.expander("Memo Pad", expanded=True):
    memo_file = "memo.txt"

    def load_memo():
        if os.path.exists(memo_file):
            with open(memo_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def save_memo(content):
        with open(memo_file, "w", encoding="utf-8") as f:
            f.write(content)

    current_memo = load_memo()
    if 'memo_content' not in st.session_state:
        st.session_state.memo_content = current_memo

    st.markdown("**Edit your memo here:**")
    new_memo = st.text_area(
        label="Memo Input",
        value=st.session_state.memo_content,
        height=250,
        placeholder="Type your notes, reminders, or to-do list...",
        key="memo_input"
    )
    st.session_state.memo_content = new_memo

    col_save, col_clear = st.columns([1, 1])
    with col_save:
        if st.button("Save Memo", use_container_width=True, key="save_memo"):
            save_memo(new_memo)
            st.session_state.memo_content = new_memo
            st.success("Memo saved to `memo.txt`!")
            st.rerun()
    with col_clear:
        if st.button("Clear Memo", use_container_width=True, key="clear_memo"):
            save_memo("")
            st.session_state.memo_content = ""
            st.warning("Memo cleared!")
            st.rerun()

    st.markdown("### Current Memo")
    if st.session_state.memo_content.strip():
        st.markdown(
            f'<div class="reminder-section">{st.session_state.memo_content.replace("\n", "<br>")}</div>',
            unsafe_allow_html=True
        )
    else:
        st.info("No memo yet. Start writing above!")

st.markdown("---")
st.markdown("**YIP SHING Project Management System** | Real-time Project Status Monitoring")


