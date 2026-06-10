import streamlit as st
import pandas as pd
import json
from datetime import date
import time
from streamlit_calendar import calendar
from io import BytesIO
import resend
import gspread
from google.oauth2.service_account import Credentials
import time
from datetime import datetime, timezone, timedelta
# reportlab 相關 import
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,       # 解決 NameError: name 'Table' is not defined
    TableStyle   # 用來設定表格樣式
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO   # 你已經有，但放在這裡一起看清楚
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from reportlab.lib.pagesizes import letter, landscape
import plotly.express as px
import plotly.graph_objects as go
# 全域變數
max_retries = 3  # 可選，未來若需重試邏輯再用
# 香港時區 (UTC+8)
hkt = timezone(timedelta(hours=8))
now_hkt = datetime.now(hkt)
# 強制每次進入日曆頁面都重新讀取 Google Sheets（解決跳轉後不更新問題）
st.cache_data.clear()  # 清空所有快取
if "calendar_refresh" not in st.session_state:
    st.session_state["calendar_refresh"] = True
    st.rerun()  # 強制重新執行一次頁面
update_time = now_hkt.strftime('%Y-%m-%d %H:%M')
# 全局安全 index 函數
def safe_index(val, options, default=0):
    try:
        return options.index(val)
    except ValueError:
        return default

def fullscreen_loading(message="正在處理，請稍候..."):
    st.markdown(f"""
    <div style="
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        color: white;
        font-size: 1.8rem;
        font-weight: bold;
    ">
        <div style="
            border: 12px solid #f3f3f3;
            border-top: 12px solid #1fb429;
            border-radius: 50%;
            width: 100px;
            height: 100px;
            animation: spin 1s linear infinite;
            margin-bottom: 30px;
        "></div>
        <div>{message}</div>
    </div>
    <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
    """, unsafe_allow_html=True)


from reportlab.lib.colors import HexColor
def generate_overview_pdf(specs, project_info, qty):
    pdfmetrics.registerFont(TTFont('NotoSansTC', 'fonts/NotoSansTC-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('NotoSansTC-Bold', 'fonts/NotoSansTC-Bold.ttf'))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=28,
        leftMargin=28,
        topMargin=20,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
        fontName='NotoSansTC-Bold', fontSize=21, alignment=TA_CENTER,
        spaceBefore=0, spaceAfter=8, textColor=HexColor('#1e88e5'))

    info_style = ParagraphStyle('Info', parent=styles['Normal'],
        fontName='NotoSansTC-Bold', fontSize=13, alignment=TA_CENTER,
        spaceBefore=4, spaceAfter=12)

    normal = ParagraphStyle('Normal', parent=styles['Normal'],
        fontName='NotoSansTC', fontSize=10.8, leading=13, spaceAfter=3)

    elements = []

    # 判斷是否為 Open Set
    is_open_set = project_info.get('Project_Type', '') == "Open Set"

    # ==================== 判斷區塊是否有輸入 ====================
    def section_has_content(spec, keys):
        for k in keys:
            val = str(spec.get(k, "")).strip()
            if val and val not in ["—", ""]:
                return True
        return False

    # ==================== 共用表格函數 ====================
    def create_table(data, gray=False, header_gray=False):
        t = Table(data, colWidths=[255, 255])
        style_commands = [
            ('FONTNAME', (0, 0), (0, 0), 'NotoSansTC-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 13),
            ('SPAN', (0, 0), (1, 0)),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),

            # ==================== 只讓 "Feature" 和 "Option" 置中 ====================
            ('ALIGN', (0, 1), (0, 1), 'CENTER'),  # Feature 水平置中
            ('ALIGN', (1, 1), (1, 1), 'CENTER'),  # Option 水平置中
            ('VALIGN', (0, 1), (1, 1), 'MIDDLE'),  # 垂直置中

            ('FONTNAME', (0, 2), (-1, -1), 'NotoSansTC'),
            ('FONTSIZE', (0, 2), (-1, -1), 10.5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]

        # Open Set 整表變灰
        if gray:
            style_commands.append(('BACKGROUND', (0, 0), (-1, -1), HexColor('#171616')))

        # 區塊有輸入時，標題列變灰
        if header_gray:
            style_commands.append(('BACKGROUND', (0, 0), (-1, 0), HexColor('#d0d0d0')))

        # Option 欄有值時變灰
        for i in range(2, len(data)):
            option_cell = str(data[i][1]).strip()
            if '：' in option_cell:
                option_value = option_cell.split('：', 1)[1].strip()
            else:
                option_value = option_cell
            if option_value and option_value not in ['—', '']:
                style_commands.append(('BACKGROUND', (1, i), (1, i), HexColor('#e6e6e6')))

        t.setStyle(TableStyle(style_commands))
        return t

    for machine_idx in range(qty):
        if machine_idx > 0:
            elements.append(PageBreak())

        spec = specs[machine_idx] if machine_idx < len(specs) else {}

        # 標題
        project_name = project_info.get('Project_Name', '—')
        customer = project_info.get('Customer', '—')
        elements.append(Paragraph(f"{project_name} ({qty} 台)  - 第 {machine_idx + 1} 台", title_style))
        elements.append(Paragraph(
            f"SO#：{spec.get('so_number', '')}　｜　"
            f"Category：{spec.get('product_category', '')}　｜　"
            f"Code：{spec.get('product_code', '')}　｜　C-Code：{customer}",
            info_style))
        elements.append(Spacer(1, 10))

        # ==================== Engine (發動機) ====================
        engine_keys = ["genset_model", "engine_year", "genset_sn", "engine_color", "prime_standby",
                       "rpm", "voltage", "frequency", "engine_heater",
                       "coolant_temp_sensor", "coolant_sensor", "oil_pressure", "oil_pressure_switch",
                       "hand_pump", "silencer", "flex_pipe", "exhaust_pipe", "fuel_water_separator","coolant_temp_switch"]
        has_engine = section_has_content(spec, engine_keys)

        data = [
            ["Engine (發動機)", ""],
            ["Feature", "Option"],
            ["Model (型號)： " + (spec.get('genset_model') or ''),
             "Coolant temperature sensor： " + (spec.get('coolant_temp_sensor') or '')],
            ["Year (年份)： " + (spec.get('engine_year') or ''),
             "Coolant temperature switch： " + (spec.get('coolant_temp_switch') or '')],
            ["Colour (顏色)： " + (spec.get('engine_color') or ''),
             "Oil Coolant Temp Sensor： " + (spec.get('coolant_sensor') or '')],
            ["Prime/Standby (kW)： " + (spec.get('prime_standby') or ''),
             "Oil Pressure Sensor： " + (spec.get('oil_pressure') or '')],
            ["RPM (轉速)： " + (spec.get('rpm') or ''),
             "Oil pressure switch： " + (spec.get('oil_pressure_switch') or '')],
            ["Voltage (電壓)： " + (spec.get('voltage') or ''), "Hand Swing Pump： " + (spec.get('hand_pump') or '')],
            ["Frequency (頻率)： " + (spec.get('frequency') or ''), "Silencer： " + (spec.get('silencer') or '')],
            ["S/N (序號)： " + (spec.get('genset_sn') or ''),
             "Flexible Pipe & Flange： " + (spec.get('flex_pipe') or '')],
            ["", "Exhaust Pipe： " + (spec.get('exhaust_pipe') or '')],
            ["", "Heater (加熱器) kW： " + (spec.get('engine_heater') or '')],
            ["", "Fuel Water Separator： " + (spec.get('fuel_water_separator') or '')]
        ]
        elements.append(create_table(data, header_gray=has_engine))
        elements.append(Spacer(1, 8))

        # ==================== Alternator (電球) ====================
        alt_keys = ["alt_model", "alt_winding", "droop", "alt_color", "alt_sn", "alt_heater", "pmg"]
        has_alt = section_has_content(spec, alt_keys)

        data = [
            ["Alternator (電球)", ""],
            ["Feature", "Option"],
            ["Model (型號)： " + (spec.get('alt_model') or ''), "Heater： " + (spec.get('alt_heater') or '')],
            ["Winding： " + (spec.get('alt_winding') or ''), "PMG： " + (spec.get('pmg') or '')],
            ["Droop： " + (spec.get('droop') or ''), ""],
            ["Color： " + (spec.get('alt_color') or ''), ""],
            ["S/N： " + (spec.get('alt_sn') or ''), ""],
        ]
        elements.append(create_table(data, header_gray=has_alt))
        elements.append(Spacer(1, 8))

        # ==================== Radiator (水箱) ====================
        rad_keys = ["rad_model", "rad_temp", "fan_size", "radiator_guard", "rad_sn",
                    "fuel_cooler", "low_water", "murphy_coolant", "anti_freezer",
                    "radiator_custom1", "radiator_custom2"]  # ← 已加入新欄位
        has_rad = section_has_content(spec, rad_keys)

        data = [
            ["Radiator (水箱)", ""],
            ["Feature", "Option"],
            ["Model (型號)： " + (spec.get('rad_model') or ''), "Fuel Cooler： " + (spec.get('fuel_cooler') or '')],
            ["Degree (温度)： " + (spec.get('rad_temp') or ''),
             "Low Water Level Switch： " + (spec.get('low_water') or '')],
            ["Fan Size (扇呎吋)： " + (spec.get('fan_size') or ''),
             "Murphy Coolant Level Switch： " + (spec.get('murphy_coolant') or '')],
            ["Protection Cover (保護罩)： " + (spec.get('radiator_guard') or ''),
             "Anti-Freezer： " + (spec.get('anti_freezer') or '')],
            ["S/N： " + (spec.get('rad_sn') or ''), "自行輸入 1： " + (spec.get('radiator_custom1') or '')],  # ← 新增
            ["", "自行輸入 2： " + (spec.get('radiator_custom2') or '')],  # ← 新增
        ]
        elements.append(create_table(data, header_gray=has_rad))
        elements.append(Spacer(1, 8))

        # ==================== Base Frame (底架) ====================
        base_keys = ["base_model", "avm", "base_color", "base_sn"]
        has_base = section_has_content(spec, base_keys)

        data = [
            ["Base Frame (底架)", ""],
            ["Feature", "Option"],
            ["Model (型號)： " + (spec.get('base_model') or ''), "Color： " + (spec.get('base_color') or '')],
            ["Anti-Vibration Mounts (避震腳)： " + (spec.get('avm') or ''), "Spring isolator： " + (spec.get('spring_isolator') or '')],
            ["S/N： " + (spec.get('base_sn') or ''), ""],
        ]
        elements.append(create_table(data, header_gray=has_base))
        elements.append(Spacer(1, 8))

        # ==================== 第二頁 ====================
        elements.append(PageBreak())

        # ==================== Container (貨櫃) ====================
        cont_keys = ["cont_type", "cont_size", "cont_sn", "co_detector", "cont_color","topone_sticker"]
        has_cont = section_has_content(spec, cont_keys)

        data = [
            ["Container (貨櫃)", ""],
            ["Feature", "Option"],
            ["Type (型號)： " + (spec.get('cont_type') or ''), "CO Detector： " + (spec.get('co_detector') or '')],
            ["Dimension (呎吋)： " + (spec.get('cont_size') or ''), "Color： " + (spec.get('cont_color') or '')],
            ["櫃號： " + (spec.get('cont_sn') or ''), "Topone 貼紙： " + (spec.get('topone_sticker') or '')],
        ]
        elements.append(create_table(data, gray=is_open_set, header_gray=has_cont))
        elements.append(Spacer(1, 8))

        # ==================== Breaker (斷路器) ====================
        breaker_keys = ["breaker_model", "breaker_type", "breaker_rating", "breaker_sn",
                        "gear_motor", "shunt_trip", "closing_coil", "uv_relay"]
        has_breaker = section_has_content(spec, breaker_keys)

        data = [
            ["Breaker (斷路器)", ""],
            ["Feature", "Option"],
            ["Model (型號)： " + (spec.get('breaker_model') or ''), "Gear Motor： " + (spec.get('gear_motor') or '')],
            ["Type (類型)： " + (spec.get('breaker_type') or ''), "Shunt Trip： " + (spec.get('shunt_trip') or '')],
            ["Rating： " + (spec.get('breaker_rating') or ''), "Closing Coil： " + (spec.get('closing_coil') or '')],
            ["S/N： " + (spec.get('breaker_sn') or ''), "UV Relay： " + (spec.get('uv_relay') or '')],
        ]
        elements.append(create_table(data, header_gray=has_breaker))
        elements.append(Spacer(1, 8))

        # ==================== Control Panel (控制器) ====================
        panel_keys = ["panel_model", "panel_module", "panel_sn"]
        has_panel = section_has_content(spec, panel_keys)

        data = [
            ["Control Panel (控制器)", ""],
            ["Feature", "Option"],
            ["Model (型號)： " + (spec.get('panel_model') or ''), ""],
            ["Module： " + (spec.get('panel_module') or ''), ""],
            ["S/N： " + (spec.get('panel_sn') or ''), ""],
        ]
        elements.append(create_table(data, header_gray=has_panel))
        elements.append(Spacer(1, 8))

        # ==================== Battery (電池) ====================
        battery_keys = ["battery_model", "battery_switch", "battery_rating", "charger_model"]
        has_battery = section_has_content(spec, battery_keys)

        data = [
            ["Battery (電池)", ""],
            ["Feature", "Option"],
            ["Model (型號)： " + (spec.get('battery_model') or ''), "Charger Model： " + (spec.get('charger_model') or '')],
            ["Battery Switch： " + (spec.get('battery_switch') or ''), ""],
        ]
        elements.append(create_table(data, header_gray=has_battery))
        elements.append(Spacer(1, 8))

        # ==================== Fuel Tank (燃油箱) ====================
        fuel_keys = ["fuel_volume", "fuel_layer", "fuel_gauge", "fuel_level_switch", "fuel_level_sensor", "donaldson_breather","three_way_valve"]
        has_fuel = section_has_content(spec, fuel_keys)

        data = [
            ["Fuel Tank (燃油箱)", ""],
            ["Feature", "Option"],
            ["Volume： " + (spec.get('fuel_volume') or ''), "Fuel Level Gauge： " + (spec.get('fuel_gauge') or '')],
            ["Layer： " + (spec.get('fuel_layer') or ''), "Fuel Level Switch： " + (spec.get('fuel_level_switch') or '')],
            ["", "Fuel Level Sensor： " + (spec.get('fuel_level_sensor') or '')],
            ["", "Donaldson Breather： " + (spec.get('donaldson_breather') or '')],
            ["", "3 way Valve： " + (spec.get('three_way_valve') or '')],
        ]
        elements.append(create_table(data, gray=is_open_set, header_gray=has_fuel))
        elements.append(Spacer(1, 8))

        # ==================== Oil Tank (機油箱) ====================
        oil_keys = ["oil_volume", "oil_donaldson", "murphy_oil"]
        has_oil = section_has_content(spec, oil_keys)

        data = [
            ["Oil Tank (機油箱)", ""],
            ["Feature", "Option"],
            ["Volume： " + (spec.get('oil_volume') or ''), "Donaldson Breather： " + (spec.get('oil_donaldson') or '')],
            ["", "Murphy Coolant Level Switch： " + (spec.get('murphy_oil') or '')],
        ]
        elements.append(create_table(data, gray=is_open_set, header_gray=has_oil))
        elements.append(Spacer(1, 12))

        # ==================== Remarks ====================
        remarks = spec.get("remarks", "").strip()
        if remarks:
            elements.append(Paragraph("Remarks / 備註", normal))
            elements.append(Paragraph(remarks, normal))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
##def send_update_notification_email(project_name, old_specs, new_specs, recipient_emails, project_info):

    st.write("開始發送信 debug...")
    if not recipient_emails:
        st.warning("沒有收件人，跳過發信")
        return

    if "RESEND_API_KEY" not in st.secrets:
        st.error("錯誤：Secrets 中找不到 RESEND_API_KEY")
        return

    api_key = st.secrets["RESEND_API_KEY"]
    st.write("API Key 前 10 字：", api_key[:10] + "...")

    import resend
    resend.api_key = api_key

    # 香港時區時間
    from datetime import datetime, timezone, timedelta
    hkt = timezone(timedelta(hours=8))
    update_time = datetime.now(hkt).strftime('%Y-%m-%d %H:%M')

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #1fb429;">專案 {project_name} 的規格通知</h2>
    """

    if not old_specs:
        # 新增規格：完整列出細節 + 配件 + 已指派部門 + 空缺提醒
        body += f"""
        <p>專案 <strong>{project_name}</strong> 的新規格已建立。</p>
        <p><strong>專案類型：</strong> {project_info.get('Project_Type', '—')}</p>
        <p><strong>建立時間：</strong> {update_time} (香港時間)</p>

        <p><strong>規格細節如下：</strong></p>
        <ul>
            <li><strong>Year:</strong> {project_info.get('Year', '—')}</li>
            <li><strong>Lead Time:</strong> {project_info.get('Lead_Time', '—').strftime('%Y-%m-%d') if pd.notna(project_info.get('Lead_Time')) else '—'}</li>
            <li><strong>Customer:</strong> {project_info.get('Customer', '—')}</li>
            <li><strong>Supervisor:</strong> {project_info.get('Supervisor', '—')}</li>
            <li><strong>Qty:</strong> {project_info.get('Qty', '—')}</li>
        </ul>

        <p><strong>Project Specification:</strong></p>
        <ul>
        """

        for i, spec in enumerate(new_specs):
            body += f"<li><strong>第 {i+1} 台：</strong><ul>"
            body += f"<li>Prime / Standby: {spec.get('prime', '—')} / {spec.get('standby', '—')}</li>"
            body += f"<li>Voltage / Frequency / RPM: {spec.get('voltage', '—')} / {spec.get('frequency', '—')} / {spec.get('rpm', '—')}</li>"
            body += f"<li>Genset model / S/N: {spec.get('genset_model', '—')} / {spec.get('genset_sn', '—')}</li>"
            body += f"<li>Alternator Model / S/N: {spec.get('alt_model', '—')} / {spec.get('alt_sn', '—')}</li>"
            body += f"<li>Panel model / S/N: {spec.get('panel_model', '—')} / {spec.get('panel_sn', '—')}</li>"
            body += f"<li>Breaker Type / Rating / Poles / S/N: {spec.get('breaker_type', '—')} / {spec.get('breaker_rating', '—')} / {spec.get('poles', '—')} / {spec.get('breaker_sn', '—')}</li>"
            body += f"<li>Spring Charging / Control Voltage: {spec.get('spring_charging', '—')} / {spec.get('control_voltage', '—')}</li>"
            body += f"<li>Remarks: {spec.get('remarks', '—')}</li>"
            body += "</ul></li>"

        body += "</ul>"

        # 配件清單（完整列出）
        body += "<p><strong>配件清單：</strong></p><ul>"
        for i, spec in enumerate(new_specs):
            parts = spec.get("parts", [])
            if parts:
                body += f"<li><strong>第 {i+1} 台：</strong><ul>"
                for p in parts:
                    body += f"<li>{p.get('name', '—')} (貨源: {p.get('source', '—')}, 負責部門: {p.get('department', '—')})</li>"
                body += "</ul></li>"
            else:
                body += f"<li><strong>第 {i+1} 台：</strong> 無配件</li>"
        body += "</ul>"

        # 已指派負責部門（按台分組）
        assigned_dept_by_machine = []
        for i, spec in enumerate(new_specs):
            machine_depts = []
            if spec.get('fan_department') and spec.get('fan_department') not in ['—', '']:
                machine_depts.append(f"風扇 - {spec.get('fan_department')}")
            if spec.get('fuel_cooler_department') and spec.get('fuel_cooler_department') not in ['—', '']:
                machine_depts.append(f"燃油冷卻器 - {spec.get('fuel_cooler_department')}")
            if spec.get('coolant_sensor_department') and spec.get('coolant_sensor_department') not in ['—', '']:
                machine_depts.append(f"冷卻液溫度感測器 - {spec.get('coolant_sensor_department')}")
            if spec.get('low_water_department') and spec.get('low_water_department') not in ['—', '']:
                machine_depts.append(f"低水位浮球開關 - {spec.get('low_water_department')}")
            if spec.get('panel_department') and spec.get('panel_department') not in ['—', '']:
                machine_depts.append(f"Panel (控制器) - {spec.get('panel_department')}")
            if spec.get('co_department') and spec.get('co_department') not in ['—', '']:
                machine_depts.append(f"CO 探測器 (OLED) - {spec.get('co_department')}")
            if spec.get('breaker_department') and spec.get('breaker_department') not in ['—', '']:
                machine_depts.append(f"Circuit Breaker (斷路器) - {spec.get('breaker_department')}")
            if spec.get('door_limit_department') and spec.get('door_limit_department') not in ['—', '']:
                machine_depts.append(f"Door Limit Switch - {spec.get('door_limit_department')}")
            if spec.get('avm_department') and spec.get('avm_department') not in ['—', '']:
                machine_depts.append(f"避震器 - {spec.get('avm_department')}")

            if machine_depts:
                assigned_dept_by_machine.append(f"<strong>第 {i+1} 台：</strong><ul>")
                for dept in machine_depts:
                    assigned_dept_by_machine.append(f"<li>{dept}</li>")
                assigned_dept_by_machine.append("</ul>")

        body += "<p><strong>【負責部門】</strong></p>"
        if assigned_dept_by_machine:
            body += "<ul>"
            for item in assigned_dept_by_machine:
                body += item
            body += "</ul>"
        else:
            body += "<p>暫無已指派的負責部門。</p>"

        # 空缺 S/N 提醒
        missing_sn = []
        for i, spec in enumerate(new_specs):
            genset_sn = spec.get('genset_sn', '')
            if not genset_sn or genset_sn.strip() in ['—', 'None', '']:
                missing_sn.append(f"第 {i+1} 台 發動機 S/N")

            alt_sn = spec.get('alt_sn', '')
            if not alt_sn or alt_sn.strip() in ['—', 'None', '']:
                missing_sn.append(f"第 {i+1} 台 電球 S/N")

            panel_sn = spec.get('panel_sn', '')
            if not panel_sn or panel_sn.strip() in ['—', 'None', '']:
                missing_sn.append(f"第 {i+1} 台 Panel S/N")

            breaker_sn = spec.get('breaker_sn', '')
            if not breaker_sn or breaker_sn.strip() in ['—', 'None', '']:
                missing_sn.append(f"第 {i+1} 台 斷路器 S/N")

            rad_sn = spec.get('rad_sn', '')
            if not rad_sn or rad_sn.strip() in ['—', 'None', '']:
                missing_sn.append(f"第 {i+1} 台 水箱 S/N")

            base_sn = spec.get('base_sn', '')
            if not base_sn or base_sn.strip() in ['—', 'None', '']:
                missing_sn.append(f"第 {i+1} 台 底架 S/N")

        body += "<p><strong>【請相關同事更新S/N】</strong></p><ul style='color: #d32f2f;'>"
        if missing_sn:
            body += "<li>S/N 尚未填寫：<ul>"
            for item in missing_sn:
                body += f"<li>{item}</li>"
            body += "</ul></li>"
        else:
            body += "<li>所有 S/N 已填寫完成。</li>"
        body += "</ul>"

    else:
        # 編輯模式：只列變更項目
        body += f"""
        <p>專案 <strong>{project_name}</strong> 的規格已更新。</p>
        <p><strong>更新時間：</strong> {update_time} (香港時間)</p>
        <p><strong>主要變更如下（每台機器）：</strong></p>
        <ul>
        """

        for i in range(len(new_specs)):
            old = old_specs[i] if i < len(old_specs) else {}
            new = new_specs[i]

            body += f"<li><strong>第 {i+1} 台：</strong><ul>"

            static_fields = [
                "prime", "standby", "voltage", "frequency", "rpm",
                "genset_model", "genset_sn", "engine_color", "engine_year", "engine_heater",
                "alt_model", "alt_sn", "alt_color", "droop", "pmg", "alt_heater",
                "rad_model", "rad_sn", "rad_temp", "fan_size", "radiator_guard",
                "panel_model", "panel_sn", "co_detector", "breaker_type", "breaker_rating", "poles", "breaker_sn", "base_sn", "control_voltage"
            ]

            has_change = False
            for field in static_fields:
                old_val = old.get(field, "—")
                new_val = new.get(field, "—")
                if old_val != new_val:
                    body += f"<li>{field}: {old_val} → {new_val}</li>"
                    has_change = True

            dept_fields = [
                "fan_department", "fuel_cooler_department", "coolant_sensor_department",
                "low_water_department", "panel_department", "co_department", "breaker_department"
            ]
            for field in dept_fields:
                old_val = old.get(field, "—")
                new_val = new.get(field, "—")
                if old_val != new_val:
                    body += f"<li>{field} (負責部門): {old_val} → {new_val}</li>"
                    has_change = True

            old_parts = old.get("parts", [])
            new_parts = new.get("parts", [])
            if len(old_parts) != len(new_parts) or any(p1["name"] != p2["name"] for p1, p2 in zip(old_parts, new_parts)):
                body += f"<li>配件清單有變更（新增/刪除/修改 {len(new_parts)} 項）</li>"
                has_change = True

            old_check = old.get("delivery_checklist", [])
            new_check = new.get("delivery_checklist", [])
            changed_checks = []
            for oc, nc in zip(old_check, new_check):
                if oc.get("checked") != nc.get("checked"):
                    ch_status = "已勾選" if nc.get("checked") else "取消勾選"
                    changed_checks.append(f"{nc.get('name')}：{ch_status}")
            if changed_checks:
                body += "<li>出貨檢查清單打勾變更：<ul>"
                for ch in changed_checks:
                    body += f"<li>{ch}</li>"
                body += "</ul></li>"
                has_change = True

            if not has_change:
                body += "<li>本台無變更</li>"

            body += "</ul></li>"

        body += "</ul>"

    # 固定結尾
    body += """
    <br><br>
    本郵件為自動生成，請勿回覆。如有疑問，請聯絡專案負責人。<br>
    <a href="https://yip-shing-dashboard-bhkutkwadqv2ice5ephot2.streamlit.app/" style="color: #1fb429; text-decoration: underline; font-weight: bold;">請點擊連結更新資料：進入 YIP SHING Dashboard</a>
    </body>
    </html>
    """

    params = {
        "from": "YIP SHING Dashboard <dashboard@topone-power.com>",
        "to": recipient_emails,
        "subject": f"專案規格通知：{project_name}",
        "html": body,
    }

    try:
        st.write("正在呼叫 Resend API...")
        response = resend.Emails.send(params)
        st.success(f"發送成功！Resend 訊息 ID: {response.get('id')}")
    except Exception as e:
        st.error(f"發送失敗：{str(e)}")
        st.write("錯誤類型：", type(e).__name__)
        st.write("完整錯誤：", str(e))
        ##
# 頁面設定
st.set_page_config(
    page_title="YIP SHING Project Dashboard",
    page_icon="https://i.imgur.com/Q8ehtk3.jpeg",
    layout="wide"
)
# 頁面設定
st.set_page_config(
    page_title="YIP SHING Project Dashboard",
    page_icon="https://i.imgur.com/Q8ehtk3.jpeg",
    layout="wide"
)

# 初始化 dialog active flags
if "dialog_active" not in st.session_state:
    st.session_state.dialog_active = None

# Google Sheets 連線 + 重試機制（使用 open_by_key + 純 ID）
creds_info = st.secrets["connections"]["gsheets"]
creds = Credentials.from_service_account_info(
    creds_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
client = gspread.authorize(creds)

spreadsheet = None
for attempt in range(3):
    try:
        spreadsheet_id = creds_info["spreadsheet"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        st.success("連線成功！Spreadsheet 名稱：" + spreadsheet.title)
        break
    except gspread.exceptions.APIError as e:
        st.warning(f"連線失敗（嘗試 {attempt+1}/3）：{str(e)}，5 秒後重試...")
        time.sleep(5)
    except Exception as e:
        st.error(f"連線異常：{str(e)}")
        raise e

if spreadsheet is None:
    st.error("無法連線到 Google Sheets，請稍後再試或檢查 secrets.toml")
    st.stop()

# 讀取 projects 工作表
worksheet_projects = spreadsheet.worksheet("projects")
data = worksheet_projects.get_all_records()
df = pd.DataFrame(data)

# 讀取 checklist 工作表
worksheet_checklist = spreadsheet.worksheet("checklist")
checklist_raw = pd.DataFrame(worksheet_checklist.get_all_records())
worksheet_manpower  = spreadsheet.worksheet("supremacy_manpower")
# 處理 checklist_db
checklist_db = {}
if not checklist_raw.empty:
    for _, row in checklist_raw.iterrows():
        if "Project_Name" in row and "Checklist_Data" in row and pd.notna(row["Checklist_Data"]):
            try:
                checklist_db[row["Project_Name"]] = json.loads(row["Checklist_Data"])
            except:
                pass

# 欄位補充與資料轉換（放在讀取後）
required = ["Project_Type","Project_Name","Year","Lead_Time","Customer","Supervisor",
            "Qty","Real_Count","Project_Spec","Progress_Reminder",
            "Parts_Arrival","Installation_Complete","Testing_Complete","Cleaning_Complete","Delivery_Complete","avm_qty"]

for c in required:
    if c not in df.columns:
        if c == "Year":
            df[c] = 2025
        elif c in ["Qty", "Real_Count", "avm_qty"]:
            df[c] = 0
        else:
            df[c] = ""

date_cols = ["Lead_Time","Parts_Arrival","Installation_Complete","Testing_Complete","Cleaning_Complete","Delivery_Complete"]
for c in date_cols:
    df[c] = pd.to_datetime(df[c], errors="coerce")

df["Year"] = pd.to_numeric(df["Year"], errors="coerce").fillna(date.today().year).astype(int)
df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(1).astype(int)
df["Real_Count"] = pd.to_numeric(df["Real_Count"], errors="coerce").fillna(df["Qty"]).astype(int)
df["avm_qty"] = pd.to_numeric(df["avm_qty"], errors="coerce").fillna(0).astype(int)

# 儲存函數（使用 gspread）
def save_projects():
    df_save = df.copy()
    for c in date_cols:
        df_save[c] = df_save[c].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "")
    numeric_cols = ["Qty", "Real_Count", "avm_qty"]  # 加 avm_qty
    for c in numeric_cols:
        if c in df_save.columns:
            df_save[c] = pd.to_numeric(df_save[c], errors='coerce').fillna(0).astype(int)
    worksheet_projects.clear()
    worksheet_projects.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    time.sleep(2)

def save_checklist():
    if not checklist_db:
        empty_df = pd.DataFrame(columns=["Project_Name", "Checklist_Data"])
        worksheet_checklist.clear()
        worksheet_checklist.update([empty_df.columns.values.tolist()] + empty_df.values.tolist())
    else:
        checklist_list = [{"Project_Name": k, "Checklist_Data": json.dumps(v, ensure_ascii=False)} for k, v in checklist_db.items()]
        checklist_save = pd.DataFrame(checklist_list)
        worksheet_checklist.clear()
        worksheet_checklist.update([checklist_save.columns.values.tolist()] + checklist_save.values.tolist())
    time.sleep(2)

# 進度計算 + 顏色 + fmt
def calculate_progress(row):
    p = 0
    today = date.today()
    if pd.notna(row.get("Parts_Arrival")) and row["Parts_Arrival"].date() < today:
        p += 30
    if pd.notna(row.get("Installation_Complete")) and row["Installation_Complete"].date() < today:
        p += 40
    if pd.notna(row.get("Testing_Complete")) and row["Testing_Complete"].date() < today:
        p += 10
    if pd.notna(row.get("Cleaning_Complete")) and row["Cleaning_Complete"].date() < today:
        p += 10
    if pd.notna(row.get("Delivery_Complete")) and row["Delivery_Complete"].date() < today:
        p += 10
    return min(p, 100)

def get_color(pct):
    if pct >= 100: return "#0066ff"
    elif pct >= 90: return "#00aa00"
    elif pct >= 70: return "#66cc66"
    elif pct >= 30: return "#ffaa00"
    else: return "#ff4444"

def fmt(d):
    return pd.to_datetime(d).strftime("%Y-%m-%d") if pd.notna(d) else "—"

# 專案卡片渲染
def render_project_card(row, idx):
    project_name = row["Project_Name"]
    current_check = checklist_db.get(project_name, {"purchase": [], "done_p": [], "drawing": [], "done_d": []})
    all_items = current_check["purchase"] + current_check["drawing"]
    done_items = set(current_check["done_p"]) | set(current_check["done_d"])
    real_items = [item for item in all_items if item and str(item).strip()]
    has_missing = any(str(item).strip() and str(item) not in done_items for item in real_items)
    all_done = len(real_items) > 0 and not has_missing
    is_empty = len(real_items) == 0

    status_tag = ""
    if is_empty:
        status_tag = '<span style="background:#888888; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:0.8rem; margin-left:10px;">Please add checklist</span>'
    elif all_done:
        status_tag = '<span style="background:#F0FFFD; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:1.2rem; margin-left:10px;">✅</span>'
    elif has_missing:
        status_tag = '<span style="background:#ff4444; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:0.8rem; margin-left:10px;">Missing Submission</span>'

    st.markdown(f"""
    <div style="background: linear-gradient(to right, #1e88e5 0%, #f0f0f0 0%); 
                border-radius: 8px; padding: 12px 16px; margin: 10px 0; 
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-weight: bold; font-size:1.1rem; color: #1e3a8a;">
                {project_name} • {row.get('Project_Type', '')}
            </div>
            <div>{status_tag}</div>
        </div>
        <div style="font-size:0.9rem; margin-top:6px; color:#444;">
            {row.get('Customer','—')} | {row.get('Supervisor','—')} | Qty: {row.get('Qty',0)} | 
            Lead Time: {fmt(row.get('Lead_Time')) if pd.notna(row.get('Lead_Time')) else '—'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"Details • {row['Project_Name']}", expanded=False):
        # 基本專案資訊
        st.markdown(f"**Year:** {row.get('Year', '—')} | **Lead Time:** {fmt(row.get('Lead_Time')) if pd.notna(row.get('Lead_Time')) else '—'}")
        st.markdown(f"**Customer:** {row.get('Customer','—')} | **Supervisor:** {row.get('Supervisor','—')} | **Qty:** {row.get('Qty', 0)}")

        st.markdown("---")

        # 讀取規格資料
        spec_text = row.get("Project_Spec", "")
        specs = []
        if spec_text:
            try:
                if "||EXTRA||" in spec_text:
                    extra_json = spec_text.split("||EXTRA||")[1]
                    specs = json.loads(extra_json)
                    if not isinstance(specs, list):
                        specs = [specs]
                else:
                    specs = [json.loads(spec_text)]
            except:
                specs = []

        qty = row.get("Qty", 1)
        if len(specs) < qty:
            specs += [{}] * (qty - len(specs))

        if qty == 1:
            spec = specs[0] if specs else {}
            st.markdown("**Project Specification**")
            st.markdown(
                f"**Prime/Standby (kW)：** {spec.get('prime_standby', '—')}　　"
                f"**Voltage (電壓)：** {spec.get('voltage', '—')}　　"
                f"**Frequency (頻率)：** {spec.get('frequency', '—')}"
            )
            st.markdown(
                f"**Engine Model (型號)：** {spec.get('genset_model', '—')}　　**S/N (序號)：** {spec.get('genset_sn', '—')}"
            )
            st.markdown(
                f"**Alternator Model (型號)：** {spec.get('alt_model', '—')}　　**S/N (序號)：** {spec.get('alt_sn', '—')}"
            )
            st.markdown(
                f"**Radiator Model (型號)：** {spec.get('rad_model', '—')}　　**S/N (序號)：** {spec.get('rad_sn', '—')}"
            )
            st.markdown(
                f"**Base Frame (型號)：** {spec.get('base_model', '—')}　　**S/N (序號)：** {spec.get('base_sn', '—')}"
            )
            st.markdown(
                f"**Breaker (斷路器) Model (型號)：** {spec.get('breaker_model', '—')}　　**Type (類型)：** {spec.get('breaker_type', '—')}　　**Rating：** {spec.get('breaker_rating', '—')}"
            )
            st.markdown(
                f"**Control Panel (控制器) Model (型號)：** {spec.get('panel_model', '—')}　　**S/N：** {spec.get('panel_sn', '—')}"
            )

            remarks = spec.get("remarks", "").strip()
            if remarks:
                st.markdown("---")
                st.markdown("**Remarks：**")
                st.caption(remarks)

        else:
            tabs = st.tabs([f"第 {i+1} 台" for i in range(qty)])
            for i in range(qty):
                with tabs[i]:
                    spec = specs[i] if i < len(specs) else {}
                    st.markdown("**Project Specification**")
                    st.markdown(
                        f"**Prime/Standby (kW)：** {spec.get('prime_standby', '—')}　　"
                        f"**Voltage (電壓)：** {spec.get('voltage', '—')}　　"
                        f"**Frequency (頻率)：** {spec.get('frequency', '—')}"
                    )
                    st.markdown(
                        f"**Engine Model (型號)：** {spec.get('genset_model', '—')}　　**S/N (序號)：** {spec.get('genset_sn', '—')}"
                    )
                    st.markdown(
                        f"**Alternator Model (型號)：** {spec.get('alt_model', '—')}　　**S/N (序號)：** {spec.get('alt_sn', '—')}"
                    )
                    st.markdown(
                        f"**Radiator Model (型號)：** {spec.get('rad_model', '—')}　　**S/N (序號)：** {spec.get('rad_sn', '—')}"
                    )
                    st.markdown(
                        f"**Base Frame (型號)：** {spec.get('base_model', '—')}　　**S/N (序號)：** {spec.get('base_sn', '—')}"
                    )
                    st.markdown(
                        f"**Breaker (斷路器) Model (型號)：** {spec.get('breaker_model', '—')}　　**Type (類型)：** {spec.get('breaker_type', '—')}　　**Rating：** {spec.get('breaker_rating', '—')}"
                    )
                    st.markdown(
                        f"**Control Panel (控制器) Model (型號)：** {spec.get('panel_model', '—')}　　**S/N：** {spec.get('panel_sn', '—')}"
                    )

                    remarks = spec.get("remarks", "").strip()
                    if remarks:
                        st.markdown("---")
                        st.markdown("**Remarks：**")
                        st.caption(remarks)

        # ==================== OverView 按鈕（只負責觸發） ====================
        if st.button("📊 OverView 完整規格總覽", key=f"overall_spec_btn_{idx}", use_container_width=True, type="secondary"):
            st.session_state["show_overview_dialog"] = True
            st.session_state["overview_row"] = row
            st.session_state["overview_qty"] = row.get("Qty", 1)
            st.rerun()


        if st.button("Checklist Panel", key=f"cl_btn_{idx}", use_container_width=True):
            st.session_state[f"cl_open_{idx}"] = not st.session_state.get(f"cl_open_{idx}", False)

        if st.session_state.get(f"cl_open_{idx}", False):
            current = checklist_db.get(project_name, {"purchase": [], "done_p": [], "drawing": [], "done_d": []})

            st.markdown("<h4 style='text-align:center;'>Purchase List        Drawings Submission</h4>", unsafe_allow_html=True)

            new_purchase = []
            new_done_p = set()
            new_drawing = []
            new_done_d = set()

            max_rows = max(len(current["purchase"]), len(current["drawing"]), 6)

            for i in range(max_rows):
                c1, c2 = st.columns(2)
                with c1:
                    text = current["purchase"][i] if i < len(current["purchase"]) else ""
                    checked = text in current["done_p"]
                    col_chk, col_txt = st.columns([1,7])
                    with col_chk:
                        chk = st.checkbox("", value=checked, key=f"p_{idx}_{i}")
                    with col_txt:
                        txt = st.text_input("", value=text, key=f"pt_{idx}_{i}", label_visibility="collapsed")
                    if txt.strip():
                        new_purchase.append(txt.strip())
                        if chk:
                            new_done_p.add(txt.strip())
                with c2:
                    text = current["drawing"][i] if i < len(current["drawing"]) else ""
                    checked = text in current["done_d"]
                    col_chk, col_txt = st.columns([1,7])
                    with col_chk:
                        chk = st.checkbox("", value=checked, key=f"d_{idx}_{i}")
                    with col_txt:
                        txt = st.text_input("", value=text, key=f"dt_{idx}_{i}", label_visibility="collapsed")
                    if txt.strip():
                        new_drawing.append(txt.strip())
                        if chk:
                            new_done_d.add(txt.strip())

            if st.button("SAVE CHECKLIST", key=f"save_cl_{idx}", type="primary", use_container_width=True):
                checklist_db[project_name] = {
                    "purchase": new_purchase,
                    "done_p": list(new_done_p),
                    "drawing": new_drawing,
                    "done_d": list(new_done_d)
                }
                save_checklist()
                st.cache_data.clear()
                st.success("Checklist 已永久儲存到 Google Sheets！")
                st.rerun()

    col_edit_spec, col_edit_info, col_delete = st.columns(3)
    with col_edit_spec:
        if st.button("Edit Project Spec.", key=f"spec_btn_{idx}", type="primary", use_container_width=True):
            st.session_state["current_edit_idx"] = idx
            st.session_state["show_edit_spec_dialog"] = True
            st.rerun()
    with col_edit_info:
        if st.button("Edit Info.", key=f"info_btn_{idx}", type="secondary", use_container_width=True):
            st.session_state["current_edit_idx"] = idx
            st.session_state["show_edit_info_dialog"] = True
            st.rerun()
    with col_delete:
        if st.button("Delete", key=f"del_{idx}", type="secondary", use_container_width=True):
            st.session_state["delete_idx"] = idx
            st.session_state["show_delete_confirm"] = True

    delete_placeholder = st.empty()
    if st.session_state.get("show_delete_confirm", False) and st.session_state.get("delete_idx") == idx:
        with delete_placeholder.container():
            st.markdown("---")
            st.warning(f"確定要刪除專案 **{row['Project_Name']}** 嗎？此動作無法復原！")
            col_yes, col_no = st.columns(2)
            with col_yes:
                delete_disabled = st.session_state.get(f"deleting_{idx}", False)
                if st.button("確認刪除", type="primary", key=f"confirm_del_{idx}", disabled=delete_disabled):
                    st.session_state[f"deleting_{idx}"] = True
                    st.rerun()
            with col_no:
                if st.button("取消", key=f"cancel_del_{idx}"):
                    st.session_state["show_delete_confirm"] = False
                    st.rerun()

        if st.session_state.get(f"deleting_{idx}", False):
            fullscreen_loading("正在刪除專案，請稍候...")

            df.drop(idx, inplace=True)
            df.reset_index(drop=True, inplace=True)
            save_projects()
            checklist_db.pop(row["Project_Name"], None)
            save_checklist()
            st.cache_data.clear()
            st.session_state["show_delete_confirm"] = False
            st.session_state[f"deleting_{idx}"] = False
            st.success(f"已成功刪除專案：{row['Project_Name']}")
            st.rerun()



# Edit Project Specification Dialog
if st.session_state.get("show_edit_spec_dialog", False):

    idx_to_edit = st.session_state["current_edit_idx"]
    row_to_edit = df.loc[idx_to_edit]
    qty = row_to_edit["Qty"]
    project_type = row_to_edit["Project_Type"]
    is_open_or_marine = project_type in ["Open Set", "Marine"]

    spec_text = row_to_edit.get("Project_Spec", "")
    if "||EXTRA||" in spec_text:
        try:
            extra_json = spec_text.split("||EXTRA||")[1]
            specs = json.loads(extra_json)
            if not isinstance(specs, list):
                specs = [specs]
        except:
            specs = [{} for _ in range(qty)]
    else:
        specs = [{} for _ in range(qty)]

    if len(specs) < qty:
        specs += [{}] * (qty - len(specs))

    @st.dialog("Edit Project Specification", width="large")
    def edit_spec_dialog():
        st.markdown(f"**正在編輯專案：{row_to_edit['Project_Name']} ({qty} 台機器)**")

        st.markdown(
            """
            <style>
            div[data-testid="column"] {
                display: flex !important;
                align-items: center !important;
            }
            div[data-testid="column"] div[data-testid="stTextInput"] > div > div,
            div[data-testid="column"] div[data-testid="stSelectbox"] > div > div {
                width: 100% !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        tabs = st.tabs([f"第 {i+1} 台" for i in range(qty)])

        new_specs = []
        if qty > 1:
            st.markdown("---")
            st.markdown("### 規格快速複製工具")
            if st.button("📋 從第 1 台複製規格 → 所有其他台",
                         type="primary",
                         use_container_width=True,
                         help="點擊後會把目前第1台已填寫的規格，複製到第2台～最後一台"):

                source_i = 0
                static_fields = [
                    # 基本資訊
                    "so_number", "product_category", "product_code",

                    # Engine Feature
                    "genset_model", "engine_year", "engine_color", "prime_standby",
                    "rpm", "voltage", "frequency", "genset_sn",

                    # Engine Option
                    "coolant_temp_sensor", "coolant_sensor", "oil_pressure", "oil_pressure_switch",
                    "hand_pump", "silencer", "flex_pipe", "exhaust_pipe",
                    "engine_heater", "fuel_water_separator",

                    # Alternator
                    "alt_model", "alt_winding", "alt_color", "alt_sn",
                    "alt_heater", "droop", "pmg",

                    # Radiator
                    "rad_model", "rad_temp", "fan_size", "radiator_guard", "rad_sn",
                    "fuel_cooler", "low_water", "murphy_coolant", "anti_freezer",

                    # Base Frame
                    "base_model", "avm", "base_color", "base_sn",

                    # Container
                    "cont_type", "cont_size", "cont_sn", "co_detector", "cont_color", "topone_sticker",

                    # Breaker
                    "breaker_model", "breaker_type", "breaker_rating", "breaker_sn",
                    "gear_motor", "shunt_trip", "closing_coil", "uv_relay",

                    # Control Panel
                    "panel_model", "panel_module", "panel_sn",

                    # Battery
                    "battery_model", "battery_switch", "charger_model",

                    # Fuel Tank
                    "fuel_volume", "fuel_layer", "fuel_gauge", "fuel_level_switch",
                    "fuel_level_sensor", "donaldson_breather", "three_way_valve",

                    # Oil Tank
                    "oil_volume", "oil_donaldson", "murphy_oil",

                    # Remarks
                    "remarks"
                ]

                for field in static_fields:
                    src_key = f"edit_{field}_{idx_to_edit}_{source_i}"
                    if src_key in st.session_state:
                        value = st.session_state[src_key]
                        for target_i in range(1, qty):
                            target_key = f"edit_{field}_{idx_to_edit}_{target_i}"
                            st.session_state[target_key] = value

                st.success("已成功將第 1 台的規格複製到其他所有台！")
                st.rerun()

        for i in range(qty):
            with tabs[i]:
                current = specs[i] if i < len(specs) else {}

                # ==================== 基本資訊 ====================
                st.markdown("### 基本資訊")
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                with col1:
                    e_so_number = st.text_input("SO#", value=current.get("so_number", ""),
                                                key=f"edit_so_number_{idx_to_edit}_{i}")
                with col2:
                    e_product_category = st.text_input("Product Category", value=current.get("product_category", ""),
                                                       key=f"edit_product_category_{idx_to_edit}_{i}")
                with col3:
                    e_product_code = st.text_input("Product Code", value=current.get("product_code", ""),
                                                   key=f"edit_product_code_{idx_to_edit}_{i}")
                with col4:
                    st.markdown("**QTY**")
                    st.markdown(f"<h3 style='margin: 0; color: #1e88e5;'>{qty}</h3>", unsafe_allow_html=True)

                st.markdown("---")

                # ==================== Engine (發動機) ====================
                with st.expander("Engine (發動機)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: e_genset_model = st.text_input("", value=current.get("genset_model", ""),
                                                                       key=f"edit_genset_model_{idx_to_edit}_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Year (年份)")
                        with col_input: e_engine_year = st.text_input("", value=current.get("engine_year", ""),
                                                                      key=f"edit_engine_year_{idx_to_edit}_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Colour (顏色)")
                        with col_input: e_engine_color = st.text_input("", value=current.get("engine_color", ""),
                                                                       key=f"edit_engine_color_{idx_to_edit}_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Prime/Standby (kW)")
                        with col_input: e_prime_standby = st.text_input("", placeholder="例如: 100/110",
                                                                        value=current.get("prime_standby", ""),
                                                                        key=f"edit_prime_standby_{idx_to_edit}_{i}",
                                                                        label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("RPM (轉速)")
                        with col_input: e_rpm = st.text_input("", value=current.get("rpm", ""),
                                                              key=f"edit_rpm_{idx_to_edit}_{i}",
                                                              label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Voltage (電壓)")
                        with col_input: e_voltage = st.text_input("", value=current.get("voltage", ""),
                                                                  key=f"edit_voltage_{idx_to_edit}_{i}",
                                                                  label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Frequency (頻率)")
                        with col_input: e_frequency = st.text_input("", value=current.get("frequency", ""),
                                                                    key=f"edit_frequency_{idx_to_edit}_{i}",
                                                                    label_visibility="collapsed")


                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N (序號)")
                        with col_input: e_genset_sn = st.text_input("", value=current.get("genset_sn", ""),
                                                                    key=f"edit_genset_sn_{idx_to_edit}_{i}",
                                                                    label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Coolant temperature sensor")
                        with col_input: e_coolant_temp_sensor = st.text_input("",
                                                                              value=current.get("coolant_temp_sensor",
                                                                                                ""),
                                                                              key=f"edit_coolant_temp_sensor_{idx_to_edit}_{i}",
                                                                              label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Coolant temperature switch")
                        with col_input: e_coolant_temp_switch = st.text_input("", value=current.get("coolant_temp_switch", ""),
                                                                              key=f"edit_coolant_temp_switch_{idx_to_edit}_{i}",
                                                                              label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Oil Coolant Temp Sensor")
                        with col_input: e_coolant_sensor = st.text_input("", value=current.get("coolant_sensor", ""),
                                                                         key=f"edit_coolant_sensor_{idx_to_edit}_{i}",
                                                                         label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Oil Pressure Sensor")
                        with col_input: e_oil_pressure = st.text_input("", value=current.get("oil_pressure", ""),
                                                                       key=f"edit_oil_pressure_{idx_to_edit}_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Oil pressure switch")
                        with col_input: e_oil_pressure_switch = st.text_input("",
                                                                              value=current.get("oil_pressure_switch",
                                                                                                ""),
                                                                              key=f"edit_oil_pressure_switch_{idx_to_edit}_{i}",
                                                                              label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Hand Swing Pump")
                        with col_input: e_hand_pump = st.text_input("", value=current.get("hand_pump", ""),
                                                                    key=f"edit_hand_pump_{idx_to_edit}_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Silencer")
                        with col_input: e_silencer = st.text_input("", value=current.get("silencer", ""),
                                                                   key=f"edit_silencer_{idx_to_edit}_{i}",
                                                                   label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Flexible Pipe & Flange")
                        with col_input: e_flex_pipe = st.text_input("", value=current.get("flex_pipe", ""),
                                                                    key=f"edit_flex_pipe_{idx_to_edit}_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Exhaust Pipe")
                        with col_input: e_exhaust_pipe = st.text_input("", value=current.get("exhaust_pipe", ""),
                                                                       key=f"edit_exhaust_pipe_{idx_to_edit}_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Heater (加熱器) kW")
                        with col_input: e_engine_heater = st.text_input("", value=current.get("engine_heater", ""),
                                                                        key=f"edit_engine_heater_{idx_to_edit}_{i}",
                                                                        label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fuel Water Separator")
                        with col_input: e_fuel_water_separator = st.text_input("",
                                                                               value=current.get("fuel_water_separator",
                                                                                                 ""),
                                                                               key=f"edit_fuel_water_separator_{idx_to_edit}_{i}",
                                                                               label_visibility="collapsed")

                st.markdown("---")

                # ==================== Alternator (電球) ====================
                with st.expander("Alternator (電球)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: e_alt_model = st.text_input("", value=current.get("alt_model", ""),
                                                                    key=f"edit_alt_model_{idx_to_edit}_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Winding")
                        with col_input: e_alt_winding = st.text_input("", value=current.get("alt_winding", ""),
                                                                      key=f"edit_alt_winding_{idx_to_edit}_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Droop")
                        with col_input: e_droop = st.text_input("", value=current.get("droop", ""),
                                                                key=f"edit_droop_{idx_to_edit}_{i}",
                                                                label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Color")
                        with col_input: e_alt_color = st.text_input("", value=current.get("alt_color", ""),
                                                                    key=f"edit_alt_color_{idx_to_edit}_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N")
                        with col_input: e_alt_sn = st.text_input("", value=current.get("alt_sn", ""),
                                                                 key=f"edit_alt_sn_{idx_to_edit}_{i}",
                                                                 label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Heater")
                        with col_input: e_alt_heater = st.text_input("", value=current.get("alt_heater", ""),
                                                                     key=f"edit_alt_heater_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("PMG")
                        with col_input: e_pmg = st.text_input("", value=current.get("pmg", ""),
                                                              key=f"edit_pmg_{idx_to_edit}_{i}",
                                                              label_visibility="collapsed")

                st.markdown("---")

                # ==================== Radiator (水箱) ====================
                with st.expander("Radiator (水箱)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: e_rad_model = st.text_input("", value=current.get("rad_model", ""),
                                                                    key=f"edit_rad_model_{idx_to_edit}_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Degree (温度)")
                        with col_input: e_rad_temp = st.text_input("", value=current.get("rad_temp", ""),
                                                                   key=f"edit_rad_temp_{idx_to_edit}_{i}",
                                                                   label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fan Size (扇呎吋)")
                        with col_input: e_fan_size = st.text_input("", value=current.get("fan_size", ""),
                                                                   key=f"edit_fan_size_{idx_to_edit}_{i}",
                                                                   label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Protection Cover (保護罩)")
                        with col_input: e_radiator_guard = st.text_input("", value=current.get("radiator_guard", ""),
                                                                         key=f"edit_radiator_guard_{idx_to_edit}_{i}",
                                                                         label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N")
                        with col_input: e_rad_sn = st.text_input("", value=current.get("rad_sn", ""),
                                                                 key=f"edit_rad_sn_{idx_to_edit}_{i}",
                                                                 label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fuel Cooler")
                        with col_input: e_fuel_cooler = st.text_input("", value=current.get("fuel_cooler", ""),
                                                                      key=f"edit_fuel_cooler_{idx_to_edit}_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Low Water Level Switch")
                        with col_input: e_low_water = st.text_input("", value=current.get("low_water", ""),
                                                                    key=f"edit_low_water_{idx_to_edit}_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Murphy Coolant Level Switch")
                        with col_input: e_murphy_coolant = st.text_input("", value=current.get("murphy_coolant", ""),
                                                                         key=f"edit_murphy_coolant_{idx_to_edit}_{i}",
                                                                         label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Anti-Freezer")
                        with col_input: e_anti_freezer = st.text_input("", value=current.get("anti_freezer", ""),
                                                                       key=f"edit_anti_freezer_{idx_to_edit}_{i}",
                                                                       label_visibility="collapsed")

                        col1, col2 = st.columns(2)
                        with col1:
                            e_radiator_custom1 = st.text_input("",
                                                               value=current.get("radiator_custom1", ""),
                                                               key=f"edit_radiator_custom1_{idx_to_edit}_{i}",
                                                               label_visibility="collapsed",
                                                               placeholder="自行輸入 1")
                        with col2:
                            e_radiator_custom2 = st.text_input("",
                                                               value=current.get("radiator_custom2", ""),
                                                               key=f"edit_radiator_custom2_{idx_to_edit}_{i}",
                                                               label_visibility="collapsed",
                                                               placeholder="自行輸入 2")


                st.markdown("---")

                # ==================== Base Frame (底架) ====================
                with st.expander("Base Frame (底架)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: e_base_model = st.text_input("", value=current.get("base_model", ""),
                                                                     key=f"edit_base_model_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Anti-Vibration Mounts (避震腳)")
                        with col_input: e_avm = st.text_input("", value=current.get("avm", ""),
                                                              key=f"edit_avm_{idx_to_edit}_{i}",
                                                              label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N")
                        with col_input: e_base_sn = st.text_input("", value=current.get("base_sn", ""),
                                                                  key=f"edit_base_sn_{idx_to_edit}_{i}",
                                                                  label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Color")
                        with col_input: e_base_color = st.text_input("", value=current.get("base_color", ""),
                                                                     key=f"edit_base_color_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Spring isolator")
                        with col_input: e_spring_isolator = st.text_input("", value=current.get("spring_isolator", ""),
                                                                          key=f"edit_spring_isolator_{idx_to_edit}_{i}",
                                                                          label_visibility="collapsed")

                st.markdown("---")

                # ==================== Container (貨櫃) ====================
                with st.expander("Container (貨櫃)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Type (型號)")
                        with col_input: e_cont_type = st.text_input("", value=current.get("cont_type", ""),
                                                                    key=f"edit_cont_type_{idx_to_edit}_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Dimension (呎吋)")
                        with col_input: e_cont_size = st.text_input("", value=current.get("cont_size", ""),
                                                                    key=f"edit_cont_size_{idx_to_edit}_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("櫃號")
                        with col_input: e_cont_sn = st.text_input("", value=current.get("cont_sn", ""),
                                                                  key=f"edit_cont_sn_{idx_to_edit}_{i}",
                                                                  label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("CO Detector")
                        with col_input: e_co_detector = st.text_input("", value=current.get("co_detector", ""),
                                                                      key=f"edit_co_detector_{idx_to_edit}_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Color")
                        with col_input: e_cont_color = st.text_input("", value=current.get("cont_color", ""),
                                                                     key=f"edit_cont_color_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Topone 貼紙")
                        with col_input: e_topone_sticker = st.text_input("", value=current.get("topone_sticker", ""),
                                                                         key=f"edit_topone_sticker_{idx_to_edit}_{i}",
                                                                         label_visibility="collapsed")

                st.markdown("---")

                # ==================== Breaker (斷路器) ====================
                with st.expander("Breaker (斷路器)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: e_breaker_model = st.text_input("", value=current.get("breaker_model", ""),
                                                                        key=f"edit_breaker_model_{idx_to_edit}_{i}",
                                                                        label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Type (類型)")
                        with col_input: e_breaker_type = st.text_input("", value=current.get("breaker_type", ""),
                                                                       key=f"edit_breaker_type_{idx_to_edit}_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Rating")
                        with col_input: e_breaker_rating = st.text_input("", value=current.get("breaker_rating", ""),
                                                                         key=f"edit_breaker_rating_{idx_to_edit}_{i}",
                                                                         label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N")
                        with col_input: e_breaker_sn = st.text_input("", value=current.get("breaker_sn", ""),
                                                                     key=f"edit_breaker_sn_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Gear Motor")
                        with col_input: e_gear_motor = st.text_input("", value=current.get("gear_motor", ""),
                                                                     key=f"edit_gear_motor_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Shunt Trip")
                        with col_input: e_shunt_trip = st.text_input("", value=current.get("shunt_trip", ""),
                                                                     key=f"edit_shunt_trip_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Closing Coil")
                        with col_input: e_closing_coil = st.text_input("", value=current.get("closing_coil", ""),
                                                                       key=f"edit_closing_coil_{idx_to_edit}_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("UV Relay")
                        with col_input: e_uv_relay = st.text_input("", value=current.get("uv_relay", ""),
                                                                   key=f"edit_uv_relay_{idx_to_edit}_{i}",
                                                                   label_visibility="collapsed")

                st.markdown("---")

                # ==================== Control Panel (控制器) ====================
                with st.expander("Control Panel (控制器)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: e_panel_model = st.text_input("", value=current.get("panel_model", ""),
                                                                      key=f"edit_panel_model_{idx_to_edit}_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Module")
                        with col_input: e_panel_module = st.text_input("", value=current.get("panel_module", ""),
                                                                       key=f"edit_panel_module_{idx_to_edit}_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N")
                        with col_input: e_panel_sn = st.text_input("", value=current.get("panel_sn", ""),
                                                                   key=f"edit_panel_sn_{idx_to_edit}_{i}",
                                                                   label_visibility="collapsed")

                st.markdown("---")

                # ==================== Battery (電池) ====================
                with st.expander("Battery (電池)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: e_battery_model = st.text_input("", value=current.get("battery_model", ""),
                                                                        key=f"edit_battery_model_{idx_to_edit}_{i}",
                                                                        label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Battery Switch")
                        with col_input: e_battery_switch = st.text_input("", value=current.get("battery_switch", ""),
                                                                         key=f"edit_battery_switch_{idx_to_edit}_{i}",
                                                                         label_visibility="collapsed")


                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Charger Model")
                        with col_input: e_charger_model = st.text_input("", value=current.get("charger_model", ""),
                                                                        key=f"edit_charger_model_{idx_to_edit}_{i}",
                                                                        label_visibility="collapsed")

                st.markdown("---")

                # ==================== Fuel Tank (燃油箱) ====================
                with st.expander("Fuel Tank (燃油箱)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Volume")
                        with col_input: e_fuel_volume = st.text_input("", value=current.get("fuel_volume", ""),
                                                                      key=f"edit_fuel_volume_{idx_to_edit}_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Layer")
                        with col_input: e_fuel_layer = st.text_input("", value=current.get("fuel_layer", ""),
                                                                     key=f"edit_fuel_layer_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")


                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fuel Level Gauge with level")
                        with col_input: e_fuel_gauge = st.text_input("", value=current.get("fuel_gauge", ""),
                                                                     key=f"edit_fuel_gauge_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fuel Level Switch")
                        with col_input: e_fuel_level_switch = st.text_input("",
                                                                            value=current.get("fuel_level_switch", ""),
                                                                            key=f"edit_fuel_level_switch_{idx_to_edit}_{i}",
                                                                            label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fuel Level Sensor")
                        with col_input: e_fuel_level_sensor = st.text_input("",
                                                                            value=current.get("fuel_level_sensor", ""),
                                                                            key=f"edit_fuel_level_sensor_{idx_to_edit}_{i}",
                                                                            label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Donaldson Breather")
                        with col_input: e_donaldson_breather = st.text_input("", value=current.get("donaldson_breather",
                                                                                                   ""),
                                                                             key=f"edit_donaldson_breather_{idx_to_edit}_{i}",
                                                                             label_visibility="collapsed")
                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("3 way Valve")
                        with col_input: e_three_way_valve = st.text_input("", value=current.get("three_way_valve", ""),
                                                                          key=f"edit_three_way_valve_{idx_to_edit}_{i}",
                                                                          label_visibility="collapsed")

                st.markdown("---")

                # ==================== Oil Tank (機油箱) ====================
                with st.expander("Oil Tank (機油箱)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Volume")
                        with col_input: e_oil_volume = st.text_input("", value=current.get("oil_volume", ""),
                                                                     key=f"edit_oil_volume_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Donaldson Breather")
                        with col_input: e_oil_donaldson = st.text_input("", value=current.get("oil_donaldson", ""),
                                                                        key=f"edit_oil_donaldson_{idx_to_edit}_{i}",
                                                                        label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Murphy Coolant Level Switch")
                        with col_input: e_murphy_oil = st.text_input("", value=current.get("murphy_oil", ""),
                                                                     key=f"edit_murphy_oil_{idx_to_edit}_{i}",
                                                                     label_visibility="collapsed")

                st.markdown("---")

                # ==================== Remarks ====================
                e_remarks = st.text_area("Remarks", value=current.get("remarks", ""), height=150,
                                         key=f"edit_remarks_{idx_to_edit}_{i}")
                # ==================== 收集資料 ====================
                spec_data = {
                    # ==================== 基本資訊 ====================
                    "so_number": e_so_number,
                    "product_category": e_product_category,
                    "product_code": e_product_code,

                    # ==================== Engine ====================
                    "genset_model": e_genset_model,
                    "engine_year": e_engine_year,
                    "genset_sn": e_genset_sn,
                    "engine_color": e_engine_color,
                    "prime_standby": e_prime_standby.strip() if e_prime_standby else "",
                    "rpm": e_rpm.strip(),
                    "voltage": e_voltage.strip(),
                    "frequency": e_frequency.strip(),
                    "engine_heater": e_engine_heater,
                    "coolant_temp_switch": e_coolant_temp_switch,

                    # Engine Option（已全部加入）
                    "coolant_temp_sensor": e_coolant_temp_sensor,
                    "oil_pressure_switch": e_oil_pressure_switch,
                    "coolant_sensor": e_coolant_sensor,
                    "oil_pressure": e_oil_pressure,
                    "hand_pump": e_hand_pump,
                    "silencer": e_silencer,  # ← 已加入
                    "flex_pipe": e_flex_pipe,  # ← 已加入
                    "exhaust_pipe": e_exhaust_pipe,

                    # ==================== Alternator ====================
                    "alt_model": e_alt_model,
                    "alt_winding": e_alt_winding,
                    "droop": e_droop,
                    "alt_color": e_alt_color,
                    "alt_sn": e_alt_sn,
                    "alt_heater": e_alt_heater,
                    "pmg": e_pmg,

                    # ==================== Radiator ====================
                    "rad_model": e_rad_model,
                    "rad_temp": e_rad_temp,
                    "fan_size": e_fan_size,
                    "radiator_guard": e_radiator_guard,
                    "rad_sn": e_rad_sn,
                    "fuel_cooler": e_fuel_cooler,  # ← 新增
                    "low_water": e_low_water,  # ← 新增
                    "murphy_coolant": e_murphy_coolant,
                    "anti_freezer": e_anti_freezer,
                    "radiator_custom1": e_radiator_custom1,
                    "radiator_custom2": e_radiator_custom2,
                    # ==================== Base Frame ====================
                    "base_model": e_base_model,
                    "avm": e_avm,
                    "base_color": e_base_color,
                    "base_sn": e_base_sn,
                    "spring_isolator": e_spring_isolator,

                    # ==================== Container ====================
                    "cont_type": e_cont_type,
                    "cont_size": e_cont_size,
                    "co_detector": e_co_detector,
                    "cont_color": e_cont_color,
                    "cont_sn": e_cont_sn,
                    "topone_sticker": e_topone_sticker,
                    # ==================== Breaker ====================
                    "breaker_model": e_breaker_model,
                    "breaker_type": e_breaker_type,
                    "breaker_rating": e_breaker_rating,
                    "gear_motor": e_gear_motor,  # ← 已加入
                    "shunt_trip": e_shunt_trip,
                    "closing_coil": e_closing_coil,
                    "uv_relay": e_uv_relay,
                    "breaker_sn": e_breaker_sn,

                    # ==================== Control Panel ====================
                    "panel_model": e_panel_model,
                    "panel_module": e_panel_module,
                    "panel_sn": e_panel_sn,

                    # ==================== Battery ====================
                    "battery_model": e_battery_model,
                    "battery_switch": e_battery_switch,
                    "charger_model": e_charger_model,

                    # ==================== Fuel Tank ====================
                    "fuel_volume": e_fuel_volume,
                    "fuel_layer": e_fuel_layer,
                    "fuel_water_separator": e_fuel_water_separator,
                    "fuel_gauge": e_fuel_gauge,
                    "fuel_level_switch": e_fuel_level_switch,
                    "fuel_level_sensor": e_fuel_level_sensor,
                    "donaldson_breather": e_donaldson_breather,
                    "three_way_valve": e_three_way_valve,
                    # ==================== Oil Tank ====================
                    "oil_volume": e_oil_volume,
                    "oil_donaldson": e_oil_donaldson,
                    "murphy_oil": e_murphy_oil,

                    # ==================== Remarks ====================
                    "remarks": e_remarks.strip()
                }
                new_specs.append(spec_data)

        # PDF 匯出 & Save & Close 按鈕（保留原本邏輯）
        if st.button("📄 Export PDF ", type="secondary", use_container_width=True):
            pdf_bytes = generate_overview_pdf(new_specs, row_to_edit, qty)
            st.download_button(
                label="下載 PDF",
                data=pdf_bytes,
                file_name=f"{row_to_edit['Project_Name']}_Overview.pdf",
                mime="application/pdf"
            )

        col_save, col_cancel = st.columns(2)
        with col_save:
            save_disabled = st.session_state.get("edit_saving", False)
            if st.button("Save & Close", type="primary", use_container_width=True, disabled=save_disabled):
                st.session_state.edit_saving = True
                st.rerun()

        with col_cancel:
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state["show_edit_spec_dialog"] = False
                st.session_state.dialog_active = None
                st.rerun()

        if st.session_state.get("edit_saving", False):
            fullscreen_loading("正在儲存規格至 Google Sheets，請稍候...")

            first_spec = new_specs[0] if new_specs else {}
            new_visible = "\n".join([
                f"Genset model: {first_spec.get('genset_model', '—')} | S/N: {first_spec.get('genset_sn', '—')}",
                f"Alternator Model: {first_spec.get('alt_model', '—')} | S/N: {first_spec.get('alt_sn', '—')}"
            ])

            extra_json = json.dumps(new_specs, ensure_ascii=False)
            df.at[idx_to_edit, "Project_Spec"] = new_visible + "||EXTRA||" + extra_json

            save_projects()
            st.cache_data.clear()

            st.success("所有規格已成功更新！")
            st.session_state["show_edit_spec_dialog"] = False
            st.session_state.dialog_active = None
            st.session_state.edit_saving = False
            st.rerun()

    edit_spec_dialog()

# ==============================================
# Project Specification Dialog (新增用) - 已修正
# ==============================================
if st.session_state.get("spec_dialog_open", False):
    if st.session_state.dialog_active != "new_spec":
        st.session_state.dialog_active = "new_spec"
        st.rerun()

    temp_project = st.session_state.temp_project
    qty = temp_project.get("Qty", 1)
    project_type = temp_project["Project_Type"]
    is_open_or_marine = project_type in ["Open Set", "Marine"]

    @st.dialog("Project Specification", width="large")
    def spec_dialog():
        st.markdown(f"**請填寫 {qty} 台機器的規格**")

        st.markdown(
            """
            <style>
            div[data-testid="column"] {
                display: flex !important;
                align-items: center !important;
            }
            div[data-testid="column"] div[data-testid="stTextInput"] > div > div,
            div[data-testid="column"] div[data-testid="stSelectbox"] > div > div {
                width: 100% !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        tabs = st.tabs([f"第 {i+1} 台" for i in range(qty)])

        specs = []
        if qty > 1:
            st.markdown("---")
            st.markdown("### 規格快速複製工具")
            if st.button("📋 從第 1 台複製規格 → 所有其他台",
                         type="primary",
                         use_container_width=True,
                         help="點擊後會把目前第1台已填寫的規格，複製到第2台～最後一台"):

                source_i = 0
                static_fields = [
                    # 基本資訊
                    "so_number", "product_category", "product_code",

                    # Engine Feature
                    "genset_model", "engine_year", "engine_color", "prime_standby",
                    "rpm", "voltage", "frequency", "genset_sn",

                    # Engine Option
                    "coolant_temp_sensor", "coolant_sensor", "oil_pressure", "oil_pressure_switch",
                    "hand_pump", "silencer", "flex_pipe", "exhaust_pipe",
                    "engine_heater", "fuel_water_separator",

                    # Alternator
                    "alt_model", "alt_winding", "alt_color", "alt_sn",
                    "alt_heater", "droop", "pmg",

                    # Radiator
                    "rad_model", "rad_temp", "fan_size", "radiator_guard", "rad_sn",
                    "fuel_cooler", "low_water", "murphy_coolant", "anti_freezer",

                    # Base Frame
                    "base_model", "avm", "base_color", "base_sn",

                    # Container
                    "cont_type", "cont_size", "cont_sn", "co_detector", "cont_color", "topone_sticker",

                    # Breaker
                    "breaker_model", "breaker_type", "breaker_rating", "breaker_sn",
                    "gear_motor", "shunt_trip", "closing_coil", "uv_relay",

                    # Control Panel
                    "panel_model", "panel_module", "panel_sn",

                    # Battery
                    "battery_model", "battery_switch", "charger_model",

                    # Fuel Tank
                    "fuel_volume", "fuel_layer", "fuel_gauge", "fuel_level_switch",
                    "fuel_level_sensor", "donaldson_breather", "three_way_valve",

                    # Oil Tank
                    "oil_volume", "oil_donaldson", "murphy_oil",

                    # Remarks
                    "remarks"
                ]

                for field in static_fields:
                    src_key = f"dlg_{field}_{source_i}"
                    if src_key in st.session_state:
                        value = st.session_state[src_key]
                        for target_i in range(1, qty):
                            target_key = f"dlg_{field}_{target_i}"
                            st.session_state[target_key] = value

                st.success("已成功將第 1 台的規格複製到其他所有台！")
                st.rerun()

        for i in range(qty):
            with tabs[i]:
                # ==================== 基本資訊 (Engine 上方) ====================
                st.markdown("### 基本資訊")

                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                with col1:
                    s_so_number = st.text_input("SO#", key=f"dlg_so_number_{i}")

                with col2:
                    s_product_category = st.text_input("Product Category", key=f"dlg_product_category_{i}")

                with col3:
                    s_product_code = st.text_input("Product Code", key=f"dlg_product_code_{i}")

                with col4:
                    st.markdown("**QTY**")
                    st.markdown(f"<h3 style='margin: 0; color: #1e88e5;'>{qty}</h3>", unsafe_allow_html=True)

                st.markdown("---")
                # ==================== Engine (發動機) ====================
                with st.expander("Engine (發動機)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: s_genset_model = st.text_input("", key=f"dlg_genset_model_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Year (年份)")
                        with col_input: s_engine_year = st.text_input("", key=f"dlg_engine_year_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Colour (顏色)")
                        with col_input: s_engine_color = st.text_input("", key=f"dlg_engine_color_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Prime/Standby (kW)")
                        with col_input: s_prime_standby = st.text_input("", placeholder="例如: 100/110",
                                                                        key=f"dlg_prime_standby_{i}",
                                                                        label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("RPM (轉速)")
                        with col_input: s_rpm = st.text_input("", key=f"dlg_rpm_{i}", label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Voltage (電壓)")
                        with col_input: s_voltage = st.text_input("", key=f"dlg_voltage_{i}",
                                                                  label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Frequency (頻率)")
                        with col_input: s_frequency = st.text_input("", key=f"dlg_frequency_{i}",
                                                                    label_visibility="collapsed")


                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N (序號)")
                        with col_input: s_genset_sn = st.text_input("", key=f"dlg_genset_sn_{i}",
                                                                    label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Coolant temperature sensor")
                        with col_input: s_coolant_temp_sensor = st.text_input("", key=f"dlg_coolant_temp_sensor_{i}",
                                                                              label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Coolant temperature switch")
                        with col_input: s_coolant_temp_switch = st.text_input("", key=f"dlg_coolant_temp_switch_{i}",
                                                                              label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Oil Coolant Temp Sensor")
                        with col_input: s_coolant_sensor = st.text_input("", key=f"dlg_coolant_sensor_{i}",
                                                                         label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Oil Pressure Sensor")
                        with col_input: s_oil_pressure = st.text_input("", key=f"dlg_oil_pressure_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Oil pressure switch")
                        with col_input: s_oil_pressure_switch = st.text_input("", key=f"dlg_oil_pressure_switch_{i}",
                                                                              label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Hand Swing Pump")
                        with col_input: s_hand_pump = st.text_input("", key=f"dlg_hand_pump_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Silencer")
                        with col_input: s_silencer = st.text_input("", key=f"dlg_silencer_{i}",
                                                                   label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Flexible Pipe & Flange")
                        with col_input: s_flex_pipe = st.text_input("", key=f"dlg_flex_pipe_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Exhaust Pipe")
                        with col_input: s_exhaust_pipe = st.text_input("", key=f"dlg_exhaust_pipe_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Heater (加熱器) kW")
                        with col_input: s_engine_heater = st.text_input("", key=f"dlg_engine_heater_{i}",
                                                                        label_visibility="collapsed")
                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fuel Water Separator")
                        with col_input: s_fuel_water_separator = st.text_input("", key=f"dlg_fuel_water_separator_{i}",
                                                                               label_visibility="collapsed")


                st.markdown("---")

                # ==================== Alternator (電球) ====================
                with st.expander("Alternator (電球)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: s_alt_model = st.text_input("", key=f"dlg_alt_model_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Winding")
                        with col_input: s_alt_winding = st.text_input("", key=f"dlg_alt_winding_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Color")
                        with col_input: s_alt_color = st.text_input("", key=f"dlg_alt_color_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N")
                        with col_input: s_alt_sn = st.text_input("", key=f"dlg_alt_sn_{i}",
                                                                 label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Heater")
                        with col_input: s_alt_heater = st.text_input("", key=f"dlg_alt_heater_{i}",
                                                                     label_visibility="collapsed")
                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Droop")
                        with col_input: s_droop = st.text_input("", key=f"dlg_droop_{i}", label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("PMG")
                        with col_input: s_pmg = st.text_input("", key=f"dlg_pmg_{i}", label_visibility="collapsed")

                st.markdown("---")

                # ==================== Radiator (水箱) ====================
                with st.expander("Radiator (水箱)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: s_rad_model = st.text_input("", key=f"dlg_rad_model_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Degree (温度)")
                        with col_input: s_rad_temp = st.text_input("", key=f"dlg_rad_temp_{i}",
                                                                   label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fan Size (扇呎吋)")
                        with col_input: s_fan_size = st.text_input("", key=f"dlg_fan_size_{i}",
                                                                   label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Protection Cover (保護罩)")
                        with col_input: s_radiator_guard = st.text_input("", key=f"dlg_radiator_guard_{i}",
                                                                         label_visibility="collapsed")
                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N")
                        with col_input: s_rad_sn = st.text_input("", key=f"dlg_rad_sn_{i}",
                                                                 label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fuel Cooler")
                        with col_input: s_fuel_cooler = st.text_input("", key=f"dlg_fuel_cooler_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Low Water Level Switch")
                        with col_input: s_low_water = st.text_input("", key=f"dlg_low_water_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Murphy Coolant Level Switch")
                        with col_input: s_murphy_coolant = st.text_input("", key=f"dlg_murphy_coolant_{i}",
                                                                         label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Anti-Freezer")
                        with col_input: s_anti_freezer = st.text_input("", key=f"dlg_anti_freezer_{i}",
                                                                       label_visibility="collapsed")

                        col1, col2 = st.columns(2)
                        with col1:
                            s_radiator_custom1 = st.text_input("",
                                                               key=f"dlg_radiator_custom1_{i}",
                                                               label_visibility="collapsed",
                                                               placeholder="自行輸入 1")
                        with col2:
                            s_radiator_custom2 = st.text_input("",
                                                               key=f"dlg_radiator_custom2_{i}",
                                                               label_visibility="collapsed",
                                                               placeholder="自行輸入 2")

                st.markdown("---")

                # ==================== Base Frame (底架) ====================
                with st.expander("Base Frame (底架)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: s_base_model = st.text_input("", key=f"dlg_base_model_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Anti-Vibration Mounts (避震腳)")
                        with col_input: s_avm = st.text_input("", key=f"dlg_avm_{i}", label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N")
                        with col_input: s_base_sn = st.text_input("", key=f"dlg_base_sn_{i}",
                                                                  label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Color")
                        with col_input: s_base_color = st.text_input("", key=f"dlg_base_color_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Spring isolator")
                        with col_input: s_spring_isolator = st.text_input("", key=f"dlg_spring_isolator_{i}",
                                                                          label_visibility="collapsed")

                st.markdown("---")

                # ==================== Container (貨櫃) ====================
                with st.expander("Container (貨櫃)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Type (型號)")
                        with col_input: s_cont_type = st.text_input("", key=f"dlg_cont_type_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Dimension (呎吋)")
                        with col_input: s_cont_size = st.text_input("", key=f"dlg_cont_size_{i}",
                                                                    label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("櫃號")
                        with col_input: s_cont_sn = st.text_input("", key=f"dlg_cont_sn_{i}",
                                                                  label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("CO Detector")
                        with col_input: s_co_detector = st.text_input("", key=f"dlg_co_detector_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Color")
                        with col_input: s_cont_color = st.text_input("", key=f"dlg_cont_color_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Topone 貼紙")
                        with col_input: s_topone_sticker = st.text_input("", key=f"dlg_topone_sticker_{i}",
                                                                         label_visibility="collapsed")

                st.markdown("---")

                # ==================== Breaker (斷路器) ====================
                with st.expander("Breaker (斷路器)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: s_breaker_model = st.text_input("", key=f"dlg_breaker_model_{i}",
                                                                        label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Type (類型)")
                        with col_input: s_breaker_type = st.text_input("", key=f"dlg_breaker_type_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Rating")
                        with col_input: s_breaker_rating = st.text_input("", key=f"dlg_breaker_rating_{i}",
                                                                         label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N")
                        with col_input: s_breaker_sn = st.text_input("", key=f"dlg_breaker_sn_{i}",
                                                                     label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Gear Motor")
                        with col_input: s_gear_motor = st.text_input("", key=f"dlg_gear_motor_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Shunt Trip")
                        with col_input: s_shunt_trip = st.text_input("", key=f"dlg_shunt_trip_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Closing Coil")
                        with col_input: s_closing_coil = st.text_input("", key=f"dlg_closing_coil_{i}",
                                                                       label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("UV Relay")
                        with col_input: s_uv_relay = st.text_input("", key=f"dlg_uv_relay_{i}",
                                                                   label_visibility="collapsed")

                st.markdown("---")

                # ==================== Control Panel (控制器) ====================
                with st.expander("Control Panel (控制器)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: s_panel_model = st.text_input("", key=f"dlg_panel_model_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Module")
                        with col_input: s_panel_module = st.text_input("", key=f"dlg_panel_module_{i}",
                                                                       label_visibility="collapsed")
                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("S/N")
                        with col_input: s_panel_sn = st.text_input("", key=f"dlg_panel_sn_{i}",
                                                                   label_visibility="collapsed")

                st.markdown("---")

                # ==================== Battery (電池) ====================
                with st.expander("Battery (電池)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Model (型號)")
                        with col_input: s_battery_model = st.text_input("", key=f"dlg_battery_model_{i}",
                                                                        label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Battery Switch")
                        with col_input: s_battery_switch = st.text_input("", key=f"dlg_battery_switch_{i}",
                                                                         label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Charger Model")
                        with col_input: s_charger_model = st.text_input("", key=f"dlg_charger_model_{i}",
                                                                        label_visibility="collapsed")

                st.markdown("---")

                # ==================== Fuel Tank (燃油箱) ====================
                with st.expander("Fuel Tank (燃油箱)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Volume")
                        with col_input: s_fuel_volume = st.text_input("", key=f"dlg_fuel_volume_{i}",
                                                                      label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Layer")
                        with col_input: s_fuel_layer = st.text_input("", key=f"dlg_fuel_layer_{i}",
                                                                     label_visibility="collapsed")


                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fuel Level Gauge with level")
                        with col_input: s_fuel_gauge = st.text_input("", key=f"dlg_fuel_gauge_{i}",
                                                                     label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fuel Level Switch")
                        with col_input: s_fuel_level_switch = st.text_input("", key=f"dlg_fuel_level_switch_{i}",
                                                                            label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Fuel Level Sensor")
                        with col_input: s_fuel_level_sensor = st.text_input("", key=f"dlg_fuel_level_sensor_{i}",
                                                                            label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Donaldson Breather")
                        with col_input: s_donaldson_breather = st.text_input("", key=f"dlg_donaldson_breather_{i}",
                                                                             label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("3 way Valve")
                        with col_input: s_three_way_valve = st.text_input("", key=f"dlg_three_way_valve_{i}",
                                                                          label_visibility="collapsed")

                st.markdown("---")

                # ==================== Oil Tank (機油箱) ====================
                with st.expander("Oil Tank (機油箱)", expanded=True):
                    col_feature, col_option = st.columns([1, 1])

                    with col_feature:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Feature</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Volume")
                        with col_input: s_oil_volume = st.text_input("", key=f"dlg_oil_volume_{i}",
                                                                     label_visibility="collapsed")

                    with col_option:
                        st.markdown("<h4 style='color: #1e88e5; margin-bottom: 10px;'>Option</h4>",
                                    unsafe_allow_html=True)

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Donaldson Breather")
                        with col_input: s_oil_donaldson = st.text_input("", key=f"dlg_oil_donaldson_{i}",
                                                                        label_visibility="collapsed")

                        col_label, col_input = st.columns([2, 3])
                        with col_label: st.markdown("Murphy Coolant Level Switch")
                        with col_input: s_murphy_oil = st.text_input("", key=f"dlg_murphy_oil_{i}",
                                                                     label_visibility="collapsed")

                st.markdown("---")

                # ==================== Remarks ====================
                s_remarks = st.text_area("Remarks", height=150, key=f"dlg_remarks_{i}")

                # ==================== 收集資料 ====================
                spec_data = {
                    # ==================== Engine ====================
                    "genset_model": s_genset_model,
                    "engine_year": s_engine_year,
                    "genset_sn": s_genset_sn,
                    "engine_color": s_engine_color,
                    "prime_standby": s_prime_standby.strip() if 's_prime_standby' in locals() else "",
                    "rpm": s_rpm.strip(),
                    "voltage": s_voltage.strip(),
                    "frequency": s_frequency.strip(),
                    "engine_heater": s_engine_heater,
                    "coolant_temp_switch": s_coolant_temp_switch,

                    # ==================== Alternator ====================
                    "alt_model": s_alt_model,
                    "alt_winding": s_alt_winding,
                    "droop": s_droop,
                    "alt_color": s_alt_color,
                    "alt_sn": s_alt_sn,
                    "alt_heater": s_alt_heater,
                    "pmg": s_pmg,

                    # ==================== Radiator ====================
                    "rad_model": s_rad_model,
                    "rad_temp": s_rad_temp,
                    "fan_size": s_fan_size,
                    "radiator_guard": s_radiator_guard,
                    "fuel_cooler": s_fuel_cooler,
                    "low_water": s_low_water,
                    "murphy_coolant": s_murphy_coolant,
                    "rad_sn": s_rad_sn,
                    "anti_freezer": s_anti_freezer,
                    "radiator_custom1": s_radiator_custom1,
                    "radiator_custom2": s_radiator_custom2,
                    # ==================== Base Frame ====================
                    "base_model": s_base_model,
                    "avm": s_avm,
                    "base_color": s_base_color,
                    "base_sn": s_base_sn,
                    "spring_isolator": s_spring_isolator,
                    # ==================== Container ====================
                    "cont_type": s_cont_type,
                    "cont_size": s_cont_size,
                    "co_detector": s_co_detector,
                    "cont_color": s_cont_color,
                    "cont_sn": s_cont_sn,
                    "topone_sticker": s_topone_sticker,
                    # ==================== Breaker ====================
                    "breaker_model": s_breaker_model,
                    "breaker_type": s_breaker_type,
                    "breaker_rating": s_breaker_rating,
                    "gear_motor": s_gear_motor,
                    "shunt_trip": s_shunt_trip,
                    "closing_coil": s_closing_coil,
                    "uv_relay": s_uv_relay,
                    "breaker_sn": s_breaker_sn,
                    # ==================== Control Panel ====================
                    "panel_model": s_panel_model,
                    "panel_module": s_panel_module,
                    "panel_sn": s_panel_sn,
                    # ==================== Battery ====================
                    "battery_model": s_battery_model,
                    "battery_switch": s_battery_switch,
                    "charger_model": s_charger_model,

                    # ==================== Fuel Tank ====================
                    "fuel_volume": s_fuel_volume,
                    "fuel_layer": s_fuel_layer,
                    "fuel_water_separator": s_fuel_water_separator,
                    "fuel_gauge": s_fuel_gauge,
                    "fuel_level_switch": s_fuel_level_switch,
                    "fuel_level_sensor": s_fuel_level_sensor,
                    "donaldson_breather": s_donaldson_breather,
                    "three_way_valve": s_three_way_valve,

                    # ==================== Oil Tank ====================
                    "oil_volume": s_oil_volume,
                    "oil_donaldson": s_oil_donaldson,
                    "murphy_oil": s_murphy_oil,
                    "coolant_temp_sensor": s_coolant_temp_sensor,
                    "oil_pressure_switch": s_oil_pressure_switch,
                    # ==================== Remarks ====================
                    "remarks": s_remarks.strip(),
                    "so_number": s_so_number,
                    "product_category": s_product_category,
                    "product_code": s_product_code,
                    "qty": qty  # 固定數量
                }
                specs.append(spec_data)
        # PDF 按鈕
        if st.button("📄 Export PDF", type="secondary", use_container_width=True):
            pdf_bytes = generate_overview_pdf(specs, temp_project, qty)
            st.download_button("下載 PDF", data=pdf_bytes, file_name=f"{temp_project['Project_Name']}_Overview.pdf", mime="application/pdf")

        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("Save & Close", type="primary", use_container_width=True):
                st.session_state.new_spec_saving = True
                st.rerun()

        with col_cancel:
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state.spec_dialog_open = False
                st.session_state.dialog_active = None
                if "temp_project" in st.session_state:
                    del st.session_state.temp_project
                st.rerun()

        # ==================== 儲存邏輯 ====================
        if st.session_state.get("new_spec_saving", False):
            fullscreen_loading("正在新增專案並儲存規格，請稍候...")

            first_spec = specs[0] if specs else {}
            visible_lines = [
                f"Genset model: {first_spec.get('genset_model', '—')} | S/N: {first_spec.get('genset_sn', '—')}",
                f"Alternator Model: {first_spec.get('alt_model', '—')} | S/N: {first_spec.get('alt_sn', '—')}"
            ]
            extra_json = json.dumps(specs, ensure_ascii=False)
            spec_text = "\n".join(visible_lines) + "||EXTRA||" + extra_json

            new_project = {**temp_project, "Project_Spec": spec_text}

            global df
            df = pd.concat([df, pd.DataFrame([new_project])], ignore_index=True)

            save_projects()
            st.cache_data.clear()

            st.success(f"已成功新增專案（{qty} 台機器）！")
            if "temp_project" in st.session_state:
                del st.session_state.temp_project
            st.session_state.spec_dialog_open = False
            st.session_state.dialog_active = None
            st.session_state.new_spec_saving = False
            st.rerun()

    spec_dialog()

# Edit Project Info Dialog
if st.session_state.get("show_edit_info_dialog", False):
    if st.session_state.dialog_active != "edit_info":
        st.session_state.dialog_active = "edit_info"
        st.rerun()

    idx_to_edit = st.session_state["current_edit_idx"]
    row_to_edit = df.loc[idx_to_edit]

    @st.dialog("Edit Project Info", width="large")
    def edit_info_dialog():
        st.markdown(f"**Editing Basic Info for: {row_to_edit['Project_Name']}**")

        col1, col2 = st.columns(2)
        with col1:
            e_type = st.selectbox("Project Type*", ["Enclosure","Open Set","Scania","Marine","K50G3"],
                                  index=["Enclosure","Open Set","Scania","Marine","K50G3"].index(row_to_edit["Project_Type"]),
                                  key=f"edit_info_type_{idx_to_edit}")
            e_name = st.text_input("Project Name*", value=row_to_edit["Project_Name"], key=f"edit_info_name_{idx_to_edit}")
            e_year = st.selectbox("Year*", [2024,2025,2026], index=[2024,2025,2026].index(row_to_edit["Year"]), key=f"edit_info_year_{idx_to_edit}")
            e_qty = st.number_input("Qty", min_value=1, value=int(row_to_edit["Qty"]), key=f"edit_info_qty_{idx_to_edit}")
        with col2:
            e_customer = st.text_input("Customer", value=row_to_edit.get("Customer", ""), key=f"edit_info_customer_{idx_to_edit}")
            e_supervisor = st.text_input("Supervisor", value=row_to_edit.get("Supervisor", ""), key=f"edit_info_supervisor_{idx_to_edit}")
            e_leadtime = st.date_input("Lead Time*", value=row_to_edit["Lead_Time"], key=f"edit_info_leadtime_{idx_to_edit}")

        st.markdown("**Progress Dates**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            parts_val = None if pd.isna(row_to_edit.get("Parts_Arrival")) else row_to_edit["Parts_Arrival"]
            e_parts_arrival = st.date_input("Parts Arrival", value=parts_val, key=f"edit_info_parts_{idx_to_edit}")

            install_val = None if pd.isna(row_to_edit.get("Installation_Complete")) else row_to_edit["Installation_Complete"]
            e_install_complete = st.date_input("Installation Complete", value=install_val, key=f"edit_info_install_{idx_to_edit}")

            testing_val = None if pd.isna(row_to_edit.get("Testing_Complete")) else row_to_edit["Testing_Complete"]
            e_testing_complete = st.date_input("Testing Complete", value=testing_val, key=f"edit_info_testing_{idx_to_edit}")
        with col_d2:
            cleaning_val = None if pd.isna(row_to_edit.get("Cleaning_Complete")) else row_to_edit["Cleaning_Complete"]
            e_cleaning_complete = st.date_input("Cleaning Complete", value=cleaning_val, key=f"edit_info_cleaning_{idx_to_edit}")

            delivery_val = None if pd.isna(row_to_edit.get("Delivery_Complete")) else row_to_edit["Delivery_Complete"]
            e_delivery_complete = st.date_input("Delivery Complete", value=delivery_val, key=f"edit_info_delivery_{idx_to_edit}")

        e_reminder = st.text_input("Progress Reminder (顯示在進度條中間)", value=row_to_edit.get("Progress_Reminder", ""), key=f"edit_info_reminder_{idx_to_edit}")

        col_save, col_cancel = st.columns(2)
        with col_save:
            save_disabled = st.session_state.get("edit_info_saving", False)
            if st.button("Save & Close", type="primary", use_container_width=True, disabled=save_disabled):
                st.session_state.edit_info_saving = True
                st.rerun()

            if st.session_state.get("edit_info_saving", False):
                fullscreen_loading("正在儲存基本資訊，請稍候...")

                if not e_name.strip():
                    st.error("Project Name required!")
                elif e_name != row_to_edit["Project_Name"] and e_name in df["Project_Name"].values:
                    st.error("Name exists!")
                else:
                    df.at[idx_to_edit, "Project_Type"] = e_type
                    df.at[idx_to_edit, "Project_Name"] = e_name
                    df.at[idx_to_edit, "Year"] = int(e_year)
                    df.at[idx_to_edit, "Customer"] = e_customer
                    df.at[idx_to_edit, "Supervisor"] = e_supervisor
                    df.at[idx_to_edit, "Qty"] = e_qty
                    df.at[idx_to_edit, "Real_Count"] = e_qty
                    df.at[idx_to_edit, "Progress_Reminder"] = e_reminder

                    # ←←← 關鍵修正：全部轉成 pd.to_datetime
                    df.at[idx_to_edit, "Lead_Time"] = pd.to_datetime(e_leadtime) if e_leadtime is not None else pd.NaT
                    df.at[idx_to_edit, "Parts_Arrival"] = pd.to_datetime(
                        e_parts_arrival) if e_parts_arrival is not None else pd.NaT
                    df.at[idx_to_edit, "Installation_Complete"] = pd.to_datetime(
                        e_install_complete) if e_install_complete is not None else pd.NaT
                    df.at[idx_to_edit, "Testing_Complete"] = pd.to_datetime(
                        e_testing_complete) if e_testing_complete is not None else pd.NaT
                    df.at[idx_to_edit, "Cleaning_Complete"] = pd.to_datetime(
                        e_cleaning_complete) if e_cleaning_complete is not None else pd.NaT
                    df.at[idx_to_edit, "Delivery_Complete"] = pd.to_datetime(
                        e_delivery_complete) if e_delivery_complete is not None else pd.NaT

                    save_projects()
                    st.cache_data.clear()

                    st.success("基本資訊已成功更新！")
                    st.session_state["show_edit_info_dialog"] = False
                    st.session_state.edit_info_saving = False
                    st.rerun()
    edit_info_dialog()

# Sidebar & 主畫面
with st.sidebar:
    st.header("View Controls")
    if st.button("All Projects", use_container_width=True, type="primary", key="btn_all"):
        st.session_state.view_mode = "all"
        st.rerun()
    if st.button("Delay Projects", use_container_width=True, type="secondary", key="btn_delay"):
        st.session_state.view_mode = "delay"
        st.rerun()
    if st.button("📅Calendar", use_container_width=True, type="primary", key="btn_calendar"):
        st.session_state.view_mode = "calendar"
        st.rerun()
    if st.button("📊 Analysis", type="primary", use_container_width=True, key="analysis_btn"):
        st.session_state["show_analysis"] = True

    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "all"

    st.markdown("---")
    st.markdown("### Search Project Name / Customer Name")
    search_term = st.text_input(
        "輸入專案名稱 或 客戶名稱 (部分匹配)",
        value="",
        key="search_input",
        label_visibility="collapsed"
    )

    st.markdown("---")

    project_types = ["All", "Enclosure", "Open Set", "Scania", "Marine", "K50G3"]
    years = [2024, 2025, 2026]
    month_names = ["All", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    if st.session_state.view_mode == "all":
        st.markdown("### Filters")

        default_type = st.session_state.get("last_filter_type", "All")
        default_year = st.session_state.get("last_filter_year", date.today().year)
        default_month = st.session_state.get("last_filter_month", "All")

        selected_type = st.selectbox(
            "Project Type",
            project_types,
            index=project_types.index(default_type),
            key="global_filter_type"
        )
        selected_year = st.selectbox(
            "Year",
            years,
            index=years.index(default_year),
            key="global_filter_year"
        )
        selected_month = st.selectbox(
            "Month",
            month_names,
            index=month_names.index(default_month),
            key="global_filter_month"
        )

        st.session_state.last_filter_type = selected_type
        st.session_state.last_filter_year = selected_year
        st.session_state.last_filter_month = selected_month
    else:
        selected_type = "All"
        selected_year = date.today().year
        selected_month = "All"

    st.markdown("---")
    st.header("New Project")

    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_type = st.selectbox("Project Type*", ["Enclosure","Open Set","Scania","Marine","K50G3"], key="new_type")
            new_name = st.text_input("Project Name*", key="new_name")
            new_year = st.selectbox("Year*", [2024,2025,2026], index=2, key="new_year")
            new_qty = st.number_input("Qty", min_value=1, value=1, key="new_qty")
        with c2:
            new_customer = st.text_input("Customer", key="new_customer")
            new_supervisor = st.text_input("Supervisor", key="new_supervisor")
            new_leadtime = st.date_input("Lead Time*", value=date.today(), key="new_leadtime")

        st.markdown("**Progress Dates**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            d1 = st.date_input("Parts Arrival", value=None, key="d1")
            d2 = st.date_input("Installation Complete", value=None, key="d2")
            d3 = st.date_input("Testing Complete", value=None, key="d3")
        with col_d2:
            d4 = st.date_input("Cleaning Complete", value=None, key="d4")
            d5 = st.date_input("Delivery Complete", value=None, key="d5")

        reminder = st.text_input("Progress Reminder (顯示在進度條中間)", placeholder="例如：等緊報價 / 生產中 / 已發貨", key="reminder")

        if st.form_submit_button("Add", type="primary", use_container_width=True):
            if not new_name.strip():
                st.error("Project Name required!")
            elif new_name in df["Project_Name"].values:
                st.error("Name exists!")
            else:
                st.session_state.temp_project = {
                    "Project_Type": new_type,
                    "Project_Name": new_name,
                    "Year": int(new_year),
                    "Lead_Time": new_leadtime,
                    "Customer": new_customer or "",
                    "Supervisor": new_supervisor or "",
                    "Qty": new_qty,
                    "Real_Count": new_qty,
                    "Progress_Reminder": reminder or "",
                    "Parts_Arrival": d1 if d1 else None,
                    "Installation_Complete": d2 if d2 else None,
                    "Testing_Complete": d3 if d3 else None,
                    "Cleaning_Complete": d4 if d4 else None,
                    "Delivery_Complete": d5 if d5 else None
                }

                # 清除所有舊的 parts 和 delivery_checklist session_state
                # 避免下次新專案帶入舊資料
                for key in list(st.session_state.keys()):
                    if key.startswith("dlg_parts_") or key.startswith("dlg_delivery_checklist_"):
                        del st.session_state[key]

                st.session_state.spec_dialog_open = True
                st.rerun()

# 篩選邏輯 & 主畫面
today = date.today()
filtered_df = df.copy()

has_search = search_term.strip() != ""
if has_search:
    search_term_lower = search_term.strip().lower()

    # 建立 mask：Project_Name 或 Customer 任一欄位包含搜尋詞
    mask_project = filtered_df["Project_Name"].str.lower().str.contains(search_term_lower, na=False)
    mask_customer = filtered_df.get("Customer", pd.Series([""] * len(filtered_df), index=filtered_df.index)) \
        .str.lower().str.contains(search_term_lower, na=False)

    filtered_df = filtered_df[mask_project | mask_customer]

if st.session_state.view_mode == "delay":
    filtered_df = filtered_df[
        filtered_df["Lead_Time"].notna() &
        (filtered_df["Lead_Time"] < pd.Timestamp(today)) &
        (filtered_df.apply(calculate_progress, axis=1) < 100)
    ]
    page_title = "Delay Projects"
else:
    if not has_search:
        if selected_type != "All":
            filtered_df = filtered_df[filtered_df["Project_Type"] == selected_type]
        filtered_df = filtered_df[filtered_df["Year"] == selected_year]
        if selected_month != "All":
            month_map = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
            filtered_df = filtered_df[
                filtered_df["Lead_Time"].notna() &
                (filtered_df["Lead_Time"].dt.month == month_map[selected_month])
            ]
    page_title = "YIP SHING Project Dashboard"

if st.session_state.view_mode == "calendar":
    st.title("🗓️ 專案日曆視圖 - 拖曳或點擊即可修改進度日期")

    events = []

    for idx, proj in df.iterrows():
        project_name = proj["Project_Name"]

        if pd.notna(proj["Parts_Arrival"]):
            events.append({
                "id": f"parts_{idx}",
                "title": f"🟢 零件到貨: {project_name}",
                "start": proj["Parts_Arrival"].strftime("%Y-%m-%d"),
                "backgroundColor": "#a8e6cf",
                "borderColor": "#a8e6cf",
                "textColor": "black",
            })

        if pd.notna(proj["Installation_Complete"]):
            events.append({
                "id": f"install_{idx}",
                "title": f"🟡 安裝完成: {project_name}",
                "start": proj["Installation_Complete"].strftime("%Y-%m-%d"),
                "backgroundColor": "#ffd93d",
                "borderColor": "#ffd93d",
                "textColor": "black",
            })

        if pd.notna(proj["Testing_Complete"]):
            events.append({
                "id": f"testing_{idx}",
                "title": f"🟠 測試完成: {project_name}",
                "start": proj["Testing_Complete"].strftime("%Y-%m-%d"),
                "backgroundColor": "#ff9f89",
                "borderColor": "#ff9f89",
                "textColor": "black",
            })

        if pd.notna(proj["Cleaning_Complete"]):
            events.append({
                "id": f"cleaning_{idx}",
                "title": f"🟢 清潔完成: {project_name}",
                "start": proj["Cleaning_Complete"].strftime("%Y-%m-%d"),
                "backgroundColor": "#6bcf7f",
                "borderColor": "#6bcf7f",
                "textColor": "black",
            })

        if pd.notna(proj["Delivery_Complete"]):
            events.append({
                "id": f"delivery_{idx}",
                "title": f"🔴 交付完成: {project_name}",
                "start": proj["Delivery_Complete"].strftime("%Y-%m-%d"),
                "backgroundColor": "#ff6b6b",
                "borderColor": "#ff6b6b",
                "textColor": "white",
            })

    try:
        manpower_raw = worksheet_manpower.get_all_records()
        manpower_df = pd.DataFrame(manpower_raw)
        if not manpower_df.empty:
            manpower_df["Quote_Number"] = manpower_df["Quote_Number"].astype(str).str.replace(r"\.0$", "", regex=True)
            manpower_df["Start_Date"] = pd.to_datetime(manpower_df["Start_Date"], errors="coerce")
            manpower_df["End_Date"] = pd.to_datetime(manpower_df["End_Date"], errors="coerce")

            # debug：顯示筆數與資料
            st.write("借調總筆數：", len(manpower_df))
            if len(manpower_df) > 0:
                st.write("最新借調預覽：")
                st.dataframe(manpower_df.tail(3))  # 看最後幾筆

            for _, rec in manpower_df.iterrows():
                quote_num = rec.get("Quote_Number", "未知專案")
                staff = rec.get("Staff", "未知員工")
                start_date = rec.get("Start_Date")
                end_date = rec.get("End_Date")

                if pd.notna(start_date):
                    events.append({
                        "title": f"🧑‍🔧 派工開始: {staff} @ {quote_num}",
                        "start": start_date.strftime("%Y-%m-%d"),
                        "backgroundColor": "#9d8aff",
                        "borderColor": "#9d8aff",
                        "textColor": "white",
                    })

                if pd.notna(end_date):
                    events.append({
                        "title": f"🧑‍🔧 派工結束: {staff} @ {quote_num}",
                        "start": end_date.strftime("%Y-%m-%d"),
                        "backgroundColor": "#c0a0ff",
                        "borderColor": "#c0a0ff",
                        "textColor": "black",
                    })
    except Exception as e:
        st.error(f"讀取 manpower 失敗：{e}")

    calendar_options = {
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        },
        "height": "800px",
        "locale": "zh-hk",
        "editable": "true",
        "selectable": "true",
        "dayMaxEvents": "true",
    }

    state = calendar(events=events, options=calendar_options, key="stable_project_calendar")

    if state.get("eventDrop"):
        event = state["eventDrop"]["event"]
        event_id = event["id"]
        new_date = event["start"][:10]

        if "_" in event_id:
            field_key, idx_str = event_id.split("_", 1)
            idx = int(idx_str)
            field_map = {
                "parts": "Parts_Arrival",
                "install": "Installation_Complete",
                "testing": "Testing_Complete",
                "cleaning": "Cleaning_Complete",
                "delivery": "Delivery_Complete",
            }
            field = field_map.get(field_key)
            if field and idx in df.index:
                df.at[idx, field] = pd.to_datetime(new_date)
                save_projects()
                st.cache_data.clear()
                st.success(f"已拖曳更新「{df.at[idx, 'Project_Name']}」的 {field.replace('_', ' ')} 為 {new_date}")
                st.rerun()

    if state.get("eventClick"):
        event = state["eventClick"]["event"]
        event_id = event["id"]

        if "_" in event_id:
            field_key, idx_str = event_id.split("_", 1)
            idx = int(idx_str)
            field_map = {
                "parts": "零件到貨",
                "install": "安裝完成",
                "testing": "測試完成",
                "cleaning": "清潔完成",
                "delivery": "交付完成",
            }
            field_name = field_map.get(field_key)
            project_name = df.at[idx, "Project_Name"]

            st.subheader(f"修改專案進度：{project_name} - {field_name}")

            current_date = pd.to_datetime(event["start"][:10]).date()
            new_date = st.date_input("選擇新日期", value=current_date, key=f"edit_date_{event_id}")

            if st.button("確認更新", type="primary", key=f"save_date_{event_id}"):
                field_db_map = {
                    "parts": "Parts_Arrival",
                    "install": "Installation_Complete",
                    "testing": "Testing_Complete",
                    "cleaning": "Cleaning_Complete",
                    "delivery": "Delivery_Complete",
                }
                db_field = field_db_map.get(field_key)
                if db_field:
                    old_date = df.at[idx, db_field]
                    df.at[idx, db_field] = pd.to_datetime(new_date)
                    save_projects()
                    st.cache_data.clear()
                    st.success(
                        f"已更新「{project_name}」的 {field_name} 從 {old_date.date() if pd.notna(old_date) else '無'} → {new_date}")
                    st.rerun()

    st.caption("🗓️ 操作說明：拖曳事件直接調整日期 | 點擊事件修改日期 | 所有變更即時儲存到 Google Sheets")
    st.stop()

st.markdown(f"<h1 style='text-align: center; color: #1fb429; margin-bottom: 30px; font-weight: bold;'>{page_title}</h1>", unsafe_allow_html=True)

if len(filtered_df) == 0:
    if st.session_state.view_mode == "delay":
        st.success("No delay projects! All on time!")
    else:
        st.info("No projects match the selected filters or search term.")
else:
    progress_series = filtered_df.apply(calculate_progress, axis=1)
    filtered_df = filtered_df.assign(Progress=progress_series).sort_values(by="Progress", ascending=False).drop(columns="Progress")

    counter = filtered_df.groupby("Project_Type")["Qty"].sum().astype(int).sort_index()
    total_qty = int(filtered_df["Qty"].sum())
    st.markdown(f"""
    <div style="position:fixed; top:70px; right:20px; background:#1e3a8a; color:white; padding:12px 18px; 
                border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.3); z-index:1000; font-size:0.9rem; text-align:center;">
        <strong style="font-size:1.1rem;">Total: {total_qty}</strong><br>
        {"<br>".join([f"<strong>{k}:</strong> {v}" for k, v in counter.items()])}
    </div>
    """, unsafe_allow_html=True)

    # 先按照 Lead_Time 排序（從早到晚）
    filtered_df = filtered_df.sort_values(by='Lead_Time', ascending=True)  # ascending=True: 最早日期先顯示

    # 轉成 records
    rows = filtered_df.to_dict('records')

    # 兩列顯示卡片（保持原樣）
    for i in range(0, len(rows), 2):
        col1, col2 = st.columns(2)
        with col1:
            if i < len(rows):
                render_project_card(rows[i], filtered_df.index[i])
        with col2:
            if i + 1 < len(rows):
                render_project_card(rows[i + 1], filtered_df.index[i + 1])

# ==================== OverView Dialog（最外層） ====================
if st.session_state.get("show_overview_dialog", False):
    row = st.session_state.get("overview_row")
    qty = st.session_state.get("overview_qty", 1)

    @st.dialog(f"完整規格總覽 – {row['Project_Name']} ({qty} 台)", width="large")
    def overall_spec_overview():
        st.markdown(f"**專案：{row['Project_Name']}**　｜　**{qty} 台**　｜　**類型：{row['Project_Type']}**")
        st.markdown("---")

        spec_text = row.get("Project_Spec", "")
        specs = []
        if "||EXTRA||" in spec_text:
            try:
                extra_json = spec_text.split("||EXTRA||")[1]
                specs = json.loads(extra_json)
                if not isinstance(specs, list):
                    specs = [specs]
            except:
                specs = []
        else:
            specs = []

        if len(specs) < qty:
            specs += [{}] * (qty - len(specs))

        overview_tabs = st.tabs([f"第 {i + 1} 台" for i in range(qty)])

        for machine_idx in range(qty):
            with overview_tabs[machine_idx]:
                spec = specs[machine_idx] if machine_idx < len(specs) else {}

                st.subheader("基本資訊")
                st.markdown(f"**SO#：** {spec.get('so_number', '—')}　　**Product Category：** {spec.get('product_category', '—')}　　**Product Code：** {spec.get('product_code', '—')}")

                st.divider()

                st.markdown("**Engine (發動機)**")
                st.markdown(f"**Model (型號)：** {spec.get('genset_model', '—')}　　**S/N：** {spec.get('genset_sn', '—')}")
                st.markdown(f"**Year (年份)：** {spec.get('engine_year', '—')}　　**Colour (顏色)：** {spec.get('engine_color', '—')}")
                st.markdown(f"**Prime/Standby (kW)：** {spec.get('prime_standby', '—')}　　**RPM：** {spec.get('rpm', '—')}")
                st.markdown(f"**Voltage (電壓)：** {spec.get('voltage', '—')}　　**Frequency (頻率)：** {spec.get('frequency', '—')}")
                st.markdown(f"**Heater (加熱器) kW：** {spec.get('engine_heater', '—')}")

                st.divider()

                st.markdown("**Alternator (電球)**")
                st.markdown(f"**Model (型號)：** {spec.get('alt_model', '—')}　　**S/N：** {spec.get('alt_sn', '—')}")
                st.markdown(f"**Winding：** {spec.get('alt_winding', '—')}　　**Color：** {spec.get('alt_color', '—')}")
                st.markdown(f"**Droop：** {spec.get('droop', '—')}　　**PMG：** {spec.get('pmg', '—')}　　**Heater：** {spec.get('alt_heater', '—')}")

                st.divider()

                st.markdown("**Radiator (水箱)**")
                st.markdown(f"**Model (型號)：** {spec.get('rad_model', '—')}　　**S/N：** {spec.get('rad_sn', '—')}")
                st.markdown(f"**Degree (温度)：** {spec.get('rad_temp', '—')}　　**Fan Size：** {spec.get('fan_size', '—')}")
                st.markdown(f"**Protection Cover：** {spec.get('radiator_guard', '—')}")

                st.divider()

                st.markdown("**Base Frame (底架)**")
                st.markdown(f"**Model (型號)：** {spec.get('base_model', '—')}　　**S/N：** {spec.get('base_sn', '—')}")
                st.markdown(f"**Anti-Vibration Mounts：** {spec.get('avm', '—')}　　**Color：** {spec.get('base_color', '—')}")

                st.divider()

                st.markdown("**Container (貨櫃)**")
                st.markdown(f"**Type (型號)：** {spec.get('cont_type', '—')}　　**Dimension：** {spec.get('cont_size', '—')}")
                st.markdown(f"**櫃號：** {spec.get('cont_sn', '—')}　　**Color：** {spec.get('cont_color', '—')}")

                st.divider()

                st.markdown("**Breaker (斷路器)**")
                st.markdown(f"**Model (型號)：** {spec.get('breaker_model', '—')}　　**Type：** {spec.get('breaker_type', '—')}　　**Rating：** {spec.get('breaker_rating', '—')}")
                st.markdown(f"**S/N：** {spec.get('breaker_sn', '—')}")

                st.divider()

                st.markdown("**Control Panel (控制器)**")
                st.markdown(f"**Model (型號)：** {spec.get('panel_model', '—')}　　**Module：** {spec.get('panel_module', '—')}　　**S/N：** {spec.get('panel_sn', '—')}")

                st.divider()

                st.markdown("**Battery (電池)**")
                st.markdown(f"**Model (型號)：** {spec.get('battery_model', '—')}　　**Rating：** {spec.get('battery_rating', '—')}")

                st.markdown("**Fuel Tank (燃油箱)**")
                st.markdown(f"**Volume：** {spec.get('fuel_volume', '—')}　　**Layer：** {spec.get('fuel_layer', '—')}")

                st.markdown("**Oil Tank (機油箱)**")
                st.markdown(f"**Volume：** {spec.get('oil_volume', '—')}")

                remarks = spec.get("remarks", "").strip()
                if remarks:
                    st.divider()
                    st.subheader("Remarks / 備註")
                    st.info(remarks)

                # ==================== PDF 下載按鈕 + 關閉按鈕（已加唯一 key） ====================
                st.markdown("---")
                col_pdf, col_close = st.columns(2)
                with col_pdf:
                    if st.button("📄 下載 PDF 版本",
                                 key=f"pdf_download_{row['Project_Name']}_{machine_idx}",
                                 type="primary", use_container_width=True):
                        pdf_bytes = generate_overview_pdf(specs, row, qty)
                        st.download_button(
                            label="點擊下載 PDF",
                            data=pdf_bytes,
                            file_name=f"{row['Project_Name']}_JobDetail.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                with col_close:
                    if st.button("關閉",
                                 key=f"close_overview_{row['Project_Name']}_{machine_idx}",
                                 type="secondary", use_container_width=True):
                        st.rerun()

    overall_spec_overview()

    # 關閉 dialog 後清除狀態
    st.session_state["show_overview_dialog"] = False
st.markdown("---")
st.caption("Projects Management System")
