# obf-badge-catalog

Open Badge Factory (OBF) の REST API からバッジ情報を取得し、
**静的な HTML のバッジカタログ**を生成する Python サンプルスクリプトです。

- 一覧ページ (`index.html`): バッジ画像とタイトルが並ぶ
- 詳細ページ (`badge-<id>.html`): クリックすると API で取得した説明・カテゴリ・タグ・有効期間・認定基準を表示

出力は CSS を含まない素の HTML です。
既存サイトのデザインに合わせる前提で、テンプレートに手を入れて使ってください。

## 必要なもの

- Python 3.10 以上
- `requests`, `Jinja2`

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 認証情報の設定

OBF の管理画面（Admin tools > API key）で発行した API key から得られる
`client_id` / `client_secret` を環境変数に設定します。

```bash
cp .env.example .env      # 中身を編集
export $(grep -v '^#' .env | xargs)
```

このスクリプトは `client_id` / `client_secret` を
`POST /v1/client/oauth2/token` でアクセストークンに交換し、
以降のリクエストに `Authorization: Bearer <token>` を付けて呼び出します。

## 使い方

API から取得して生成する:

```bash
python -m obf_catalog.generate --out dist
```

API を叩かずサンプルデータで生成する（動作確認・デザイン調整用）:

```bash
python -m obf_catalog.generate --out dist --input sample_data/badges.json
```

生成物はそのまま Web サーバーに置けます。ローカル確認は次のとおり:

```bash
python -m http.server -d dist 8000
```

### 主なオプション

| オプション | 説明 |
| --- | --- |
| `--out DIR` | 出力ディレクトリ（既定 `dist`） |
| `--input FILE` | API の代わりに読み込む JSON ファイル |
| `--dump FILE` | API から取得した JSON を保存する（次回以降 `--input` で再利用できる） |
| `--category NAME` | 指定カテゴリのバッジだけに絞る |
| `--include-drafts` | 下書きバッジも含める（既定は除外） |
| `--no-images` | 画像をローカルに保存せず、API の URL / data URI を直接参照する |
| `--title` / `--description` | ページのタイトルとリード文 |

## 使用している API

| 用途 | エンドポイント |
| --- | --- |
| トークン取得 | `POST /v1/client/oauth2/token` |
| バッジ一覧 | `GET /v1/badge/{client_id}` |
| バッジ詳細 | `GET /v1/badge/{client_id}/{badge_id}` |

一覧系の応答は JSON 配列と NDJSON のどちらの形式でも解釈します。

## ファイル構成

```
obf_catalog/
  client.py              OBF API クライアント（認証・一覧・詳細・画像取得）
  generate.py            HTML 生成の本体と CLI
  templates/
    base.html            全ページ共通の骨組み
    index.html           一覧ページ
    badge.html           詳細ページ
sample_data/badges.json  API を叩かずに試すためのダミーデータ
tests/test_basic.py      最小限の回帰テスト
```

## カスタマイズの勘所

- **見た目**: `templates/*.html` を編集します。`base.html` に `<link rel="stylesheet">` を足せば既存サイトの CSS をそのまま適用できます。
- **項目の増減**: `generate.py` の `normalize()` で API の応答をテンプレート向けに整えています。表示したいフィールドはここで足します。
- **認定基準 HTML**: `criteria_html` は OBF 側で編集された HTML をエスケープせず埋め込んでいます（`badge.html` の `| safe`）。自組織のデータを信頼する前提なので、外部から取り込んだバッジを混ぜる場合はサニタイズを検討してください。

## テスト

```bash
pip install pytest
python -m pytest tests
```

## ライセンス

MIT
