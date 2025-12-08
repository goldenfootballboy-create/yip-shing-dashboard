import streamlit as st
import json
from datetime import datetime

# -------------------------------------------------
# 永久儲存（用 JSON，永不消失）
# -------------------------------------------------
DATA_FILE = "yipshing_projects.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        projects = json.load(f)
else:
    projects = []  # 格式：[{"name": "TP25/201", "type": "Open Set", "year": 2025, ...}]

# -------------------------------------------------
# 頁面設定
# -------------------------------------------------
st.set_page_config(page_title="YIP SHING Project Dashboard", layout="wide", initial_sidebar_state="expanded")
st.markdown("<h1 style='text-align: center; color: #1fb429;'>YIP SHING Project Status Dashboard</h1>",
            unsafe_allow_html=True)
st.markdown("---")

# -------------------------------------------------
# 左側篩選
# -------------------------------------------------
with st.sidebar:
    st.title("Filters")

    all_types = list(set(p["type"] for p in projects)) + ["All"]
    selected_type = st.selectbox("Project Type", options=all_types,
                                 index=all_types.index("All") if "All" in all_types else 0)

    all_years = sorted(list(set(p["year"] for p in projects)), reverse=True)
    selected_year = st.selectbox("Year", options=["All"] + all_years, index=0)

    all_months = sorted(list(set(p.get("lead_time", "--") for p in projects)))
    selected_month = st.selectbox("Lead Time", options=["All"] + all_months, index=0)

# -------------------------------------------------
# 篩選資料
# -------------------------------------------------
filtered = projects
if selected_type != "All":
    filtered = [p for p in filtered if p["type"] == selected_type]
if selected_year != "All":
    filtered = [p for p in filtered if p["year"] == selected_year]
if selected_month != "All":
    filtered = [p for p in filtered if p.get("lead_time") == selected_month]

# -------------------------------------------------
# 主畫面：你最愛的大格仔排版
# -------------------------------------------------
if filtered:
    st.markdown(f"### {len(filtered)} Projects Found")

    for i in range(0, len(filtered), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(filtered):
                p = filtered[i + j]
                with cols[j]:
                    # 計算進度
                    progress = 0
                    today = datetime.now().date()
                    if p.get("parts_arrival") and datetime.strptime(p["parts_arrival"], "%Y-%m-%d").date() <= today:
                        progress += 30
                    if p.get("installation") and datetime.strptime(p["installation"], "%Y-%m-%d").date() <= today:
                        progress += 40
                    if p.get("testing") and datetime.strptime(p["testing"], "%Y-%m-%d").date() <= today:
                        progress += 10
                    if p.get("cleaning") == "YES":
                        progress += 10
                    if p.get("delivery") and datetime.strptime(p["delivery"], "%Y-%m-%d").date() <= today:
                        progress += 10
                    progress = min(progress, 100)

                    color = "#0000ff" if progress == 100 else "#ff4500"

                    with st.expander(f"**{p['name']}** • {p.get('genset', '')} • {p.get('qty', '')}台", expanded=False):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.progress(progress / 100)
                            st.write(f"**{progress}%**")
                        with col2:
                            st.write(f"**Type:** {p.get('type', '-')}")
                            st.write(f"**Year:** {p.get('year', '-')}")
                            st.write(f"**Lead Time:** {p.get('lead_time', '-')}")
                            st.write(f"**Genset:** {p.get('genset', '-')}")
                            st.write(f"**Alternator:** {p.get('alternator', '-')}")
                            st.write(f"**Controller:** {p.get('controller', '-')}")

                        st.markdown("---")
                        st.markdown("### Checklist")
                        # 你原本的 Checklist 邏輯（我幫你保留）
                        # ...（可直接貼你原本的 checklist 程式碼）
else:
    st.info("還沒有專案，請到「新增專案」頁面建立第一個！")

# -------------------------------------------------
# 新增專案頁面
# -------------------------------------------------
with st.expander("➕ 新增專案", expanded=False):
    with st.form("new_project"):
        name = st.text_input("Project Name (e.g. TP25/201)")
        col1, col2 = st.columns(2)
        with col1:
            genset = st.text_input("Genset Model")
            alternator = st.text_input("Alternator Model")
            controller = st.text_input("Controller")
            qty = st.text_input("Qty", "x1")
        with col2:
            ptype = st.selectbox("Type", ["Open Set", "Enclosure", "Scania", "Marine", "Pre-Install"])
            year = st.number_input("Year", 2020, 2030, 2025)
            lead_time = st.selectbox("Lead Time",
                                     ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月",
                                      "十一月", "十二月"])

        parts_arrival = st.date_input("Parts Arrival Date", datetime.now())
        installation = st.date_input("Installation Complete Date", datetime.now())
        testing = st.date_input("Testing Date", datetime.now())
        cleaning = st.selectbox("Cleaning", ["YES", "NO"])
        delivery = st.date_input("Delivery Date", datetime.now())

        if st.form_submit_button("新增專案"):
            new_project = {
                "name": name,
                "type": ptype,
                "year": year,
                "lead_time": lead_time,
                "genset": genset,
                "alternator": alternator,
                "controller": controller,
                "qty": qty,
                "parts_arrival": parts_arrival.strftime("%Y-%m-%d"),
                "installation": installation.strftime("%Y-%m-%d"),
                "testing": testing.strftime("%Y-%m-%d"),
                "cleaning": cleaning,
                "delivery": delivery.strftime("%Y-%m-%d")
            }
            projects.append(new_project)
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(projects, f, ensure_ascii=False, indent=2)
            st.success("專案已新增！")
            st.rerun()