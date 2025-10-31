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
# 2. CSS
# -------------------------------------------------
st.markdown("""
<style>
    .main-header {font-size:3rem;color:#1fb429;margin-bottom:1rem;margin-top:-4rem;font-weight:bold;text-align:center;}
    .custom-progress {height:20px;background:#e0e0e0;border-radius:10px;overflow:hidden;width:150px;}
    .custom-progress-fill {height:100%;transition:width .3s;border-radius:10px;}
    .reminder-section {background:#fff3cd;padding:1rem;border:1px solid #ffeeba;border-radius:5px;color:#856404;max-height:200px;overflow-y:auto;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">YIP SHING Project Status Dashboard</div>', unsafe_allow_html=True)
st.markdown("---")

# -------------------------------------------------
# 3. 側邊欄
# -------------------------------------------------
st.sidebar.title("Dashboard Controls")
project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
selected_project_type = st.sidebar.selectbox("Select Project Type:", project_types, index=0)

years = ["2024", "2025", "2026"]
selected_year = st.sidebar.selectbox("Select Year:", years, index=years.index("2025"))

month_options = ["--", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
selected_month = st.sidebar.selectbox("Lead Time:", month_options, index=0)

# -------------------------------------------------
# 4. 讀取 CSV（支援 yyyy-mm-dd）
# -------------------------------------------------
def load_data():
    csv_file = "projects.csv"
    if not os.path.exists(csv_file):
        st.error(f"找不到 {csv_file}！請放在腳本同目錄")
        return None
    try:
        df = pd.read_csv(csv_file, encoding="utf-8")
        # 必要欄位
        required = ["Project_Type", "Project_Name", "Year", "Lead_Time"]
        if not all(c in df.columns for c in required):
            st.error(f"缺少必要欄位：{', '.join([c for c in required if c not in df.columns])}")
            return None

        # Year 轉數字
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

        # 日期欄位（自動解析 ISO 格式）
        date_cols = ["Lead_Time", "Parts_Arrival_Date", "Installation_Complete_Date",
                     "Testing_Date", "Delivery_Date"]
        for c in date_cols:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")   # 支援 2025-11-07
        return df
    except Exception as e:
        st.error(f"讀檔錯誤：{e}")
        return None

df = load_data()
if df is None:
    st.stop()

# -------------------------------------------------
# 5. 篩選
# -------------------------------------------------
filtered = df[df["Year"] == int(selected_year)].copy()

if selected_project_type != "All":
    filtered = filtered[filtered["Project_Type"] == selected_project_type]

if selected_month != "--" and "Lead_Time" in filtered.columns:
    if pd.api.types.is_datetime64_any_dtype(filtered["Lead_Time"]):
        m_idx = month_options.index(selected_month)
        if m_idx:
            filtered = filtered[filtered["Lead_Time"].dt.month == m_idx]

# -------------------------------------------------
# 6. 統計
# -------------------------------------------------
total = len(filtered)
counts = filtered["Project_Type"].value_counts().to_dict()
month_str = selected_month if selected_month != "--" else "All Months"
st.markdown(f"### {selected_project_type} - {selected_year} {month_str} Project Count")
c1, *rest = st.columns([1] + [1]*len(counts))
with c1: st.write(f"**Total:** {total}")
for i, (pt, cnt) in enumerate(counts.items()):
    with rest[i]: st.write(f"**{pt}:** {cnt}")

# -------------------------------------------------
# 7. 主畫面
# -------------------------------------------------
if total:
    st.markdown("### Project Details")

    # 顯示用的 DataFrame（字串格式）
    disp_cols = ["Project_Name", "Description", "Parts_Arrival_Date", "Installation_Complete_Date",
                 "Testing_Date", "Cleaning", "Delivery_Date", "Remarks"]
    avail = [c for c in disp_cols if c in filtered.columns]
    disp_df = filtered[avail].copy()
    for c in avail:
        if c in ["Parts_Arrival_Date", "Installation_Complete_Date",
                 "Testing_Date", "Delivery_Date"]:
            disp_df[c] = pd.to_datetime(disp_df[c], errors="coerce").dt.strftime("%Y-%m-%d")

    now = datetime.now()

    for _, row in filtered.iterrows():
        prog = 0

        # Parts 30%
        if "Parts_Arrival_Date" in filtered.columns and pd.notna(row["Parts_Arrival_Date"]):
            if row["Parts_Arrival_Date"].date() < now.date():
                prog += 30

        # Installation 40%
        if "Installation_Complete_Date" in filtered.columns and pd.notna(row["Installation_Complete_Date"]):
            if row["Installation_Complete_Date"].date() < now.date():
                prog += 40

        # Testing 10%
        if "Testing_Date" in filtered.columns and pd.notna(row["Testing_Date"]):
            if row["Testing_Date"].date() < now.date():
                prog += 10

        # Cleaning 10%
        if "Cleaning" in filtered.columns and str(row.get("Cleaning","")).strip().upper() == "YES":
            prog += 10

        # Delivery 10%（可選）
        if "Delivery_Date" in filtered.columns and pd.notna(row["Delivery_Date"]):
            if row["Delivery_Date"].date() < now.date():
                prog += 10

        prog = min(prog, 100)

        # 顏色漸層
        if prog == 0: color = "#e0e0e0"
        elif prog < 30: color = f"rgb({int(224+(255-224)*(prog/30))}, {int(224+(69-224)*(prog/30))}, {int(224+(0-224)*(prog/30))})"
        elif prog < 70: color = f"rgb(255, {int(69+(255-69)*((prog-30)/40))}, 0)"
        elif prog < 80: color = f"rgb({int(255+(154-255)*((prog-70)/10))}, 255, {int(0+(50-0)*((prog-70)/10))})"
        elif prog < 90: color = f"rgb({int(154+(0-154)*((prog-80)/10))}, {int(205+(255-205)*((prog-80)/10))}, {int(50+(0-50)*((prog-80)/10))})"
        elif prog < 100: color = f"rgb(0, {int(255+(0-255)*((prog-90)/10))}, {int(0+(255-0)*((prog-90)/10))})"
        else: color = "#0000ff"

        # 說明文字
        txt = {0:"Not Start",30:"Parts Arrived",70:"Installation Completed",
               80:"Testing Completed",90:"Cleaning Completed",100:"Project Completed"}
        explanation = txt.get(prog, f"{prog}% In Progress")

        # KTA 圖示
        desc = str(row.get("Description","")).upper()
        k38 = "KTA38" in desc
        k50 = "KTA50" in desc

        # 進度條
        c1, c2, c3 = st.columns([1, 0.2, 6])
        with c1: st.write(row["Project_Name"])
        with c2:
            if k38: st.image("https://i.imgur.com/koGZmUz.jpeg", width=30)
            elif k50: st.image("https://i.imgur.com/3Cb2Nqj.png", width=30)
        with c3:
            st.markdown(
                f'<div class="custom-progress"><div class="custom-progress-fill" style="width:{prog}%;background:{color};"></div></div>',
                unsafe_allow_html=True)
            pc1, pc2 = st.columns([1, 20])
            with pc1: st.write(f"{prog}%")
            with pc2: st.write(explanation)

    # 表格
    st.markdown('<div class="milestone-table">', unsafe_allow_html=True)
    st.dataframe(disp_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.warning("No projects match the current filters.")

# -------------------------------------------------
# 8. 提醒（Delivery_Date 超期）
# -------------------------------------------------
if "Delivery_Date" in df.columns and "Lead_Time" in df.columns:
    remind = df[df["Delivery_Date"].isna() | (df["Delivery_Date"] > df["Lead_Time"])][["Project_Name","Lead_Time","Delivery_Date"]]
    if not remind.empty:
        st.markdown(f"<div class='reminder-section'><h3>Delivery Date Issues</h3>{remind.to_html(index=False)}</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("**YIP SHING Project Management System**")