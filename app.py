import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
import json
import requests
import math

from PIL import Image, ImageDraw, ImageFont
from streamlit_drawable_canvas import st_canvas


# ==================================================
# Streamlit 初期設定
# ==================================================
st.set_page_config(
    page_title="看護業務 記録アプリ",
    layout="wide"
)

APP_PASSWORD = st.secrets["APP_PASSWORD"]
APPS_SCRIPT_URL = st.secrets["APPS_SCRIPT_URL"]


# ==================================================
# パスワード認証
# ==================================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:

    st.title("看護業務 記録アプリ")

    password = st.text_input(
        "パスワードを入力してください",
        type="password"
    )

    if st.button("ログイン"):
        if password == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("パスワードが違います")

    st.stop()


# ==================================================
# 保存設定
# ==================================================
SAVE_DIR = Path("data")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

DRAFT_FILE = SAVE_DIR / "nurse_draft.json"


# ==================================================
# 業務種別
# ==================================================
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

TIME_SLOTS = [
    f"{hour:02d}:{minute:02d}"
    for hour in range(24)
    for minute in [0, 15, 30, 45]
]


# ==================================================
# 表示サイズ設定
# ==================================================
LABEL_W = 220
HEADER_H = 44
CELL_W = 26
ROW_H = 30

CANVAS_W = LABEL_W + CELL_W * len(TIME_SLOTS)
CANVAS_H = HEADER_H + ROW_H * len(TASK_TYPES)


# ==================================================
# Google Sheets送信
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
        return {
            "status": "unknown",
            "message": response.text
        }


# ==================================================
# 下書き
# ==================================================
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


# ==================================================
# 背景グリッド作成
# ==================================================
def create_background_image(timeline_data=None):

    img = Image.new(
        "RGB",
        (CANVAS_W, CANVAS_H),
        "white"
    )

    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            12
        )
        small_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            10
        )
    except Exception:
        font = None
        small_font = None

    # ヘッダー背景
    draw.rectangle(
        [0, 0, CANVAS_W, HEADER_H],
        fill="#eeeeee"
    )

    draw.rectangle(
        [0, 0, LABEL_W, CANVAS_H],
        fill="#f7f7f7"
    )

    # 既存入力の塗りつぶし表示
    if timeline_data:
        for task, times in timeline_data.items():
            if task not in TASK_TYPES:
                continue

            row = TASK_TYPES.index(task)

            for t in times:
                if t not in TIME_SLOTS:
                    continue

                col = TIME_SLOTS.index(t)

                x1 = LABEL_W + col * CELL_W
                y1 = HEADER_H + row * ROW_H

                draw.rectangle(
                    [x1 + 1, y1 + 1, x1 + CELL_W - 1, y1 + ROW_H - 1],
                    fill="#8fc5ff"
                )

    # 業務名
    for i, task in enumerate(TASK_TYPES):
        y = HEADER_H + i * ROW_H
        draw.text(
            (6, y + 7),
            task,
            fill="black",
            font=font
        )

    # 時刻
    for i, t in enumerate(TIME_SLOTS):
        x = LABEL_W + i * CELL_W

        if i % 4 == 0:
            draw.text(
                (x + 2, 8),
                f"{t[:2]}時",
                fill="black",
                font=small_font
            )

        if i % 4 == 0:
            line_color = "#777777"
        else:
            line_color = "#dddddd"

        draw.line(
            [(x, 0), (x, CANVAS_H)],
            fill=line_color,
            width=1
        )

    # 横線
    for i in range(len(TASK_TYPES) + 1):
        y = HEADER_H + i * ROW_H
        draw.line(
            [(0, y), (CANVAS_W, y)],
            fill="#999999",
            width=1
        )

    # 境界線
    draw.line(
        [(LABEL_W, 0), (LABEL_W, CANVAS_H)],
        fill="#333333",
        width=2
    )

    draw.line(
        [(0, HEADER_H), (CANVAS_W, HEADER_H)],
        fill="#333333",
        width=2
    )

    draw.text(
        (8, 12),
        "業務 / 時刻",
        fill="black",
        font=font
    )

    return img


# ==================================================
# canvasの線データを業務×時間へ変換
# ==================================================
def canvas_json_to_timeline(canvas_json, existing_data=None):

    timeline = existing_data.copy() if existing_data else {}

    if not canvas_json:
        return timeline

    objects = canvas_json.get("objects", [])

    for obj in objects:

        if obj.get("type") != "path":
            continue

        left = obj.get("left", 0)
        top = obj.get("top", 0)
        path = obj.get("path", [])

        points = []

        for item in path:
            if len(item) >= 3:
                cmd = item[0]

                if cmd in ["M", "L"]:
                    x = left + float(item[1])
                    y = top + float(item[2])
                    points.append((x, y))

                elif cmd == "Q" and len(item) >= 5:
                    x = left + float(item[3])
                    y = top + float(item[4])
                    points.append((x, y))

        for i in range(len(points) - 1):

            x1, y1 = points[i]
            x2, y2 = points[i + 1]

            distance = max(
                abs(x2 - x1),
                abs(y2 - y1),
                1
            )

            steps = int(distance / 4) + 1

            for s in range(steps + 1):

                rate = s / steps

                x = x1 + (x2 - x1) * rate
                y = y1 + (y2 - y1) * rate

                if x < LABEL_W or y < HEADER_H:
                    continue

                row = int((y - HEADER_H) // ROW_H)
                col = int((x - LABEL_W) // CELL_W)

                if row < 0 or row >= len(TASK_TYPES):
                    continue

                if col < 0 or col >= len(TIME_SLOTS):
                    continue

                task = TASK_TYPES[row]
                time = TIME_SLOTS[col]

                if task not in timeline:
                    timeline[task] = []

                if time not in timeline[task]:
                    timeline[task].append(time)

    for task in list(timeline.keys()):
        timeline[task] = sorted(timeline[task])
        if not timeline[task]:
            del timeline[task]

    return timeline


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


# ==================================================
# 初期ロード
# ==================================================
if "draft_loaded" not in st.session_state:
    load_draft()
    st.session_state["draft_loaded"] = True

if "timeline_data" not in st.session_state:
    st.session_state["timeline_data"] = {}

if "submit_result_message" not in st.session_state:
    st.session_state["submit_result_message"] = ""


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
    selected_date = st.date_input(
        "日付",
        value=date.today()
    )

st.session_state["ward_name"] = ward_name
st.session_state["nurse_id"] = nurse_id


# ==================================================
# 固定ボタン
# ==================================================
st.markdown(
    """
    <style>
    .fixed-area {
        position: sticky;
        top: 0;
        background: white;
        z-index: 9999;
        padding: 10px 0 12px 0;
        border-bottom: 1px solid #ddd;
    }
    </style>
    <div class="fixed-area">
    """,
    unsafe_allow_html=True
)

st.info(
    "業務行をマウスでドラッグ、またはスマホ・タブレットで指でなぞって入力してください。入力後は「入力内容を反映」を押すと、下にプレビュー件数が表示されます。"
)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    reflect_clicked = st.button(
        "入力内容を反映",
        use_container_width=True
    )

with col2:
    clear_clicked = st.button(
        "全消去",
        use_container_width=True
    )

with col3:
    save_clicked = st.button(
        "途中保存",
        use_container_width=True
    )

with col4:
    load_clicked = st.button(
        "途中保存読込",
        use_container_width=True
    )

with col5:
    delete_clicked = st.button(
        "途中保存削除",
        use_container_width=True
    )

st.markdown(
    "</div>",
    unsafe_allow_html=True
)


if clear_clicked:
    st.session_state["timeline_data"] = {}
    st.session_state["submit_result_message"] = ""
    st.success("入力内容を全消去しました。")
    st.rerun()

if load_clicked:
    load_draft()
    st.success("途中保存を読み込みました。")
    st.rerun()

if delete_clicked:
    delete_draft()
    st.session_state["timeline_data"] = {}
    st.session_state["submit_result_message"] = ""
    st.success("途中保存を削除しました。")
    st.rerun()


# ==================================================
# 入力キャンバス
# ==================================================
background_img = create_background_image(
    st.session_state.get("timeline_data", {})
)

canvas_result = st_canvas(
    fill_color="rgba(79, 156, 255, 0.25)",
    stroke_width=18,
    stroke_color="rgba(20, 120, 255, 0.70)",
    background_image=background_img,
    update_streamlit=True,
    height=CANVAS_H,
    width=CANVAS_W,
    drawing_mode="freedraw",
    key="nursing_timeline_canvas",
)

if reflect_clicked:

    parsed_timeline = canvas_json_to_timeline(
        canvas_result.json_data,
        st.session_state.get("timeline_data", {})
    )

    st.session_state["timeline_data"] = parsed_timeline

    reflected_records = build_records(
        st.session_state["timeline_data"],
        ward_name,
        nurse_id,
        selected_date
    )

    if reflected_records:
        st.success(
            f"入力内容を反映しました。現在 {len(reflected_records)} 件、"
            f"{len(reflected_records) * 15} 分ぶんの入力があります。"
        )
    else:
        st.warning(
            "入力内容がありません。業務行の時間部分を横になぞってから、もう一度押してください。"
        )

if save_clicked:

    parsed_timeline = canvas_json_to_timeline(
        canvas_result.json_data,
        st.session_state.get("timeline_data", {})
    )

    st.session_state["timeline_data"] = parsed_timeline

    save_draft()

    st.success("途中保存しました。")


# ==================================================
# プレビュー
# ==================================================
records = build_records(
    st.session_state.get("timeline_data", {}),
    ward_name,
    nurse_id,
    selected_date
)

if records:

    df_preview = pd.DataFrame(records)

    st.subheader("入力プレビュー")

    st.success(
        f"現在の入力：{len(records)} 件、合計 {len(records) * 15} 分"
    )

    st.dataframe(
        df_preview,
        width="stretch"
    )

    summary = (
        df_preview
        .groupby("業務種別")["この業務に割り当てた時間(分)"]
        .sum()
        .reset_index()
    )

    st.subheader("業務集計")

    st.dataframe(
        summary,
        width="stretch"
    )

else:
    st.warning(
        "まだ反映済みの入力がありません。タイムラインをなぞった後、「入力内容を反映」を押してください。"
    )


# ==================================================
# 提出
# ==================================================
st.divider()

submit_clicked = st.button(
    "スプレッドシートへ提出",
    type="primary",
    use_container_width=True
)

if submit_clicked:

    parsed_timeline = canvas_json_to_timeline(
        canvas_result.json_data,
        st.session_state.get("timeline_data", {})
    )

    st.session_state["timeline_data"] = parsed_timeline

    records = build_records(
        st.session_state.get("timeline_data", {}),
        ward_name,
        nurse_id,
        selected_date
    )

    if not ward_name:
        st.warning("病棟名称を入力してください。")
        st.stop()

    if not nurse_id:
        st.warning("看護師IDを入力してください。")
        st.stop()

    if not records:
        st.warning(
            "入力データがありません。タイムラインをなぞった後、「入力内容を反映」または「スプレッドシートへ提出」を押してください。"
        )
        st.stop()

    df_daily = pd.DataFrame(records)

    try:
        result = send_to_google_sheet(records)

        if result.get("status") == "success":

            delete_draft()

            sent_count = result.get(
                "count",
                len(records)
            )

            st.balloons()

            st.success(
                f"スプレッドシートへ反映完了しました。送信件数：{sent_count}件。"
            )

            st.info(
                f"送信内容：{selected_date.isoformat()} / {ward_name} / {nurse_id}"
            )

            st.dataframe(
                df_daily,
                width="stretch"
            )

        else:
            st.error(
                "送信は実行されましたが、Apps Script側から成功応答が返っていません。"
            )
            st.write(result)

    except Exception as e:
        st.error("スプレッドシートへの送信に失敗しました。")
        st.exception(e)

    csv_data = (
        df_daily
        .to_csv(index=False, encoding="utf-8-sig")
        .encode("utf-8-sig")
    )

    st.download_button(
        label="CSVダウンロード",
        data=csv_data,
        file_name=f"nursing_{selected_date}_{ward_name}_{nurse_id}.csv",
        mime="text/csv"
    )
