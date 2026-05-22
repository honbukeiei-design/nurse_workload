import io
import os
import platform
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# -----------------------------
# 基本設定
# -----------------------------
st.set_page_config(page_title="看護業務 15分単位 記録アプリ", layout="centered")

APP_TITLE = "看護業務 15分単位 記録アプリ"
DRAFT_DIR_NAME = ".nurse_15min_log_drafts"

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
# 保存先・ファイル名
# -----------------------------
def get_desktop_path() -> Path:
    """アプリを実行しているPCのデスクトップパスを返す。存在しなければホームフォルダ。"""
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        return desktop

    # 日本語Windows環境などで「デスクトップ」の場合
    jp_desktop = Path.home() / "デスクトップ"
    if jp_desktop.exists():
        return jp_desktop

    return Path.home()


def safe_filename_part(value: str) -> str:
    """ファイル名に使えない文字を置換。"""
    value = value.strip() or "unknown"
    return re.sub(r'[\\/:*?"<>|]+', "_", value)


DESKTOP_DIR = get_desktop_path()
DATA_FILE = DESKTOP_DIR / "nurse_15min_log.csv"
DRAFT_DIR = DESKTOP_DIR / DRAFT_DIR_NAME


# -----------------------------
# CSV 読み書き用ヘルパー
# -----------------------------
def load_all_data() -> pd.DataFrame:
    """ローカルCSVから全データを読み込み（なければ空データフレーム）"""
    columns = ["日付", "看護師ID", "開始", "終了", "業務種別", "この業務に割り当てた時間(分)"]
    if DATA_FILE.exists():
        try:
            return pd.read_csv(DATA_FILE, encoding="utf-8-sig")
        except UnicodeError:
            return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=columns)


def append_daily_data(df_daily: pd.DataFrame) -> None:
    """日次データをCSVに追記"""
    df_all = load_all_data()
    if df_all.empty:
        df_all = df_daily.copy()
    else:
        df_all = pd.concat([df_all, df_daily], ignore_index=True)

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


def save_submitted_file(df_daily: pd.DataFrame, selected_date: date, nurse_id: str) -> Path:
    """提出時点の入力データをデスクトップに個別CSVとして保存"""
    filename = f"nursing_{selected_date.isoformat()}_{safe_filename_part(nurse_id)}_{datetime.now().strftime('%H%M%S')}.csv"
    out_path = DESKTOP_DIR / filename
    df_daily.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def draft_path(selected_date: date, nurse_id: str) -> Path:
    filename = f"draft_{selected_date.isoformat()}_{safe_filename_part(nurse_id)}.csv"
    return DRAFT_DIR / filename


def build_records(selected_date: date, nurse_id: str) -> list[dict]:
    records = []

    for hour in range(24):
        for minute in [0, 15, 30, 45]:
            start_label = f"{hour:02d}:{minute:02d}"

            end_hour = hour
            end_min = minute + 15
            if end_min == 60:
                end_min = 0
                end_hour += 1
            end_label = "24:00" if end_hour >= 24 else f"{end_hour:02d}:{end_min:02d}"

            state_key = f"{selected_date.isoformat()}_{hour:02d}{minute:02d}"
            selected_tasks = st.session_state.get(state_key, [])

            if not selected_tasks:
                continue

            minutes_per_task = 15 / max(len(selected_tasks), 1)

            for task in selected_tasks:
                records.append(
                    {
                        "日付": selected_date.isoformat(),
                        "看護師ID": nurse_id,
                        "開始": start_label,
                        "終了": end_label,
                        "業務種別": task,
                        "この業務に割り当てた時間(分)": minutes_per_task,
                    }
                )

    return records


def save_draft(selected_date: date, nurse_id: str) -> Path | None:
    """途中保存。未入力の場合は空ファイルを作らない。"""
    if not nurse_id:
        return None

    records = build_records(selected_date, nurse_id)
    if not records:
        return None

    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    df_draft = pd.DataFrame(records)
    path = draft_path(selected_date, nurse_id)
    df_draft.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def load_draft_to_session(selected_date: date, nurse_id: str) -> bool:
    """途中保存CSVを読み込み、session_stateに反映"""
    path = draft_path(selected_date, nurse_id)
    if not path.exists():
        return False

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeError:
        df = pd.read_csv(path)

    # いったん当日分の入力状態を消す
    for hour in range(24):
        for minute in [0, 15, 30, 45]:
            key = f"{selected_date.isoformat()}_{hour:02d}{minute:02d}"
            st.session_state[key] = []

    # 同一スロットに複数業務を復元
    for _, row in df.iterrows():
        start = str(row.get("開始", ""))
        task = str(row.get("業務種別", ""))
        if not start or not task:
            continue

        try:
            hour, minute = start.split(":")
            key = f"{selected_date.isoformat()}_{int(hour):02d}{int(minute):02d}"
            current = st.session_state.get(key, [])
            if task not in current:
                st.session_state[key] = current + [task]
        except Exception:
            continue

    return True


def delete_draft(selected_date: date, nurse_id: str) -> None:
    path = draft_path(selected_date, nurse_id)
    if path.exists():
        path.unlink()


def make_daily_csv_bytes(df: pd.DataFrame) -> bytes:
    """ダウンロード用CSV。ブラウザ側に永続保存しないためメモリ上で生成。"""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")


# -----------------------------
# 画面レイアウト
# -----------------------------
st.title(APP_TITLE)
st.caption("ローカル保存版：提出データは、このアプリを実行しているPCのデスクトップにCSV保存されます。")

with st.expander("保存仕様・注意点", expanded=False):
    st.write(
        f"""
- 保存先：`{DESKTOP_DIR}`
- 累積CSV：`{DATA_FILE.name}`
- 途中保存：`{DRAFT_DIR_NAME}` フォルダ内
- 証明書は不要です。ローカルで `streamlit run app.py` として起動すれば、通常は `http://localhost:8501` で動作します。
- GitHubには**コードだけ**を置き、CSVは `.gitignore` で除外します。
- Streamlit Cloud等のWebサーバー上で実行した場合、「デスクトップ」は利用者PCではなくサーバー側を指します。利用者PCのデスクトップへ直接保存したい場合は、各PCでローカル実行してください。
"""
    )

nurse_id = st.text_input("看護師ID（イニシャル等でも可）", value="")
selected_date = st.date_input("日付を選択", value=date.today())

st.markdown(
    """
    1日24時間を15分刻みで区切り、各15分に対して、その時間帯に行っていた業務を最大3つまで選択します。  
    「途中保存」で入力途中の内容をデスクトップ側に保存できます。  
    「提出」で当日の入力データをデスクトップにCSV出力し、累積CSVにも追記します。
    """
)

st.divider()

# -----------------------------
# 途中保存・復元
# -----------------------------
st.subheader("途中保存・復元")

col_draft1, col_draft2, col_draft3 = st.columns(3)

with col_draft1:
    if st.button("途中保存", use_container_width=True):
        if not nurse_id:
            st.warning("看護師IDを入力してください。")
        else:
            saved_path = save_draft(selected_date, nurse_id)
            if saved_path is None:
                st.info("保存する入力データがありません。")
            else:
                st.success(f"途中保存しました：{saved_path}")

with col_draft2:
    if st.button("途中保存を復元", use_container_width=True):
        if not nurse_id:
            st.warning("看護師IDを入力してください。")
        elif load_draft_to_session(selected_date, nurse_id):
            st.success("途中保存データを復元しました。")
            st.rerun()
        else:
            st.info("該当する途中保存データが見つかりません。")

with col_draft3:
    if st.button("途中保存を削除", use_container_width=True):
        if not nurse_id:
            st.warning("看護師IDを入力してください。")
        else:
            delete_draft(selected_date, nurse_id)
            st.success("途中保存データを削除しました。")

st.divider()

# -----------------------------
# 15分ごとの入力UI
# -----------------------------
st.subheader("15分ごとの業務入力")
st.caption("※ 1時間ごとに折りたたみ表示にしています。")

for hour in range(24):
    with st.expander(f"{hour:02d}:00 〜 {hour:02d}:59"):
        for minute in [0, 15, 30, 45]:
            start_label = f"{hour:02d}:{minute:02d}"

            end_hour = hour
            end_min = minute + 15
            if end_min == 60:
                end_min = 0
                end_hour += 1
            end_label = "24:00" if end_hour >= 24 else f"{end_hour:02d}:{end_min:02d}"

            slot_label = f"{start_label} 〜 {end_label}"
            state_key = f"{selected_date.isoformat()}_{hour:02d}{minute:02d}"

            selected_tasks = st.multiselect(
                slot_label,
                options=TASK_TYPES,
                key=state_key,
                help="この15分間に行っていた業務を選択（最大3つ）",
                max_selections=3,
            )

st.divider()

# -----------------------------
# 提出＆ローカルCSV保存
# -----------------------------
st.subheader("提出・CSV保存")

if st.button("提出してデスクトップにCSV保存", type="primary"):
    if nurse_id == "":
        st.warning("看護師IDを入力してください。")
    else:
        records = build_records(selected_date, nurse_id)

        if not records:
            st.info("この日に入力されたデータがありません。")
        else:
            df_daily = pd.DataFrame(records)

            # 1) 提出時点の個別CSVをデスクトップに保存
            submitted_path = save_submitted_file(df_daily, selected_date, nurse_id)

            # 2) 累積CSVにも追記
            append_daily_data(df_daily)

            # 3) 提出後、途中保存を削除
            delete_draft(selected_date, nurse_id)

            st.success("提出データをデスクトップに保存しました。")
            st.write(f"個別CSV：`{submitted_path}`")
            st.write(f"累積CSV：`{DATA_FILE}`")

            st.write("▼ この日の記録")
            st.dataframe(df_daily, width="stretch")

            st.write("▼ この日の業務種別ごとの合計時間（分）")
            summary = (
                df_daily.groupby("業務種別")["この業務に割り当てた時間(分)"]
                .sum()
                .round(1)
            )
            st.dataframe(summary.reset_index(), width="stretch")

            st.download_button(
                label="念のためCSVをダウンロード",
                data=make_daily_csv_bytes(df_daily),
                file_name=f"nursing_{selected_date.isoformat()}_{safe_filename_part(nurse_id)}.csv",
                mime="text/csv",
            )

st.divider()

# -----------------------------
# 月次集計（ローカルCSVから）
# -----------------------------
st.subheader("月次集計")

col1, col2 = st.columns(2)
with col1:
    year = st.number_input(
        "年（例：2026）",
        min_value=2000,
        max_value=2100,
        value=date.today().year,
    )
with col2:
    month = st.number_input(
        "月（1〜12）",
        min_value=1,
        max_value=12,
        value=date.today().month,
    )

if st.button("この年月のデータを集計"):
    df_all = load_all_data()

    if df_all.empty:
        st.info("まだデータファイルがありません。先に日次記録を提出してください。")
    else:
        df_all["日付"] = pd.to_datetime(df_all["日付"], errors="coerce")
        df_all = df_all.dropna(subset=["日付"])

        mask = (df_all["日付"].dt.year == int(year)) & (
            df_all["日付"].dt.month == int(month)
        )
        m_df = df_all[mask].copy()

        if m_df.empty:
            st.info("該当するデータがありませんでした。")
        else:
            st.write("▼ 該当月の全レコード")
            st.dataframe(m_df, width="stretch")

            st.write("▼ 業務種別ごとの合計時間（分）")
            m_summary = (
                m_df.groupby("業務種別")["この業務に割り当てた時間(分)"]
                .sum()
                .round(1)
            )
            st.dataframe(m_summary.reset_index(), width="stretch")
            st.bar_chart(m_summary)

            st.write("▼ 看護師ID × 業務種別 のピボット（合計時間）")
            pivot = pd.pivot_table(
                m_df,
                values="この業務に割り当てた時間(分)",
                index="看護師ID",
                columns="業務種別",
                aggfunc="sum",
            ).fillna(0).round(1)
            st.dataframe(pivot, width="stretch")

            st.download_button(
                label=f"{int(year)}年{int(month)}月のデータをCSVでダウンロード",
                data=make_daily_csv_bytes(m_df),
                file_name=f"nursing_{int(year)}_{int(month):02d}.csv",
                mime="text/csv",
            )
