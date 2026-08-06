# コミット生物

このリポジトリの活動(コミット・マージ済みPR・クローズ済みIssue)をエサに、
毎日少しずつ育つ生物です。GitHub Actionsが1日1回状態を更新し、GitHub Pagesの
ダッシュボードで今の姿と実行状況を確認できます。

## しくみ

- `.github/workflows/feed.yml` … 毎日 JST 0:00 に実行される cron ジョブ(手動実行も可)
- `scripts/feed.py` … 過去24時間の活動を集計してスコア化し、状態とSVGを更新
- `data/creature.json` … 生物の状態(EXP・進化段階・履歴)。gitで履歴が残る
- `docs/` … GitHub Pagesとして公開するダッシュボード一式
  - `index.html` … ダッシュボード本体
  - `creature.svg` … 現在の生物の見た目(自動生成)
  - `status.json` … ダッシュボードが読む最新状態(自動生成)

## 成長ルール

| イベント | スコア |
|---|---|
| コミット1件 | +2 |
| PRマージ1件 | +5 |
| Issueクローズ1件 | +3 |
| その日の活動なし | -1 (おなかがすく) |

進化段階(累積EXP): たまご(0) → 幼体(10) → 成体(30) → 進化体(70) → 伝説体(150)

## セットアップ(GitHub上で運用する場合)

1. GitHubに空のリポジトリを作成し、このディレクトリをpushする
2. リポジトリの Settings → Pages で「Deploy from a branch」→ ブランチ `main` / フォルダ `/docs` を選択
3. `docs/index.html` 内の `REPO_SLUG` 定数を `"owner/repo"` の形式で設定する(Actions実行履歴の表示に使用)
4. Settings → Actions → General → Workflow permissions を「Read and write permissions」にする
   (`feed.yml` が状態ファイルをコミット・pushするため)
5. Actions タブから `Feed Creature` を手動実行(workflow_dispatch)して初回動作を確認

## ローカルでの確認

```bash
python scripts/feed.py          # 実際の git ログを集計して1回分成長させる
python scripts/feed.py --demo   # 乱数で活動量を模擬(見た目の確認用)
```

ダッシュボードは静的ファイルなので、`docs/` を簡易サーバーで配信して確認できます。

```bash
python -m http.server 8000 --directory docs
```
