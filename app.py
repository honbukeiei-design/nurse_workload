import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
import json
import requests
import streamlit.components.v1 as components

st.set_page_config(
    page_title="看護業務 記録アプリ",
    layout="wide"
)

APP_PASSWORD = st.secrets["APP_PASSWORD"]
APPS_SCRIPT_URL = st.secrets["APPS_SCRIPT_URL"]

# -----------------------------
# 認証
# -----------------------------
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
    "食事",
    "排泄",
    "清潔",
    "安全",
    "安楽",
    "入院環境の整備",
    "自立の援助",
    "患者の移送・移動",
    "患者及び家族との連絡相談",
    "終末看護処置",
    "準備・後片付け",
    "入院当日に関わる業務",
    "退院準備に関わるもの",
    "指示受け・報告",
    "測定",
    "呼吸・循環管理",
    "治療・診察の介助",
    "諸検査の介助及び検体採取",
    "与薬（注射）",
    "与薬（注射を除く）",
    "看護計画・記録",
    "その他の記録",
    "看護師間の報告・引継ぎ",
    "病棟管理に関する記録作成",
    "薬剤業務・薬品管理",
    "滅菌物・消耗品の管理",
    "機器・機材の管理",
    "病室以外の環境整備",
    "病棟外の連絡",
    "事務業務",
    "物品搬送業務",
    "職員の勤務及び調整",
    "看護学生・職員の指導",
    "教育・研修参加",
    "会議",
    "職員の健康管理",
    "助産師業務",
    "その他",
]

TIME_SLOTS = []
for hour in range(24):
    for minute in [0, 15, 30, 45]:
        TIME_SLOTS.append(f"{hour:02d}:{minute:02d}")

# -----------------------------
# 下書き
# -----------------------------
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


if "draft_loaded" not in st.session_state:
    load_draft()
    st.session_state["draft_loaded"] = True

if "timeline_data" not in st.session_state:
    st.session_state["timeline_data"] = {}

# -----------------------------
# 画面
# -----------------------------
st.title("看護業務 記録アプリ")

col_a, col_b, col_c = st.columns([1, 1, 1])

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

st.info(
    "業務行をマウスでドラッグ、またはスマホ・タブレットで指でなぞると15分単位で入力できます。"
)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("途中保存"):
        save_draft()
        st.success("途中保存しました")

with col2:
    if st.button("途中保存読込"):
        load_draft()
        st.success("途中保存を読み込みました")
        st.rerun()

with col3:
    if st.button("途中保存削除"):
        delete_draft()
        st.session_state["timeline_data"] = {}
        st.success("途中保存を削除しました")
        st.rerun()

st.divider()

# -----------------------------
# タイムラインUI
# -----------------------------
initial_data = st.session_state.get("timeline_data", {})

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
    grid-template-columns: 180px repeat(96, 24px);
    user-select: none;
    touch-action: none;
    font-size: 12px;
}}

.cell, .task, .time {{
    border-right: 1px solid #ddd;
    border-bottom: 1px solid #ddd;
    height: 28px;
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
    line-height: 28px;
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
    text-align: center;
    line-height: 28px;
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

.controls {{
    margin: 12px 0;
}}

button {{
    padding: 8px 12px;
    margin-right: 8px;
    border: 1px solid #aaa;
    background: #fff;
    border-radius: 6px;
}}
</style>
</head>

<body>

<div class="controls">
    <button onclick="clearAll()">全消去</button>
    <button onclick="sendData()">入力内容を反映</button>
</div>

<div class="wrapper">
    <div class="grid" id="grid"></div>
</div>

<script>
const tasks = {json.dumps(TASK_TYPES, ensure_ascii=False)};
const timeSlots = {json.dumps(TIME_SLOTS, ensure_ascii=False)};
let selected = {json.dumps(initial_data, ensure_ascii=False)};

let isDragging = false;
let dragMode = true;

const grid = document.getElementById("grid");

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
        }} else {{
            div.innerText = "";
        }}

        grid.appendChild(div);
    }});

    tasks.forEach((task, row) => {{
        const taskDiv = document.createElement("div");
        taskDiv.className = "task";
        taskDiv.innerText = task;
        grid.appendChild(taskDiv);

        timeSlots.forEach((time, col) => {{
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
    }}
}}

function startDrag(e) {{
    isDragging = true;
    dragMode = !e.target.classList.contains("selected");
    toggleCell(e.target, dragMode);
}}

function dragOver(e) {{
    if (!isDragging) return;
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

function clearAll() {{
    selected = {{}};
    document.querySelectorAll(".cell").forEach(c => c.classList.remove("selected"));
}}

function sendData() {{
    const text = JSON.stringify(selected);
    const textarea = window.parent.document.querySelector('textarea[aria-label="timeline_json"]');

    if (textarea) {{
        textarea.value = text;
        textarea.dispatchEvent(new Event("input", {{ bubbles: true }}));
    }}
}}

document.addEventListener("mouseup", endDrag);
buildGrid();
</script>

</body>
</html>
"""

components.html(html, height=950, scrolling=True)

timeline_json = st.text_area(
    "timeline_json",
    value=json.dumps(st.session_state.get("timeline_data", {}), ensure_ascii=False),
    height=1,
    label_visibility="collapsed"
)

try:
    st.session_state["timeline_data"] = json.loads(timeline_json)
except Exception:
    pass

st.caption("入力後は「入力内容を反映」を押してください。その後、途中保存または提出できます。")

st.divider()

# -----------------------------
# 提出用データ作成
# -----------------------------
def next_time_label(start):
    hour, minute = map(int, start.split(":"))
    minute += 15

    if minute == 60:
        minute = 0
        hour += 1

    if hour >= 24:
        return "24:00"

    return f"{hour:02d}:{minute:02d}"


def build_records(timeline_data):
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


records = build_records(st.session_state["timeline_data"])

if records:
    df_preview = pd.DataFrame(records)

    st.subheader("入力プレビュー")
    st.dataframe(df_preview, width="stretch")

    summary = (
        df_preview.groupby("業務種別")["この業務に割り当てた時間(分)"]
        .sum()
        .reset_index()
    )

    st.subheader("業務集計")
    st.dataframe(summary, width="stretch")

# -----------------------------
# 提出
# -----------------------------
if st.button("提出"):
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
