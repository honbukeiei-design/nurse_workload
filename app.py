import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
import json

# -----------------------------
# 基本設定
# -----------------------------
st.set_page_config(
    page_title="看護業務 15分単位 記録アプリ",
    layout="centered"
)

# -----------------------------
# 保存先設定
# -----------------------------
DESKTOP = Path.home() / "Desktop"

# 累積保存CSV
DATA_FILE = DESKTOP / "nurse_15min_log.csv"

# 下書き保存ファイル
DRAFT_FILE = DESKTOP / "nurse_draft.json"

# -----------------------------
# 業務分類
# -----------------------------
TASK_TYPES = [
    "身体の清潔",
    "入退院時の世話",
    "与薬（注射除く）",
    "食事の世話",
    "観察",
    "患者の移送",
    "排泄の世話",
    "身の回りの世話",
    "安全の確保",
    "安楽",
    "自立の援助",
    "終末看護",
    "診療、治療の介助",
    "呼吸循環管理",
    "測定",
    "諸検査",
    "医師への報告・連絡",
    "NS間の報告・申し継ぎ",
    "患者および家族との連絡",
    "記録",
    "家族の指導、相談",
    "看護職員・看護学生の指導",
    "薬剤業務",
    "物品管理",
    "医療器具・材料の取り扱い",
    "病室内の環境整備",
    "病室外の環境整備",
    "ナースコール",
    "病棟外の連絡",
    "電話による連絡",
    "メッセンジャー業務",
    "事務業務",
    "管理業務",
    "職員の健康管理",
    "ME機器の管理",
    "その他",
]

# -----------------------------
# CSV読み込み
# -----------------------------
def load_all_data():
    if DATA_FILE.exists():
        try:
            return pd.read_csv(DATA_FILE, encoding="utf-8-sig")
        except:
            return pd.read_csv(DATA_FILE)

    columns = [
        "病棟名称",
        "日付",
        "看護師ID",
        "開始",
        "終了",
        "業務種別",
        "この業務に割り当てた時間(分)"
    ]

    return pd.DataFrame(columns=columns)

# -----------------------------
# CSV追記
# -----------------------------
def append_daily_data(df_daily):

    df_all = load_all_data()

    if df_all.empty:
        df_all = df_daily.copy()
    else:
        df_all = pd.concat([df_all, df_daily], ignore_index=True)

    df_all.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# -----------------------------
# 下書き保存
# -----------------------------
def save_draft():

    draft = {}

    for key, value in st.session_state.items():
        if isinstance(value, (list, str)):
            draft[key] = value

    with open(DRAFT_FILE, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False)

# -----------------------------
# 下書き読込
# -----------------------------
def load_draft():

    if DRAFT_FILE.exists():

        with open(DRAFT_FILE, "r", encoding="utf-8") as f:
            draft = json.load(f)

        for key, value in draft.items():
            st.session_state[key] = value

# -----------------------------
# 下書き削除
# -----------------------------
def delete_draft():

    if DRAFT_FILE.exists():
        DRAFT_FILE.unlink()

# -----------------------------
# 初回読込
# -----------------------------
if "draft_loaded" not in st.session_state:
    load_draft()
    st.session_state["draft_loaded"] = True

# -----------------------------
# タイトル
# -----------------------------
st.title("看護業務 15分単位 記録アプリ")

# -----------------------------
# 基本情報
# -----------------------------
ward_name = st.text_input(
    "病棟名称",
    value=st.session_state.get("ward_name", "")
)

nurse_id = st.text_input(
    "看護師ID（イニシャル等でも可）",
    value=st.session_state.get("nurse_id", "")
)

selected_date = st.date_input(
    "日付を選択",
    value=date.today()
)

# session保持
st.session_state["ward_name"] = ward_name
st.session_state["nurse_id"] = nurse_id

st.markdown("""
1日24時間を15分刻みで入力します。  
途中保存可能です。  
提出時はデスクトップへCSV保存されます。
""")

st.divider()

# -----------------------------
# 下書き操作
# -----------------------------
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("途中保存"):
        save_draft()
        st.success(f"途中保存しました：{DRAFT_FILE.resolve()}")

with col2:
    if st.button("途中保存を読込"):
        load_draft()
        st.success("途中保存を読み込みました")

with col3:
    if st.button("途中保存削除"):
        delete_draft()
        st.success("途中保存を削除しました")

st.divider()

# -----------------------------
# 15分入力
# -----------------------------
st.subheader("15分ごとの業務入力")

for hour in range(24):

    with st.expander(f"{hour:02d}:00 ～ {hour:02d}:59"):

        for minute in [0, 15, 30, 45]:

            start_label = f"{hour:02d}:{minute:02d}"

            end_hour = hour
            end_min = minute + 15

            if end_min == 60:
                end_min = 0
                end_hour += 1

            if end_hour >= 24:
                end_label = "24:00"
            else:
                end_label = f"{end_hour:02d}:{end_min:02d}"

            state_key = f"{selected_date}_{hour}_{minute}"

            selected_tasks = st.multiselect(
                f"{start_label} ～ {end_label}",
                options=TASK_TYPES,
                key=state_key
            )

            if len(selected_tasks) > 3:
                st.warning("最大3つまでです")
                st.session_state[state_key] = selected_tasks[:3]

st.divider()

# -----------------------------
# 提出
# -----------------------------
if st.button("提出"):

    if ward_name == "":
        st.warning("病棟名称を入力してください")
        st.stop()

    if nurse_id == "":
        st.warning("看護師IDを入力してください")
        st.stop()

    records = []

    for hour in range(24):

        for minute in [0, 15, 30, 45]:

            start_label = f"{hour:02d}:{minute:02d}"

            end_hour = hour
            end_min = minute + 15

            if end_min == 60:
                end_min = 0
                end_hour += 1

            if end_hour >= 24:
                end_label = "24:00"
            else:
                end_label = f"{end_hour:02d}:{end_min:02d}"

            state_key = f"{selected_date}_{hour}_{minute}"

            selected_tasks = st.session_state.get(state_key, [])

            if not selected_tasks:
                continue

            minutes_per_task = 15 / len(selected_tasks)

            for task in selected_tasks:

                records.append({
                    "病棟名称": ward_name,
                    "日付": selected_date.isoformat(),
                    "看護師ID": nurse_id,
                    "開始": start_label,
                    "終了": end_label,
                    "業務種別": task,
                    "この業務に割り当てた時間(分)": minutes_per_task
                })

    if not records:
        st.warning("入力データがありません")
        st.stop()

    # DataFrame化
    df_daily = pd.DataFrame(records)

    # 累積CSV保存
    append_daily_data(df_daily)

    # 個別CSV保存
    daily_file = DESKTOP / f"nursing_{selected_date}_{nurse_id}.csv"

    df_daily.to_csv(
        daily_file,
        index=False,
        encoding="utf-8-sig"
    )

    # 下書き削除
    delete_draft()

    # 表示
    st.success("提出完了")

    st.success(f"""
累積CSV保存先：
{DATA_FILE.resolve()}
""")

    st.success(f"""
提出データ保存先：
{daily_file.resolve()}
""")

    st.dataframe(df_daily, width="stretch")

    summary = (
        df_daily.groupby("業務種別")[
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
