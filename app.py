import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
import json
import requests

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
    f"{h:02d}:{m:02d}"
    for h in range(24)
    for m in [0, 15, 30, 45]
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


def next_time_label(start):
    hour, minute = map(int, start.split(":"))
    minute += 15

    if minute == 60:
        minute = 0
        hour += 1

    if hour >= 24:
        return "24:00"

    return f"{hour:02d}:{minute:02d}"


def create_empty_grid():
    data = []

    for task in TASK_TYPES:
        row = {"業務種別": task}
        for t in TIME_SLOTS:
            row[t] = False
        data.append(row)

    return pd.DataFrame(data)


def grid_to_timeline(df):
    timeline = {}

    for _, row in df.iterrows():
        task = row["業務種別"]
        selected_times = []

        for t in TIME_SLOTS:
            if bool(row[t]):
                selected_times.append(t)

        if selected_times:
            timeline[task] = selected_times

    return timeline


def timeline_to_grid(timeline_data):
    df = create_empty_grid()

    for task, times in timeline_data.items():
        if task not in TASK_TYPES:
            continue

        row_index = df.index[df["業務種別"] == task]

        if len(row_index) == 0:
            continue

        idx = row_index[0]

        for t in times:
            if t in TIME_SLOTS:
                df.at[idx, t] = True

    return df


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
    selected_date = st.date_input(
        "日付",
        value=date.today()
    )

st.session_state["ward_name"] = ward_name
st.session_state["nurse_id"] = nurse_id

st.info(
    "業務ごとに、実施した15分枠へチェックを入れてください。横スクロールできます。"
)

st.markdown(
    """
    <style>
    div[data-testid="stHorizontalBlock"] {
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

col1, col2, col3 = st.columns(3)

with col1:
    clear_clicked = st.button("全消去", use_container_width=True)

with col2:
    save_clicked = st.button("途中保存", use_container_width=True)

with col3:
    load_clicked = st.button("途中保存読込", use_container_width=True)

if clear_clicked:
    st.session_state["timeline_data"] = {}
    st.success("入力内容を全消去しました。")
    st.rerun()

if load_clicked:
    load_draft()
    st.success("途中保存を読み込みました。")
    st.rerun()

initial_df = timeline_to_grid(
    st.session_state.get("timeline_data", {})
)

edited_df = st.data_editor(
    initial_df,
    hide_index=True,
    use_container_width=True,
    height=720,
    disabled=["業務種別"],
    column_config={
        "業務種別": st.column_config.TextColumn(
            "業務種別",
            width="medium"
        )
    },
    key="timeline_editor"
)

timeline_data = grid_to_timeline(edited_df)
st.session_state["timeline_data"] = timeline_data

records = build_records(
    timeline_data,
    ward_name,
    nurse_id,
    selected_date
)

if save_clicked:
    save_draft()
    st.success(
        f"途中保存しました。現在 {len(records)} 件、合計 {len(records) * 15} 分です。"
    )

st.subheader("入力状況")

if records:
    st.success(
        f"現在の入力：{len(records)} 件、合計 {len(records) * 15} 分"
    )

    df_preview = pd.DataFrame(records)

    st.dataframe(
        df_preview,
        use_container_width=True
    )

    summary = (
        df_preview
        .groupby("業務種別")["この業務に割り当てた時間(分)"]
        .sum()
        .reset_index()
    )

    st.subheader("業務集計")
    st.dataframe(summary, use_container_width=True)

else:
    st.warning("まだ入力がありません。チェックを入れると、ここに件数が表示されます。")

st.divider()

submit_clicked = st.button(
    "スプレッドシートへ提出",
    type="primary",
    use_container_width=True
)

if submit_clicked:
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
        st.warning("入力データがありません。チェックを入れてから提出してください。")
        st.stop()

    df_daily = pd.DataFrame(records)

    try:
        result = send_to_google_sheet(records)

        if result.get("status") == "success":
            delete_draft()

            sent_count = result.get("count", len(records))

            st.balloons()
            st.success(
                f"スプレッドシートへ反映完了しました。送信件数：{sent_count} 件。"
            )
            st.info(
                f"送信内容：{selected_date.isoformat()} / {ward_name} / {nurse_id}"
            )

            st.subheader("送信済みデータ")
            st.dataframe(df_daily, use_container_width=True)

        else:
            st.error("Apps Script側から成功応答が返っていません。")
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
