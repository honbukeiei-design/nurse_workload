import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
import json
import requests
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(
    page_title="看護業務 記録アプリ",
    layout="wide"
)

APP_PASSWORD = st.secrets["APP_PASSWORD"]
APPS_SCRIPT_URL = st.secrets["APPS_SCRIPT_URL"]

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("看護業務 記録アプリ")

    password = st.text_input("パスワードを入力してください", type="password")

    if st.button("ログイン"):
        if password == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("パスワードが違います")

    st.stop()

SAVE_DIR = Path("data")
SAVE_DIR.mkdir(parents=True, exist_ok=True)
DRAFT_FILE = SAVE_DIR / "nurse_draft.json"

TASK_TYPES = [
    "食事", "排泄", "清潔", "安全", "安楽",
    "入院環境の整備", "自立の援助", "患者の移送・移動",
    "患者及び家族との連絡相談", "終末看護処置",
    "準備・後片付け", "入院当日に関わる業務",
    "退院準備に関わるもの", "指示受け・報告", "測定",
    "呼吸・循環管理", "治療・診察の介助",
    "諸検査の介助及び検体採取", "与薬（注射）",
    "与薬（注射を除く）", "看護計画・記録",
    "その他の記録", "看護師間の報告・引継ぎ",
    "病棟管理に関する記録作成", "薬剤業務・薬品管理",
    "滅菌物・消耗品の管理", "機器・機材の管理",
    "病室以外の環境整備", "病棟外の連絡", "事務業務",
    "物品搬送業務", "職員の勤務及び調整",
    "看護学生・職員の指導", "教育・研修参加",
    "会議", "職員の健康管理", "助産師業務", "その他",
]

TIME_SLOTS = [
    f"{hour:02d}:{minute:02d}"
    for hour in range(24)
    for minute in [0, 15, 30, 45]
]

def send_to_google_sheet(records):
    response = requests.post(
        APPS_SCRIPT_URL,
        json={"records": records},
        timeout=30
    )
    response.raise_for_status()

    try:
        return response.json()
    except Exception:
        return {
            "status": "unknown",
            "message": response.text
        }

def save_draft():
    draft = {
        "ward_name": st.session_state.get("ward_name", ""),
        "nurse_id": st.session_state.get("nurse_id", ""),
        "timeline_data": st.session_state.get("timeline_data", {}),
    }

    with open(DRAFT_FILE, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False)

def load_draft():
    if DRAFT_FILE.exists():
        with open(DRAFT_FILE, "r", encoding="utf-8") as f:
            draft = json.load(f)

        for key, value in draft.items():
            st.session_state[key] = value

def delete_draft():
    if DRAFT_FILE.exists():
        DRAFT_FILE.unlink()

def next_time_label(start):
    hour, minute = map(int, start.split(":"))
    minute += 15

    if minute == 60:
        minute = 0
        hour += 1

    if hour >= 24:
        return "24:00"

    return f"{hour:02d}:{minute:02d}"

def build_records(timeline_data, ward_name, nurse_id, selected_date):
    records = []

    for task, times in timeline_data.items():
        for start_label in sorted(times):
            records.append({
                "病棟名称": ward_name,
                "日付": selected_date.isoformat(),
                "看護師ID": nurse_id,
                "開始": start_label,
                "終了": next_time_label(start_label),
                "業務種別": task,
                "この業務に割り当てた時間(分)": 15
            })

    return records

if "draft_loaded" not in st.session_state:
    load_draft()
    st.session_state["draft_loaded"] = True

if "timeline_data" not in st.session_state:
    st.session_state["timeline_data"] = {}

st.title("看護業務 記録アプリ")

col_a, col_b, col_c = st.columns(3)

with col_a:
    ward_name = st.text_input(
        "病棟名称",
        value=st.session_state.get("ward_name", "")
    )

with col_b:
    nurse_id = st.text_input(
        "看護師ID",
        value=st.session_state.get("nurse_id", "")
    )

with col_c:
    selected_date = st.date_input("日付", value=date.today())

st.session_state["ward_name"] = ward_name
st.session_state["nurse_id"] = nurse_id

st.info("業務行をクリック、マウスでドラッグ、またはスマホ・タブレットで指でなぞって入力できます。")

# ==================================================
# 固定操作ボタン
# ==================================================
st.markdown(
    """
    <style>
    div[data-testid="stHorizontalBlock"]:has(button) {
        position: sticky;
        top: 0;
        background: white;
        z-index: 999;
        padding: 8px 0;
        border-bottom: 1px solid #ddd;
    }
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    reflect_clicked = st.button("入力内容を反映", use_container_width=True)

with col2:
    clear_clicked = st.button("全消去", use_container_width=True)

with col3:
    save_clicked = st.button("途中保存", use_container_width=True)

with col4:
    load_clicked = st.button("途中保存読込", use_container_width=True)

with col5:
    delete_clicked = st.button("途中保存削除", use_container_width=True)

storage_key = f"nursing_timeline_{selected_date.isoformat()}_{nurse_id or 'no_id'}"

if clear_clicked:
    st.session_state["timeline_data"] = {}
    streamlit_js_eval(
        js_expressions=f"localStorage.removeItem('{storage_key}');",
        key="clear_storage"
    )
    st.success("入力内容を全消去しました")
    st.rerun()

if reflect_clicked:
    stored_json = streamlit_js_eval(
        js_expressions=f"localStorage.getItem('{storage_key}')",
        key="get_timeline_data"
    )

    if stored_json:
        try:
            st.session_state["timeline_data"] = json.loads(stored_json)
            st.success("入力内容を反映しました")
        except Exception:
            st.error("入力内容の読込に失敗しました")
    else:
        st.session_state["timeline_data"] = {}
        st.warning("反映できる入力内容がありません")

if save_clicked:
    stored_json = streamlit_js_eval(
        js_expressions=f"localStorage.getItem('{storage_key}')",
        key="get_timeline_for_save"
    )

    if stored_json:
        st.session_state["timeline_data"] = json.loads(stored_json)

    save_draft()
    st.success("途中保存しました")

if load_clicked:
    load_draft()
    st.success("途中保存を読み込みました")
    st.rerun()

if delete_clicked:
    delete_draft()
    st.session_state["timeline_data"] = {}
    streamlit_js_eval(
        js_expressions=f"localStorage.removeItem('{storage_key}');",
        key="delete_storage"
    )
    st.success("途中保存を削除しました")
    st.rerun()

st.divider()

initial_data = st.session_state.get("timeline_data", {})

# ==================================================
# タイムラインUI
# ==================================================
html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{
    font-family: sans-serif;
    margin: 0;
}}

.wrapper {{
    width: 100%;
    overflow-x: auto;
    border: 1px solid #ccc;
}}

.grid {{
    display: grid;
    grid-template-columns: 190px repeat(96, 26px);
    user-select: none;
    touch-action: none;
    font-size: 12px;
}}

.cell, .task, .time {{
    border-right: 1px solid #ddd;
    border-bottom: 1px solid #ddd;
    height: 30px;
    box-sizing: border-box;
}}

.task {{
    position: sticky;
    left: 0;
    background: #f7f7f7;
    z-index: 3;
    padding: 6px;
    font-weight: bold;
    white-space: nowrap;
}}

.time {{
    background: #f0f0f0;
    text-align: center;
    font-size: 10px;
    line-height: 30px;
    position: sticky;
    top: 0;
    z-index: 2;
}}

.corner {{
    position: sticky;
    left: 0;
    top: 0;
    z-index: 4;
    background: #e8e8e8;
    font-weight: bold;
}}

.cell {{
    background: white;
}}

.cell.selected {{
    background: #4f9cff;
}}

.cell:hover {{
    outline: 2px solid #333;
}}

.notice {{
    margin-bottom: 8px;
    font-size: 13px;
    color: #555;
}}
</style>
</head>

<body>

<div class="notice">
入力すると自動的にブラウザへ一時保存されます。上部の「入力内容を反映」を押すと提出データに反映されます。
</div>

<div class="wrapper">
    <div class="grid" id="grid"></div>
</div>

<script>
const tasks = {json.dumps(TASK_TYPES, ensure_ascii=False)};
const timeSlots = {json.dumps(TIME_SLOTS, ensure_ascii=False)};
const storageKey = "{storage_key}";

let selected = {json.dumps(initial_data, ensure_ascii=False)};

const stored = localStorage.getItem(storageKey);
if (stored) {{
    try {{
        selected = JSON.parse(stored);
    }} catch(e) {{}}
}} else {{
    localStorage.setItem(storageKey, JSON.stringify(selected));
}}

let isDragging = false;
let dragMode = true;

const grid = document.getElementById("grid");

function saveToStorage() {{
    localStorage.setItem(storageKey, JSON.stringify(selected));
}}

function buildGrid() {{
    grid.innerHTML = "";

    const corner = document.createElement("div");
    corner.className = "time corner";
    corner.innerText = "業務 / 時刻";
    grid.appendChild(corner);

    timeSlots.forEach((t, i) => {{
        const div = document.createElement("div");
        div.className = "time";

        if (i % 4 === 0) {{
            div.innerText = t.substring(0, 2) + "時";
        }}

        grid.appendChild(div);
    }});

    tasks.forEach((task) => {{
        const taskDiv = document.createElement("div");
        taskDiv.className = "task";
        taskDiv.innerText = task;
        grid.appendChild(taskDiv);

        timeSlots.forEach((time) => {{
            const cell = document.createElement("div");
            cell.className = "cell";
            cell.dataset.task = task;
            cell.dataset.time = time;

            if (selected[task] && selected[task].includes(time)) {{
                cell.classList.add("selected");
            }}

            cell.addEventListener("mousedown", startDrag);
            cell.addEventListener("mouseover", dragOver);
            cell.addEventListener("mouseup", endDrag);

            cell.addEventListener("touchstart", touchStart, {{ passive: false }});
            cell.addEventListener("touchmove", touchMove, {{ passive: false }});
            cell.addEventListener("touchend", endDrag);

            grid.appendChild(cell);
        }});
    }});
}}

function toggleCell(cell, mode) {{
    const task = cell.dataset.task;
    const time = cell.dataset.time;

    if (!selected[task]) {{
        selected[task] = [];
    }}

    if (mode) {{
        if (!selected[task].includes(time)) {{
            selected[task].push(time);
            cell.classList.add("selected");
        }}
    }} else {{
        selected[task] = selected[task].filter(t => t !== time);
        cell.classList.remove("selected");

        if (selected[task].length === 0) {{
            delete selected[task];
        }}
    }}

    saveToStorage();
}}

function startDrag(e) {{
    isDragging = true;
    dragMode = !e.target.classList.contains("selected");
    toggleCell(e.target, dragMode);
}}

function dragOver(e) {{
    if (!isDragging) return;
    if (!e.target.classList.contains("cell")) return;
    toggleCell(e.target, dragMode);
}}

function endDrag() {{
    isDragging = false;
}}

function touchStart(e) {{
    e.preventDefault();
    isDragging = true;

    const touch = e.touches[0];
    const el = document.elementFromPoint(touch.clientX, touch.clientY);

    if (el && el.classList.contains("cell")) {{
        dragMode = !el.classList.contains("selected");
        toggleCell(el, dragMode);
    }}
}}

function touchMove(e) {{
    e.preventDefault();
    if (!isDragging) return;

    const touch = e.touches[0];
    const el = document.elementFromPoint(touch.clientX, touch.clientY);

    if (el && el.classList.contains("cell")) {{
        toggleCell(el, dragMode);
    }}
}}

document.addEventListener("mouseup", endDrag);
buildGrid();
</script>

</body>
</html>
"""

components.html(html, height=950, scrolling=True)

records = build_records(
    st.session_state.get("timeline_data", {}),
    ward_name,
    nurse_id,
    selected_date
)

if records:
    df_preview = pd.DataFrame(records)

    st.subheader("入力プレビュー")
    st.dataframe(df_preview, width="stretch")

    summary = (
        df_preview
        .groupby("業務種別")["この業務に割り当てた時間(分)"]
        .sum()
        .reset_index()
    )

    st.subheader("業務集計")
    st.dataframe(summary, width="stretch")

st.divider()

if st.button("提出", type="primary"):
    stored_json = streamlit_js_eval(
        js_expressions=f"localStorage.getItem('{storage_key}')",
        key="get_timeline_for_submit"
    )

    if stored_json:
        try:
            st.session_state["timeline_data"] = json.loads(stored_json)
        except Exception:
            st.error("入力内容の読込に失敗しました")
            st.stop()

    records = build_records(
        st.session_state.get("timeline_data", {}),
        ward_name,
        nurse_id,
        selected_date
    )

    if not ward_name:
        st.warning("病棟名称を入力してください")
        st.stop()

    if not nurse_id:
        st.warning("看護師IDを入力してください")
        st.stop()

    if not records:
        st.warning("入力データがありません")
        st.stop()

    df_daily = pd.DataFrame(records)

    try:
        result = send_to_google_sheet(records)

        if result.get("status") == "success":
            delete_draft()
            st.success(f"提出完了：{result.get('count', len(records))}件を送信しました")
        else:
            st.warning("Apps Script側を確認してください")
            st.write(result)

    except Exception as e:
        st.error("送信に失敗しました")
        st.error(str(e))

    csv_data = (
        df_daily.to_csv(index=False, encoding="utf-8-sig")
        .encode("utf-8-sig")
    )

    st.download_button(
        label="CSVダウンロード",
        data=csv_data,
        file_name=f"nursing_{selected_date}_{ward_name}_{nurse_id}.csv",
        mime="text/csv"
    )
