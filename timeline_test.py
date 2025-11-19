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
CHECKLIST_FILE = "checklist.json"
if os.path.exists(CHECKLIST_FILE):
    with open(CHECKLIST_FILE, "r", encoding="utf-8") as f:
        st.session_state.checklist = json.load(f)
else:
    st.session_state.checklist = {}


def save_checklist():
    with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.checklist, f, ensure_ascii=False, indent=2)


# -------------------------------------------------
# 2. CSS
# -------------------------------------------------
st.markdown("""
<style>
    .main-header {font-size: 3rem; color: #1fb429; margin-bottom: 1rem; margin-top: -4rem; font-weight: bold; text-align: center;}
    .custom-progress {height: 20px; background-color: #e0e0e0; border-radius: 10px; overflow: hidden; width: 150px;}
    .custom-progress-fill {height: 100%; transition: width 0.3s ease; border-radius: 10px;}

    /* 右側側邊欄標題更醒目 */
    section[data-testid="stSidebar"] h1 {
        color: #1fb429 !important;
        font-size: 1.6rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">YIP SHING Project Status Dashboard</div>', unsafe_allow_html=True)
st.markdown("---")

# -------------------------------------------------
# 3. 左側側邊欄（原本的 Controls）
# -------------------------------------------------
with st.sidebar:
    st.title("Dashboard Controls")
    project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
    selected_project_type = st.selectbox("Select Project Type:", project_types, index=0)

    years = ["2024", "2025", "2026"]
    selected_year = st.selectbox("Select Year:", years, index=years.index("2025"))

    month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月",
                     "十二月"]
    selected_month = st.selectbox("Lead Time:", month_options, index=0)


# -------------------------------------------------
# 4. 讀取 CSV + 篩選 + 統計
# -------------------------------------------------
def load_data():
    if not os.path.exists("projects.csv"):
        st.error("Cannot find `projects.csv`!")
        return None
    try:
        df = pd.read_csv("projects.csv", encoding='utf-8')
        required = ['Project_Type', 'Project_Name', 'Year', 'Lead_Time']
        if not all(col in df.columns for col in required):
            st.error(f"Missing columns: {', '.join([c for c in required if c not in df.columns])}")
            return None
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        date_cols = ['Lead_Time', 'Parts_Arrival_Date', 'Installation_Complete_Date', 'Testing_Date', 'Delivery_Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None


df = load_data()
if df is None:
    st.stop()

filtered_df = df[df['Year'] == int(selected_year)].copy()
if selected_project_type != "All":
    filtered_df = filtered_df[filtered_df['Project_Type'] == selected_project_type]
if selected_month != "--" and 'Lead_Time' in filtered_df.columns:
    month_idx = month_options.index(selected_month)
    if month_idx > 0:
        filtered_df = filtered_df[filtered_df['Lead_Time'].dt.month == month_idx]

filtered_df['Real_Count'] = pd.to_numeric(filtered_df.get('Real_Count', 0), errors='coerce').fillna(0).astype(int)
total_real_count = int(filtered_df['Real_Count'].sum())
project_counts = filtered_df.groupby('Project_Type')['Real_Count'].sum().to_dict()

month_str = selected_month if selected_month != "--" else "All Months"
st.markdown(f"### {selected_project_type} - {selected_year} {month_str} Project Count (by Real_Count)")
col1, *rest = st.columns([1] + [1] * len(project_counts))
with col1: st.write(f"**Total: {total_real_count}**")
for i, (pt, cnt) in enumerate(project_counts.items()):
    with rest[i]: st.write(f"**{pt}: {int(cnt)}**")

# -------------------------------------------------
# 5. 主畫面 + 右側側邊欄 Checklist（左右收合）
# -------------------------------------------------
if total_real_count > 0:
    # 左邊主內容
    main_container = st.container()
    with main_container:
        current_date = datetime.now()
        left_rows = filtered_df.to_dict('records')

        # 延誤專案計算
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

            if prog < 100 and 'Lead_Time' in df.columns and pd.notna(row['Lead_Time']) and current_date.date() > row[
                'Lead_Time'].date():
                delay_projects.append({
                    'name': row['Project_Name'],
                    'progress': prog,
                    'remarks': row.get('Remarks', ''),
                    'explanation': {0: "Not Start Yet", 30: "Parts Arrived", 70: "Installation Completed",
                                    80: "Testing Completed", 90: "Cleaning Completed", 100: "Project Completed"}.get(
                        prog, f"{prog}% In Progress")
                })

        # 右邊內容預先準備
        right_contents = [""] * len(left_rows)
        if delay_projects:
            right_contents[0] = "### Delay Projects"
            for idx, item in enumerate(delay_projects):
                if idx < len(right_contents):
                    color = f'rgb(255, {int(69 * (1 - item["progress"] / 100))}, 0)'
                    right_contents[
                        idx] = f"**{item['name']}**<br><div class='custom-progress'><div class='custom-progress-fill' style='width:{item['progress']}%;background:{color};'></div></div><br>{item['progress']}% - {item['explanation']}<br><small style='color:#d00'>{item['remarks']}</small>"

        for i, row in enumerate(left_rows):
            col_left, col_right = st.columns([5, 5])

            with col_left:
                # 計算 progress
                progress = 0
                if 'Parts_Arrival_Date' in row and pd.notna(row['Parts_Arrival_Date']):
                    if row['Parts_Arrival_Date'].date() < current_date.date():
                        progress += 30
                if 'Installation_Complete_Date' in row and pd.notna(row['Installation_Complete_Date']):
                    if row['Installation_Complete_Date'].date() < current_date.date():
                        progress += 40
                if 'Testing_Date' in row and pd.notna(row['Testing_Date']):
                    if row['Testing_Date'].date() < current_date.date():
                        progress += 10
                if str(row.get('Cleaning', '')).strip().upper() == 'YES':
                    progress += 10
                if 'Delivery_Date' in row and pd.notna(row['Delivery_Date']):
                    if row['Delivery_Date'].date() < current_date.date():
                        progress += 10
                progress = min(progress, 100)

                color = '#0000ff' if progress == 100 else '#ff4500'
                explanation = {0: "Not Start Yet", 30: "Parts Arrived", 70: "Installation Completed",
                               80: "Testing Completed", 90: "Cleaning Completed", 100: "Project Completed"}.get(
                    progress, f"{progress}% In Progress")

                # 主顯示
                c1, c2, c3, c4 = st.columns([3, 2, 3, 10])
                with c1:
                    project_name = row['Project_Name']
                    brand = str(row.get('Brand', '')).strip()
                    if brand and brand.lower() != 'nan':
                        html = f"<div style='line-height:1.2;'><div style='font-weight:bold;margin-bottom:2px;'>{project_name}</div><div style='font-size:0.8rem;color:#666;'>{brand}</div></div>"
                        st.markdown(html, unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{project_name}**")

                with c2:
                    qty = row.get('Qty', '')
                    if qty:
                        st.write(qty)

                with c3:
                    desc = str(row.get('Description', '')).upper()
                    if 'KTA38' in desc and 'KTA50' in desc:
                        st.image("https://i.imgur.com/S2kIoCM.png", width=30)
                    elif 'KTA38' in desc:
                        st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
                    elif 'KTA50' in desc:
                        st.image("https://i.imgur.com/oJNLgDG.png", width=30)

                with c4:
                    st.markdown(
                        f'<div class="custom-progress"><div class="custom-progress-fill" style="width:{progress}%;background:{color};"></div></div>',
                        unsafe_allow_html=True)
                    pc1, pc2 = st.columns([1, 5])
                    with pc1: st.write(f"**{progress}%**")
                    with pc2: st.write(explanation)

            # 右邊顯示 Delay Projects
            if right_contents[i]:
                with col_right:
                    st.markdown(right_contents[i], unsafe_allow_html=True)

    # -------------------------------------------------
    # 右側側邊欄 Checklist（左右收合）
    # -------------------------------------------------
    with st.sidebar:
        st.title("Checklist Panel")
        if st.button("保存所有狀態", use_container_width=True):
            save_checklist()
            st.success("已保存！")

        for row in filtered_df.itertuples(index=False):
            with st.expander(f"{row.Project_Name}", expanded=False):
                order_items = [x.strip() for x in str(getattr(row, 'Order_List', '')).split(',') if x.strip()]
                submit_items = [x.strip() for x in str(getattr(row, 'Submit_List', '')).split(',') if x.strip()]

                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("需要訂購")
                    for item in order_items:
                        key = f"order_{row.Project_Name}_{item}"
                        checked = st.checkbox(item, value=st.session_state.checklist.get(key, False), key=key)
                        st.session_state.checklist[key] = checked

                with col_b:
                    st.subheader("需要提交")
                    for item in submit_items:
                        key = f"submit_{row.Project_Name}_{item}"
                        checked = st.checkbox(item, value=st.session_state.checklist.get(key, False), key=key)
                        st.session_state.checklist[key] = checked

                total = len(order_items) + len(submit_items)
                completed = sum(st.session_state.checklist.get(k, False) for k in st.session_state.checklist if
                                k.startswith(f"order_{row.Project_Name}_") or k.startswith(
                                    f"submit_{row.Project_Name}_"))
                st.progress(completed / total if total else 0)
                st.write(f"**完成度：{completed}/{total}**")

else:
    st.warning("No projects found.")

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