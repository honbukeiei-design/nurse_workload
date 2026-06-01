import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
import json
import requests

# ----------------------------------------
# Streamlit 初期設定
# ----------------------------------------
st.set_page_config(
    page_title="看護業務 記録アプリ",
    layout="centered"
)

# ----------------------------------------
# Secrets
# ----------------------------------------
APP_PASSWORD = st.secrets["APP_PASSWORD"]

APPS_SCRIPT_URL = st.secrets[
    "APPS_SCRIPT_URL"
]

# ----------------------------------------
# パスワード認証
# ----------------------------------------
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

            st.session_state[
                "authenticated"
            ] = True

            st.rerun()

        else:

            st.error(
                "パスワードが違います"
            )

    st.stop()

# ----------------------------------------
# 保存フォルダ
# ----------------------------------------
SAVE_DIR = Path("data")

SAVE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

DRAFT_FILE = (
    SAVE_DIR / "nurse_draft.json"
)

# ----------------------------------------
# 業務種別
# ----------------------------------------
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

# ----------------------------------------
# 下書き保存
# ----------------------------------------
def save_draft():

    draft = {}

    for key, value in st.session_state.items():

        if isinstance(value, (list, str)):
            draft[key] = value

    with open(
        DRAFT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            draft,
            f,
            ensure_ascii=False
        )

# ----------------------------------------
# 下書き読込
# ----------------------------------------
def load_draft():

    if DRAFT_FILE.exists():

        with open(
            DRAFT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            draft = json.load(f)

        for key, value in draft.items():

            st.session_state[key] = value

# ----------------------------------------
# 下書き削除
# ----------------------------------------
def delete_draft():

    if DRAFT_FILE.exists():
        DRAFT_FILE.unlink()

# ----------------------------------------
# Google Sheets送信
# ----------------------------------------
def send_to_google_sheet(records):

    payload = {
        "records": records
    }

    response = requests.post(
        APPS_SCRIPT_URL,
        json=payload,
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

# ----------------------------------------
# 初回ロード
# ----------------------------------------
if "draft_loaded" not in st.session_state:

    load_draft()

    st.session_state[
        "draft_loaded"
    ] = True

# ----------------------------------------
# タイトル
# ----------------------------------------
st.title("看護業務 記録アプリ")

# ----------------------------------------
# 基本情報
# ----------------------------------------
ward_name = st.text_input(
    "病棟名称",
    value=st.session_state.get(
        "ward_name",
        ""
    )
)

nurse_id = st.text_input(
    "看護師ID",
    value=st.session_state.get(
        "nurse_id",
        ""
    )
)

selected_date = st.date_input(
    "日付",
    value=date.today()
)

st.session_state[
    "ward_name"
] = ward_name

st.session_state[
    "nurse_id"
] = nurse_id

st.markdown("""
1日24時間を15分単位で入力します。  
途中保存が可能です。  
提出時にGoogleスプレッドシートへ送信します。
""")

st.divider()

# ----------------------------------------
# 下書き操作
# ----------------------------------------
col1, col2, col3 = st.columns(3)

with col1:

    if st.button("途中保存"):

        save_draft()

        st.success(
            "途中保存しました"
        )

with col2:

    if st.button("途中保存読込"):

        load_draft()

        st.success(
            "途中保存を読み込みました"
        )

with col3:

    if st.button("途中保存削除"):

        delete_draft()

        st.success(
            "途中保存を削除しました"
        )

st.divider()

# ----------------------------------------
# 15分入力
# ----------------------------------------
st.subheader(
    "15分ごとの業務入力"
)

for hour in range(24):

    with st.expander(
        f"{hour:02d}:00 ～ "
        f"{hour:02d}:59"
    ):

        for minute in [
            0,
            15,
            30,
            45
        ]:

            start_label = (
                f"{hour:02d}:"
                f"{minute:02d}"
            )

            end_hour = hour

            end_min = minute + 15

            if end_min == 60:

                end_min = 0

                end_hour += 1

            if end_hour >= 24:

                end_label = "24:00"

            else:

                end_label = (
                    f"{end_hour:02d}:"
                    f"{end_min:02d}"
                )

            state_key = (
                f"{selected_date}_"
                f"{hour}_"
                f"{minute}"
            )

            selected_tasks = st.multiselect(
                f"{start_label} ～ "
                f"{end_label}",
                options=TASK_TYPES,
                key=state_key
            )

            if len(selected_tasks) > 3:

                st.error(
                    "選択は最大3つまでです"
                )

st.divider()

# ----------------------------------------
# 提出
# ----------------------------------------
if st.button("提出"):

    if not ward_name:

        st.warning(
            "病棟名称を入力してください"
        )

        st.stop()

    if not nurse_id:

        st.warning(
            "看護師IDを入力してください"
        )

        st.stop()

    records = []

    for hour in range(24):

        for minute in [
            0,
            15,
            30,
            45
        ]:

            start_label = (
                f"{hour:02d}:"
                f"{minute:02d}"
            )

            end_hour = hour

            end_min = minute + 15

            if end_min == 60:

                end_min = 0

                end_hour += 1

            if end_hour >= 24:

                end_label = "24:00"

            else:

                end_label = (
                    f"{end_hour:02d}:"
                    f"{end_min:02d}"
                )

            state_key = (
                f"{selected_date}_"
                f"{hour}_"
                f"{minute}"
            )

            selected_tasks = (
                st.session_state.get(
                    state_key,
                    []
                )
            )

            if len(selected_tasks) > 3:

                st.error(
                    (
                        f"{start_label} ～ "
                        f"{end_label} "
                        "は3つ以下にしてください"
                    )
                )

                st.stop()

            if not selected_tasks:
                continue

            minutes_per_task = (
                15 / len(selected_tasks)
            )

            for task in selected_tasks:

                records.append({

                    "病棟名称":
                    ward_name,

                    "日付":
                    selected_date.isoformat(),

                    "看護師ID":
                    nurse_id,

                    "開始":
                    start_label,

                    "終了":
                    end_label,

                    "業務種別":
                    task,

                    "この業務に割り当てた時間(分)":
                    minutes_per_task
                })

    if not records:

        st.warning(
            "入力データがありません"
        )

        st.stop()

    df_daily = pd.DataFrame(records)

    # ----------------------------------------
    # Google Sheets送信
    # ----------------------------------------
    try:

        result = send_to_google_sheet(
            records
        )

        if result.get(
            "status"
        ) == "success":

            delete_draft()

            st.success(
                (
                    "提出完了："
                    f"{result.get('count', len(records))}"
                    "件を送信しました"
                )
            )

        else:

            st.warning(
                "Apps Script側を確認してください"
            )

            st.write(result)

    except Exception as e:

        st.error(
            "送信に失敗しました"
        )

        st.error(str(e))

    # ----------------------------------------
    # CSVダウンロード
    # ----------------------------------------
    csv_data = (
        df_daily.to_csv(
            index=False,
            encoding="utf-8-sig"
        )
        .encode("utf-8-sig")
    )

    st.download_button(
        label="CSVダウンロード",
        data=csv_data,
        file_name=(
            f"nursing_"
            f"{selected_date}_"
            f"{ward_name}_"
            f"{nurse_id}.csv"
        ),
        mime="text/csv"
    )

    # ----------------------------------------
    # データ表示
    # ----------------------------------------
    st.subheader("提出データ")

    st.dataframe(
        df_daily,
        width="stretch"
    )

    # ----------------------------------------
    # 集計
    # ----------------------------------------
    summary = (
        df_daily.groupby(
            "業務種別"
        )[
            "この業務に割り当てた時間(分)"
        ]
        .sum()
        .round(1)
    )

    st.subheader("業務集計")

    st.dataframe(
        summary.reset_index(),
        width="stretch"
    )
