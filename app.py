import streamlit as st
import pandas as pd
from datetime import date
import json
import requests
import html
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(
    page_title="看護業務 記録アプリ",
    layout="wide"
)

# ==================================================
# Secrets
# ==================================================
def get_required_secret(key):
    value = st.secrets.get(key)
    if not value:
        st.error(f"Streamlit Secrets に {key} が設定されていません。")
        st.stop()
    return value


APP_PASSWORD = get_required_secret("APP_PASSWORD")
APPS_SCRIPT_URL = get_required_secret("APPS_SCRIPT_URL")

# ==================================================
# 表示設定
# ==================================================
EDITOR_HEIGHT = 520
ROW_HEIGHT = 42
TASK_COL_WIDTH = 220
CELL_WIDTH = 56

# ==================================================
# 業務種別
# ==================================================
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

TASK_DETAILS = {
    "食事": "食事介助、体位身支度を整える、経管栄養、摂取量観察、配膳・下膳・タイムアウト、哺乳・調乳",
    "排泄": "排便・排尿介助、トイレ歩行介助、おむつ交換、嘔吐時の世話、ストーマケア、膀胱留置カテーテルの管理、浣腸、導尿、排尿ケアチームに関わるもの、その他のドレーン類の管理",
    "清潔": "清拭、更衣、陰部洗浄、洗髪・整髪、口腔ケア、髭剃り・爪切り、トロリーバス、シャワー浴、洗面介助、沐浴",
    "安全": "転倒転落・危険行動の予防、不穏・徘徊患者の監視、病室巡視、感染の予防、防災",
    "安楽": "体位変換、体位の工夫、罨法、マッサージ、精神的安楽",
    "入院環境の整備": "採光・照明・温度調節、騒音防止、ベッドサイド・病室内の環境整備、コロナ患者に関わる環境整備、退院に関わる環境整備、その他のベッドメイキング",
    "自立の援助": "患者指導、リハビリ、在宅での介護方法指導、レクリエーション、オリエンテーション",
    "患者の移送・移動": "他病棟への転棟、病棟内・病室内でのベッド移動、その他の病棟外への移動",
    "患者及び家族との連絡相談": "家族との連絡・相談・情報交換、患者との連絡・相談、IC立ち合い、ナースコール、患者の用事対応、介護認定調査立ち合い",
    "終末看護処置": "死後の処置、家族等への終末に関する連絡・各種手続きの説明、お見送り",
    "準備・後片付け": "日常生活援助に必要な準備と後片付け",
    "入院当日に関わる業務": "書類準備、患者対応、家族対応、記録及び書類説明とサイン受理、その他入院に関わるもの",
    "退院準備に関わるもの": "チェックリストに基づいた退院準備、看護サマリ・患者指導は別項目",
    "指示受け・報告": "指示受け、医師への確認、病状報告",
    "測定": "バイタルサイン、状態観察、身長、体重、胸囲・腹囲、BSチェック、尿検査、モニター類の観察、その他の測定",
    "呼吸・循環管理": "レスピレーター操作、酸素吸入、排痰促進・喀痰吸引、ネブライザー、Aライン管理、肺・心音聴取、水分出納チェック、CVP、蘇生",
    "治療・診察の介助": "回診補助、包帯交換、ギプス、穿刺、カテーテル類の挿入・除去、血液ガス、髄液検査、組織、その他診療介助",
    "諸検査の介助及び検体採取": "血液、尿、便、痰、胃液、内視鏡・血管造影・カテーテル検査等、検体容器及び提出準備、結果整理",
    "与薬（注射）": "ミキシング、皮下注射・筋肉注射、静脈注射・点滴注射、輸血、注射指示受け、IVH・持続点滴管理、硬膜外からの薬剤管理",
    "与薬（注射を除く）": "内服、経管より注入、軟膏塗布、坐薬、点眼・点耳・点鼻",
    "看護計画・記録": "看護サマリ、各種カンファレンス記録、患者メモ",
    "その他の記録": "その他の看護記録",
    "看護師間の報告・引継ぎ": "申し送り、看護師間の連絡、各種カンファレンス参加",
    "病棟管理に関する記録作成": "病棟管理日誌、業務分担表、その他の管理記録",
    "薬剤業務・薬品管理": "薬剤の請求・受領・返納・管理、常備薬管理、麻薬・向精神薬等の管理",
    "滅菌物・消耗品の管理": "有効期限チェック、滅菌物管理、消耗品管理、検体容器管理",
    "機器・機材の管理": "レスピレーター・ME機器管理、救急カート・回診車点検、清拭車点検整備",
    "病室以外の環境整備": "スタッフステーション、処置室、休憩室、洗浄室等、営繕・修理依頼",
    "病棟外の連絡": "病棟以外の部署への連絡",
    "事務業務": "貸出簿の管理、カルテ管理、面会者対応、荷物の受け渡し対応",
    "物品搬送業務": "あらゆる物品の搬送",
    "職員の勤務及び調整": "勤務表作成、勤務表修正、勤怠システム入力および確認",
    "看護学生・職員の指導": "看護学生指導、面接、スタッフ指導、指導を受けていた",
    "教育・研修参加": "研修会参加",
    "会議": "各種委員会、病棟会議、チームラウンド",
    "職員の健康管理": "休憩休息、健康診断",
    "助産師業務": "助産師外来で行う事項、分娩物品の準備・片付け、分娩室清掃、内診、分娩直接介助、乳房マッサージ、相談対応、腹部エコー、児預かり等",
    "その他": "情報収集、外来応援、その他全般",
}

TIME_SLOTS = [
    f"{h:02d}:{m:02d}"
    for h in range(24)
    for m in [0, 15, 30, 45]
]

# ==================================================
# 関数
# ==================================================
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
        return {"status": "unknown", "message": response.text}


def next_time_label(start):
    hour, minute = map(int, start.split(":"))
    minute += 15

    if minute == 60:
        minute = 0
        hour += 1

    if hour >= 24:
        return "24:00"

    return f"{hour:02d}:{minute:02d}"


def normalize_timeline(data):
    if not isinstance(data, dict):
        return {}

    clean = {}

    for task, times in data.items():
        if task not in TASK_TYPES:
            continue

        if not isinstance(times, list):
            continue

        clean_times = [t for t in times if t in TIME_SLOTS]

        if clean_times:
            clean[task] = sorted(list(set(clean_times)))

    return clean


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


# ==================================================
# 認証
# ==================================================
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

# ==================================================
# 初期化
# ==================================================
if "timeline_data" not in st.session_state:
    st.session_state["timeline_data"] = {}

# ==================================================
# 画面
# ==================================================
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

storage_key = f"nursing_timeline_{selected_date.isoformat()}_{nurse_id or 'no_id'}"

st.info(
    "セル全体をタップできます。指またはマウスで横になぞると、通過したセルを連続入力できます。業務種別をタップすると具体例を表示します。"
)

initial_data = normalize_timeline(st.session_state.get("timeline_data", {}))

tasks_json = json.dumps(TASK_TYPES, ensure_ascii=False)
details_json = json.dumps(TASK_DETAILS, ensure_ascii=False)
slots_json = json.dumps(TIME_SLOTS, ensure_ascii=False)
initial_json = json.dumps(initial_data, ensure_ascii=False)

html_code = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

.timeline-shell {{
    width: 100%;
    height: {EDITOR_HEIGHT}px;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    overflow: auto;
    background: #ffffff;
    touch-action: pan-x pan-y;
}}

.timeline-grid {{
    display: grid;
    grid-template-columns: {TASK_COL_WIDTH}px repeat({len(TIME_SLOTS)}, {CELL_WIDTH}px);
    width: max-content;
    min-width: 100%;
    user-select: none;
}}

.corner,
.time-header,
.task-name,
.cell {{
    border-right: 1px solid #d6d6d6;
    border-bottom: 1px solid #e5e7eb;
}}

.corner {{
    position: sticky;
    left: 0;
    top: 0;
    z-index: 40;
    height: {ROW_HEIGHT}px;
    line-height: {ROW_HEIGHT}px;
    padding-left: 10px;
    background: #e5e7eb;
    font-weight: 800;
}}

.time-header {{
    position: sticky;
    top: 0;
    z-index: 30;
    height: {ROW_HEIGHT}px;
    line-height: {ROW_HEIGHT}px;
    text-align: center;
    background: #f3f4f6;
    font-size: 12px;
    font-weight: 700;
}}

.task-name {{
    position: sticky;
    left: 0;
    z-index: 20;
    height: {ROW_HEIGHT}px;
    line-height: {ROW_HEIGHT}px;
    padding-left: 10px;
    background: #f9fafb;
    font-size: 14px;
    font-weight: 650;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: pointer;
    box-shadow: 2px 0 4px rgba(0,0,0,0.08);
}}

.task-name:hover {{
    background: #eaf4ff;
}}

.cell {{
    height: {ROW_HEIGHT}px;
    min-width: {CELL_WIDTH}px;
    background: #ffffff;
    cursor: pointer;
    touch-action: none;
}}

.cell.hour-start {{
    border-left: 2px solid #9ca3af;
}}

.cell.selected {{
    background: #1e88e5;
    box-shadow: inset 0 0 0 2px #ffffff;
}}

.cell:active {{
    background: #bfdbfe;
}}

.status {{
    margin-top: 8px;
    font-size: 14px;
    color: #374151;
}}

.modal-backdrop {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.35);
    z-index: 9998;
}}

.modal {{
    display: none;
    position: fixed;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: min(760px, calc(100vw - 32px));
    max-height: 70vh;
    overflow-y: auto;
    background: #ffffff;
    border-radius: 14px;
    border: 1px solid #94a3b8;
    box-shadow: 0 12px 32px rgba(0,0,0,0.28);
    z-index: 9999;
    padding: 18px 20px;
}}

.modal-title {{
    font-weight: 800;
    font-size: 18px;
    margin-bottom: 10px;
}}

.modal-body {{
    line-height: 1.8;
    font-size: 15px;
}}

.modal-close {{
    margin-top: 16px;
    padding: 9px 16px;
    border: 1px solid #94a3b8;
    border-radius: 8px;
    background: #f8fafc;
    cursor: pointer;
    font-weight: 800;
}}

@media screen and (max-width: 900px) {{
    .timeline-grid {{
        grid-template-columns: 170px repeat({len(TIME_SLOTS)}, 60px);
    }}

    .task-name,
    .corner {{
        font-size: 12px;
    }}

    .cell {{
        min-width: 60px;
    }}
}}
</style>
</head>
<body>

<div class="timeline-shell" id="timelineShell">
    <div class="timeline-grid" id="timelineGrid"></div>
</div>

<div class="status" id="statusText"></div>

<div class="modal-backdrop" id="modalBackdrop"></div>
<div class="modal" id="modal">
    <div class="modal-title" id="modalTitle"></div>
    <div class="modal-body" id="modalBody"></div>
    <button class="modal-close" id="modalClose">閉じる</button>
</div>

<script>
const tasks = {tasks_json};
const taskDetails = {details_json};
const timeSlots = {slots_json};
const storageKey = "{storage_key}";
let selected = {initial_json};

function readStored() {{
    let stored = null;

    try {{
        stored = window.parent.localStorage.getItem(storageKey);
    }} catch(e) {{}}

    if (!stored) {{
        stored = localStorage.getItem(storageKey);
    }}

    if (stored) {{
        try {{
            selected = JSON.parse(stored) || selected;
        }} catch(e) {{}}
    }} else {{
        saveSelected();
    }}
}}

function saveSelected() {{
    const value = JSON.stringify(selected);
    localStorage.setItem(storageKey, value);

    try {{
        window.parent.localStorage.setItem(storageKey, value);
    }} catch(e) {{}}

    updateStatus();
}}

readStored();

let isPointerDown = false;
let dragMode = true;
let lastCellKey = "";
let didMove = false;

const grid = document.getElementById("timelineGrid");
const statusText = document.getElementById("statusText");

function countSelected() {{
    let count = 0;
    Object.keys(selected).forEach(task => {{
        count += selected[task].length;
    }});
    return count;
}}

function updateStatus() {{
    const count = countSelected();
    statusText.textContent = `現在の入力：${{count}}件、合計 ${{count * 15}} 分`;
}}

function normalizeSelected() {{
    Object.keys(selected).forEach(task => {{
        selected[task] = Array.from(new Set(selected[task])).sort();
        if (selected[task].length === 0) {{
            delete selected[task];
        }}
    }});
}}

function isSelected(task, time) {{
    return selected[task] && selected[task].includes(time);
}}

function setCell(cell, mode) {{
    if (!cell || !cell.classList.contains("cell")) return;

    const task = cell.dataset.task;
    const time = cell.dataset.time;

    if (!selected[task]) {{
        selected[task] = [];
    }}

    if (mode) {{
        if (!selected[task].includes(time)) {{
            selected[task].push(time);
        }}
        cell.classList.add("selected");
    }} else {{
        selected[task] = selected[task].filter(t => t !== time);
        cell.classList.remove("selected");

        if (selected[task].length === 0) {{
            delete selected[task];
        }}
    }}

    normalizeSelected();
    saveSelected();
}}

function getCellFromPoint(x, y) {{
    const el = document.elementFromPoint(x, y);
    if (!el) return null;
    if (el.classList.contains("cell")) return el;
    return el.closest(".cell");
}}

function cellKey(cell) {{
    if (!cell) return "";
    return `${{cell.dataset.task}}__${{cell.dataset.time}}`;
}}

function buildGrid() {{
    grid.innerHTML = "";

    const corner = document.createElement("div");
    corner.className = "corner";
    corner.textContent = "業務種別";
    grid.appendChild(corner);

    timeSlots.forEach((time, i) => {{
        const header = document.createElement("div");
        header.className = "time-header";
        header.textContent = i % 4 === 0 ? time.substring(0, 2) + "時" : time.substring(3, 5);
        grid.appendChild(header);
    }});

    tasks.forEach(task => {{
        const name = document.createElement("div");
        name.className = "task-name";
        name.textContent = task;
        name.dataset.task = task;
        name.dataset.detail = taskDetails[task] || "説明は登録されていません。";
        name.addEventListener("click", () => openModal(name.dataset.task, name.dataset.detail));
        grid.appendChild(name);

        timeSlots.forEach((time, i) => {{
            const cell = document.createElement("div");
            cell.className = "cell";
            if (i % 4 === 0) cell.classList.add("hour-start");
            cell.dataset.task = task;
            cell.dataset.time = time;

            if (isSelected(task, time)) {{
                cell.classList.add("selected");
            }}

            cell.addEventListener("pointerdown", onPointerDown);
            cell.addEventListener("pointerenter", onPointerEnter);
            cell.addEventListener("pointermove", onPointerMove);
            cell.addEventListener("click", onCellClick);

            grid.appendChild(cell);
        }});
    }});

    updateStatus();
}}

function onPointerDown(e) {{
    const cell = e.currentTarget;
    isPointerDown = true;
    didMove = false;
    lastCellKey = cellKey(cell);
    dragMode = !cell.classList.contains("selected");

    try {{
        cell.setPointerCapture(e.pointerId);
    }} catch(err) {{}}

    setCell(cell, dragMode);
    e.preventDefault();
}}

function onPointerEnter(e) {{
    if (!isPointerDown) return;

    const cell = e.currentTarget;
    const key = cellKey(cell);

    if (key !== lastCellKey) {{
        didMove = true;
        lastCellKey = key;
        setCell(cell, dragMode);
    }}
}}

function onPointerMove(e) {{
    if (!isPointerDown) return;

    const cell = getCellFromPoint(e.clientX, e.clientY);
    const key = cellKey(cell);

    if (cell && key !== lastCellKey) {{
        didMove = true;
        lastCellKey = key;
        setCell(cell, dragMode);
    }}

    e.preventDefault();
}}

function onCellClick(e) {{
    if (didMove) {{
        e.preventDefault();
        e.stopPropagation();
    }}
}}

document.addEventListener("pointerup", () => {{
    isPointerDown = false;
    lastCellKey = "";
    setTimeout(() => {{ didMove = false; }}, 60);
}});

document.addEventListener("pointercancel", () => {{
    isPointerDown = false;
    lastCellKey = "";
    didMove = false;
}});

function openModal(task, detail) {{
    document.getElementById("modalTitle").textContent = task;
    document.getElementById("modalBody").textContent = detail;
    document.getElementById("modal").style.display = "block";
    document.getElementById("modalBackdrop").style.display = "block";
}}

function closeModal() {{
    document.getElementById("modal").style.display = "none";
    document.getElementById("modalBackdrop").style.display = "none";
}}

document.getElementById("modalClose").addEventListener("click", closeModal);
document.getElementById("modalBackdrop").addEventListener("click", closeModal);

buildGrid();
</script>

</body>
</html>
"""

components.html(
    html_code,
    height=EDITOR_HEIGHT + 45,
    scrolling=False
)

reflect_clicked = st.button(
    "入力内容を反映",
    type="secondary",
    use_container_width=True
)

submit_clicked = st.button(
    "提出",
    type="primary",
    use_container_width=True
)

stored_json = streamlit_js_eval(
    js_expressions=f"""
    (function() {{
        let v = null;
        try {{
            v = window.localStorage.getItem('{storage_key}');
        }} catch(e) {{}}
        return v;
    }})()
    """,
    key=f"get_timeline_json_{selected_date}_{nurse_id}"
)

if stored_json:
    try:
        st.session_state["timeline_data"] = normalize_timeline(
            json.loads(stored_json)
        )
    except Exception:
        st.warning("入力内容の読み取りに失敗しました。")

records = build_records(
    st.session_state.get("timeline_data", {}),
    ward_name,
    nurse_id,
    selected_date
)

if reflect_clicked:
    if records:
        st.success(
            f"入力内容を反映しました。現在 {len(records)} 件、合計 {len(records) * 15} 分です。"
            "参考内容はページ最下部に表示しています。"
        )
    else:
        st.warning("入力内容がありません。セルをタップまたはなぞってから反映してください。")

if submit_clicked:
    if not ward_name:
        st.warning("病棟名称を入力してください。")
        st.stop()

    if not nurse_id:
        st.warning("看護師IDを入力してください。")
        st.stop()

    if not records:
        st.warning("入力データがありません。セルをタップまたはなぞってから提出してください。")
        st.stop()

    try:
        result = send_to_google_sheet(records)

        if result.get("status") == "success":
            st.balloons()
            st.success(
                f"スプレッドシートへ反映完了しました。送信件数：{result.get('count', len(records))} 件。"
            )
            st.info(
                f"送信内容：{selected_date.isoformat()} / {ward_name} / {nurse_id}"
            )
        else:
            st.error("Apps Script側から成功応答が返っていません。")
            st.write(result)

    except Exception as e:
        st.error("スプレッドシートへの送信に失敗しました。")
        st.exception(e)

st.divider()
st.subheader("参考：入力内容")

if records:
    st.success(f"現在の入力：{len(records)} 件、合計 {len(records) * 15} 分")

    df_preview = pd.DataFrame(records)
    st.dataframe(df_preview, use_container_width=True)

    summary = (
        df_preview
        .groupby("業務種別")["この業務に割り当てた時間(分)"]
        .sum()
        .reset_index()
    )

    st.subheader("参考：業務集計")
    st.dataframe(summary, use_container_width=True)

    csv_data = (
        df_preview
        .to_csv(index=False, encoding="utf-8-sig")
        .encode("utf-8-sig")
    )

    st.download_button(
        label="CSVダウンロード",
        data=csv_data,
        file_name=f"nursing_{selected_date}_{ward_name}_{nurse_id}.csv",
        mime="text/csv"
    )
else:
    st.warning("まだ反映済みの入力がありません。")
