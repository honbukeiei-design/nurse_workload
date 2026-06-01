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

EDITOR_HEIGHT = 500
ROW_HEIGHT = 35

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


def create_empty_grid():
    rows = []

    for _ in TASK_TYPES:
        row = {}

        for t in TIME_SLOTS:
            row[t] = False

        rows.append(row)

    return pd.DataFrame(rows)


def timeline_to_grid(timeline_data):
    df = create_empty_grid()

    for task, times in timeline_data.items():
        if task not in TASK_TYPES:
            continue

        idx = TASK_TYPES.index(task)

        for t in times:
            if t in TIME_SLOTS:
                df.at[idx, t] = True

    return df


def grid_to_timeline(df):
    timeline = {}

    for idx, row in df.iterrows():
        task = TASK_TYPES[idx]
        selected_times = []

        for t in TIME_SLOTS:
            if bool(row[t]):
                selected_times.append(t)

        if selected_times:
            timeline[task] = selected_times

    return timeline


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

if "editor_df" not in st.session_state:
    st.session_state["editor_df"] = timeline_to_grid(
        st.session_state["timeline_data"]
    )

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

st.info(
    "右側タイムラインと左側業務種別の上下スクロールを連動します。"
    "横スクロール位置は上下スクロール時に保持されます。"
)

st.markdown(
    f"""
    <style>
    section.main > div {{
        max-width: 100%;
        padding-left: 1rem;
        padding-right: 1rem;
    }}

    div[data-testid="stHorizontalBlock"] {{
        position: sticky;
        top: 0;
        background: white;
        z-index: 1000;
        padding: 8px 0;
        border-bottom: 1px solid #ddd;
    }}

    .task-panel {{
        height: {EDITOR_HEIGHT}px;
        overflow-y: auto;
        overflow-x: hidden;
        border: 1px solid #ddd;
        border-radius: 8px;
        background: #f7f7f7;
    }}

    .task-panel::-webkit-scrollbar {{
        width: 10px;
    }}

    .task-panel::-webkit-scrollbar-thumb {{
        background: #999;
        border-radius: 8px;
    }}

    .task-header {{
        height: 38px;
        line-height: 38px;
        padding-left: 10px;
        font-weight: 700;
        background: #e8e8e8;
        border-bottom: 1px solid #ccc;
        position: sticky;
        top: 0;
        z-index: 20;
    }}

    .task-row {{
        height: {ROW_HEIGHT}px;
        line-height: {ROW_HEIGHT}px;
        padding-left: 10px;
        border-bottom: 1px solid #e1e1e1;
        font-size: 14px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    div[data-testid="stDataFrame"] {{
        height: {EDITOR_HEIGHT}px !important;
        border: 1px solid #ddd;
        border-radius: 8px;
        overflow: hidden;
    }}

    div[data-testid="stDataFrame"] div[role="columnheader"] {{
        position: sticky !important;
        top: 0 !important;
        z-index: 50 !important;
        background: #eeeeee !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        border-bottom: 2px solid #aaa !important;
    }}

    div[data-testid="stDataFrame"] div[role="gridcell"] {{
        padding: 0 !important;
        min-width: 48px !important;
        min-height: {ROW_HEIGHT}px !important;
    }}

    div[data-testid="stDataFrame"] div[role="row"] {{
        min-height: {ROW_HEIGHT}px !important;
    }}

    div[data-testid="stDataFrame"] input[type="checkbox"] {{
        width: 28px !important;
        height: 28px !important;
        transform: scale(1.35);
        cursor: pointer;
        accent-color: #1e88e5;
    }}

    div[data-testid="stDataFrame"] label {{
        width: 100% !important;
        height: 100% !important;
        min-height: {ROW_HEIGHT}px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
    }}

    @media screen and (max-width: 900px) {{
        section.main > div {{
            padding-left: 0.4rem;
            padding-right: 0.4rem;
        }}

        .task-row {{
            font-size: 12px;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    clear_clicked = st.button("全消去", use_container_width=True)

with col2:
    save_clicked = st.button("途中保存", use_container_width=True)

with col3:
    load_clicked = st.button("途中保存読込", use_container_width=True)

with col4:
    delete_clicked = st.button("途中保存削除", use_container_width=True)

if clear_clicked:
    st.session_state["timeline_data"] = {}
    st.session_state["editor_df"] = create_empty_grid()
    st.success("入力内容を全消去しました。")
    st.rerun()

if load_clicked:
    load_draft()
    st.session_state["editor_df"] = timeline_to_grid(
        st.session_state.get("timeline_data", {})
    )
    st.success("途中保存を読み込みました。")
    st.rerun()

if delete_clicked:
    delete_draft()
    st.session_state["timeline_data"] = {}
    st.session_state["editor_df"] = create_empty_grid()
    st.success("途中保存を削除しました。")
    st.rerun()

column_config = {}

for t in TIME_SLOTS:
    label = t if t.endswith(":00") else t[-2:]
    column_config[t] = st.column_config.CheckboxColumn(
        label,
        width="small",
        help=t
    )

left_col, right_col = st.columns([1.3, 8.7], gap="small")

with left_col:
    task_html = """
    <div class="task-panel" id="task-panel">
        <div class="task-header">業務種別</div>
    """

    for task in TASK_TYPES:
        task_html += f'<div class="task-row">{task}</div>'

    task_html += "</div>"

    st.markdown(task_html, unsafe_allow_html=True)

with right_col:
    with st.form("timeline_input_form", clear_on_submit=False):

        edited_df = st.data_editor(
            st.session_state["editor_df"],
            hide_index=True,
            use_container_width=True,
            height=EDITOR_HEIGHT,
            column_order=TIME_SLOTS,
            column_config=column_config,
            key="timeline_editor",
            num_rows="fixed"
        )

        reflect_clicked = st.form_submit_button(
            "入力内容を反映",
            type="primary",
            use_container_width=True
        )

components.html(
    """
    <script>
    (function() {
        let isSyncing = false;
        let lastKnownScrollLeft = 0;
        let attachedEditor = null;
        let attachedTaskPanel = null;

        function getDoc() {
            return window.parent.document;
        }

        function findTaskPanel() {
            return getDoc().querySelector('#task-panel');
        }

        function isScrollableY(el) {
            if (!el) return false;
            const style = window.parent.getComputedStyle(el);
            return (
                (style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                el.scrollHeight > el.clientHeight + 20
            );
        }

        function isScrollableX(el) {
            if (!el) return false;
            const style = window.parent.getComputedStyle(el);
            return (
                (style.overflowX === 'auto' || style.overflowX === 'scroll') &&
                el.scrollWidth > el.clientWidth + 20
            );
        }

        function findEditorScrollElement() {
            const doc = getDoc();
            const frames = Array.from(doc.querySelectorAll('div[data-testid="stDataFrame"]'));

            let best = null;
            let bestScore = 0;

            for (const frame of frames) {
                const descendants = Array.from(frame.querySelectorAll('*'));

                for (const el of descendants) {
                    const hasY = isScrollableY(el);
                    const hasX = isScrollableX(el);

                    if (!hasY && !hasX) continue;

                    const score =
                        (hasY ? 1000 : 0) +
                        (hasX ? 500 : 0) +
                        el.scrollHeight +
                        el.scrollWidth;

                    if (score > bestScore) {
                        best = el;
                        bestScore = score;
                    }
                }
            }

            return best;
        }

        function syncVertical(source, target) {
            if (!source || !target) return;
            if (isSyncing) return;

            isSyncing = true;

            const preservedLeft = attachedEditor ? attachedEditor.scrollLeft : lastKnownScrollLeft;

            target.scrollTop = source.scrollTop;

            if (attachedEditor) {
                attachedEditor.scrollLeft = preservedLeft;
                lastKnownScrollLeft = preservedLeft;
            }

            window.setTimeout(function() {
                isSyncing = false;
            }, 30);
        }

        function attachSync() {
            const taskPanel = findTaskPanel();
            const editorScroll = findEditorScrollElement();

            if (!taskPanel || !editorScroll) {
                window.setTimeout(attachSync, 500);
                return;
            }

            if (attachedEditor === editorScroll && attachedTaskPanel === taskPanel) {
                return;
            }

            attachedEditor = editorScroll;
            attachedTaskPanel = taskPanel;
            lastKnownScrollLeft = editorScroll.scrollLeft || 0;

            editorScroll.addEventListener('scroll', function() {
                const currentLeft = editorScroll.scrollLeft;

                if (currentLeft !== lastKnownScrollLeft) {
                    lastKnownScrollLeft = currentLeft;
                }

                syncVertical(editorScroll, taskPanel);

                if (editorScroll.scrollLeft !== lastKnownScrollLeft) {
                    editorScroll.scrollLeft = lastKnownScrollLeft;
                }
            }, { passive: true });

            taskPanel.addEventListener('scroll', function() {
                syncVertical(taskPanel, editorScroll);

                if (attachedEditor) {
                    attachedEditor.scrollLeft = lastKnownScrollLeft;
                }
            }, { passive: true });

            editorScroll.addEventListener('wheel', function() {
                lastKnownScrollLeft = editorScroll.scrollLeft;
            }, { passive: true });

            editorScroll.addEventListener('touchmove', function() {
                lastKnownScrollLeft = editorScroll.scrollLeft;
            }, { passive: true });
        }

        function watchDomChanges() {
            const doc = getDoc();

            const observer = new MutationObserver(function() {
                window.setTimeout(attachSync, 300);
            });

            observer.observe(doc.body, {
                childList: true,
                subtree: true
            });
        }

        window.setTimeout(attachSync, 800);
        window.setTimeout(attachSync, 1500);
        window.setTimeout(attachSync, 2500);
        watchDomChanges();
    })();
    </script>
    """,
    height=0,
)

if reflect_clicked:
    st.session_state["editor_df"] = edited_df.copy()
    st.session_state["timeline_data"] = grid_to_timeline(edited_df)

    records = build_records(
        st.session_state["timeline_data"],
        ward_name,
        nurse_id,
        selected_date
    )

    if records:
        st.success(
            f"入力内容を反映しました。現在 {len(records)} 件、合計 {len(records) * 15} 分です。"
        )
    else:
        st.warning("入力内容がありません。チェックを入れてから反映してください。")

if save_clicked:
    save_draft()

    records = build_records(
        st.session_state.get("timeline_data", {}),
        ward_name,
        nurse_id,
        selected_date
    )

    st.success(
        f"途中保存しました。現在 {len(records)} 件、合計 {len(records) * 15} 分です。"
    )

records = build_records(
    st.session_state.get("timeline_data", {}),
    ward_name,
    nurse_id,
    selected_date
)

st.subheader("入力状況")

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

    st.subheader("業務集計")
    st.dataframe(summary, use_container_width=True)

else:
    st.warning("まだ反映済みの入力がありません。チェック後に「入力内容を反映」を押してください。")

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
        st.warning("入力データがありません。チェック後に「入力内容を反映」を押してから提出してください。")
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
