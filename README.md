# 看護業務 15分単位 記録アプリ

## 使い方

```bash
pip install -r requirements.txt
streamlit run app.py
```

ブラウザで `http://localhost:8501` が開きます。ローカル実行では証明書は不要です。

## 保存仕様

- 提出時の個別CSVは、アプリを実行しているPCのデスクトップに保存されます。
- 累積CSV `nurse_15min_log.csv` もデスクトップに保存されます。
- 途中保存データはデスクトップの `.nurse_15min_log_drafts` フォルダに保存されます。
- `.gitignore` により、CSVや途中保存データはGitHubへアップされない設定です。

## 注意

Streamlit CloudなどWebサーバーで実行すると、「デスクトップ」は利用者のPCではなくサーバー側を指します。利用者PCのデスクトップに直接保存したい場合は、各PCでローカル実行してください。
