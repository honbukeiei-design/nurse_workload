import streamlit as st
import pandas as pd
from datetime import date, datetime
from pathlib import Path
import json
import re
import smtplib
from email.message import EmailMessage
from email.utils import parseaddr


st.set_page_config(
    page_title="看護業務 15分単位 記録アプリ",
    layout="centered"
)

SAVE_DIR = Path("data")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

DATA_FILE = SAVE_DIR / "nurse_15min_log.csv"
DRAFT_FILE = SAVE_DIR / "nurse_draft.json"

TASK_TYPES = [
    "身体の清潔", "入退院時の世話", "与薬（注射除く）", "食事の世話", "観察",
    "患者の移送", "排泄の世話", "身の回りの世話", "安全の確保", "安楽",
    "自立の援助", "終末看護", "診療、治療の介助", "呼吸循環管理", "測定",
    "諸検査", "医師への報告・連絡", "NS間の報告・申し継ぎ",
    "患者および家族との連絡", "記録", "家族の指導、相談",
    "看護職員・看護学生の指導", "薬剤業務", "物品管理",
    "医療器具・材料の取り扱い", "病室内の環境整備", "病室外の環境整備",
    "ナースコール", "病棟外の連絡", "電話による連絡", "メッセンジャー業務",
    "事務業務", "管理業務", "職員の健康管理", "ME機器の管理", "その他",
]


def ascii_safe_text(text):
    text = str(text).strip()
    text = re.sub(r"[^A-Za-z0-9_-]", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or "unknown"


def clean_email(value):
    _, addr = parseaddr(str(value))
    return addr.strip()


def make_csv_filename(selected_date, ward_name, nurse_id):
    ward = ascii_safe_text(ward_name)
    nurse = ascii_safe_text(nurse_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{selected_date}_{ward}_{nurse}_nursing_work_{timestamp}.csv"


def load_all_data():
    if DATA_FILE.exists():
        try:
            return pd.read_csv(DATA_FILE, encoding="utf-8-sig")
        except Exception:
            return pd.read_csv(DATA_FILE)

    return pd.DataFrame(columns=[
        "病棟名称", "日付", "看護師ID", "開始", "終了",
        "業務種別", "この業務に割り当てた時間(分)"
    ])


def append_daily_data(df_daily):
    df_all = load_all_data()
    df_all = pd.concat([df_all, df_daily], ignore_index=True)
    df_all.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


def save_draft():
    draft = {}
    for key, value in st.session_state.items():
        if isinstance(value, (list, str)):
            draft[key] = value

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


def send_csv_mail(to_email, filename, csv_bytes):
    smtp_host = str(st.secrets["SMTP_HOST"])
    smtp_port = int(st.secrets["SMTP_PORT"])
    smtp_user = clean_email(st.secrets["SMTP_USER"])
    smtp_password = str(st.secrets["SMTP_PASSWORD"])
    mail_from = clean_email(st.secrets["MAIL_FROM"])
    mail_to = clean_email(to_email)

    msg = EmailMessage()

    # 重要：メールヘッダーは完全に英数字のみ
    msg["Subject"] = "Nursing work CSV submission"
    msg["From"] = mail_from
    msg["To"] = mail_to

    msg.set_content(
        "Nursing work CSV file is attached.\n\n"
        "This email was sent automatically from the Streamlit app.",
        charset="utf-8"
    )

    # 添付ファイル名も完全にASCII化
    ascii_filename = filename.encode("ascii", errors="ignore").decode("ascii")

    msg.add_attachment(
        csv_bytes,
        maintype="application",
        subtype="octet-stream",
        filename=ascii_filename
    )

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


if "draft_loaded" not in st.session_state:
    load_draft()
    st.session_state["draft_loaded"] = True


st.title("看護業務 15分単位 記録アプリ")

ward_name = st.text_input(
    "病棟名称",
    value=st.session_state.get("ward_name", "")
)

nurse_id = st.text_input(
    "看護師ID",
    value=st.session_state.get("nurse_id", "")
)

submit_email = st.text_input(
    "提出先メールアドレス",
    value=st.session_state.get("submit_email", "")
)

selected_date = st.date_input(
    "日付",
    value=date.today()
)

st.session_state["ward_name"] = ward_name
st.session_state["nurse_id"] = nurse_id
st.session_state["submit_email"] = submit_email

st.markdown("""
1日24時間を15分単位で入力します。  
途中保存が可能です。  
提出時にCSVをメール送信します。
""")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("途中保存"):
        save_draft()
        st.success("途中保存しました")

with col2:
    if st.button("途中保存読込"):
        load_draft()
        st.success("途中保存を読み込みました")

with col3:
    if st.button("途中保存削除"):
        delete_draft()
        st.success("途中保存を削除しました")

st.divider()

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

            end_label = "24:00" if end_hour >= 24 else f"{end_hour:02d}:{end_min:02d}"

            state_key = f"{selected_date}_{hour}_{minute}"

            selected_tasks = st.multiselect(
                f"{start_label} ～ {end_label}",
                options=TASK_TYPES,
                key=state_key
            )

            if len(selected_tasks) > 3:
                st.error("選択は最大3つまでです")

st.divider()

if st.button("提出"):

    if not ward_name:
        st.warning("病棟名称を入力してください")
        st.stop()

    if not nurse_id:
        st.warning("看護師IDを入力してください")
        st.stop()

    if not submit_email:
        st.warning("提出先メールアドレスを入力してください")
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

            end_label = "24:00" if end_hour >= 24 else f"{end_hour:02d}:{end_min:02d}"

            state_key = f"{selected_date}_{hour}_{minute}"
            selected_tasks = st.session_state.get(state_key, [])

            if len(selected_tasks) > 3:
                st.error(f"{start_label} ～ {end_label} は3つ以下にしてください")
                st.stop()

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

    df_daily = pd.DataFrame(records)

    filename = make_csv_filename(
        selected_date,
        ward_name,
        nurse_id
    )

    csv_text = df_daily.to_csv(
        index=False,
        encoding="utf-8-sig"
    )

    csv_bytes = csv_text.encode("utf-8-sig")

    daily_file = SAVE_DIR / filename

    df_daily.to_csv(
        daily_file,
        index=False,
        encoding="utf-8-sig"
    )

    append_daily_data(df_daily)

    try:
        send_csv_mail(
            to_email=submit_email,
            filename=filename,
            csv_bytes=csv_bytes
        )

        delete_draft()

        st.success("メール送信完了")

        st.success(f"""
送信先：
{submit_email}

添付ファイル：
{filename}
""")

    except Exception as e:
        st.error("メール送信に失敗しました")
        st.error(str(e))

    st.download_button(
        label="CSVダウンロード",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv"
    )

    st.subheader("提出データ")
    st.dataframe(df_daily, width="stretch")

    summary = (
        df_daily.groupby("業務種別")["この業務に割り当てた時間(分)"]
        .sum()
        .round(1)
    )

    st.subheader("業務集計")
    st.dataframe(summary.reset_index(), width="stretch")
