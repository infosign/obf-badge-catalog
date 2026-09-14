# obf-badge-catalog

Open Badge Factory (OBF) の REST API からバッジ情報を取得し、
**静的な HTML のバッジカタログ**を生成する Python サンプルスクリプトです。

- 一覧ページ (`index.html`): バッジ画像とタイトルが並ぶ。キーワードでの絞り込みと並び替えができる
- 詳細ページ (`badge-<id>.html`): クリックすると API で取得した説明・カテゴリ・タグ・有効期間・認定基準を表示

HTML は class 属性を使わないシンプルな構造で、見た目は要素セレクタだけで書いた
`style.css` が担っています。既存サイトのデザインに合わせるときは、
CSS を差し替えるか `<link>` を自社の CSS に向けるだけで済みます。

## 必要なもの

- Python 3.10 以上
- `requests`, `Jinja2`, `python-dotenv`

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 認証情報の設定

OBF の管理画面（Admin tools > API key）で発行した API key から得られる
`client_id` / `client_secret` を環境変数に設定します。

```bash
cp .env.example .env      # 中身を編集
```

`.env` はカレントディレクトリから上位へ遡って自動的に読み込まれます
（`--env-file` で明示指定も可）。
すでに設定済みの環境変数は上書きしないため、GitHub Actions などで
Secrets を環境変数として渡す運用でもそのまま動きます。
`.env` は `.gitignore` に入れてあります。コミットしないでください。

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
| `--env-file FILE` | 読み込む `.env` のパス |
| `--category NAME` | 指定カテゴリのバッジだけに絞る |
| `--include-drafts` | 下書きバッジも含める（既定は除外） |
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
    style.css            スタイル（生成時に出力先へコピーされる）
    catalog.js           一覧ページの絞り込みと並び替え（同上）
sample_data/badges.json  API を叩かずに試すためのダミーデータ
tests/test_basic.py      最小限の回帰テスト
```

## カスタマイズの勘所

- **見た目**: `templates/style.css` を編集します。HTML 側には class を置かず、要素セレクタだけでスタイルを当てています（例外は一覧のグリッドに使う `#badges` のみ）。既存サイトの CSS に載せ替える場合は `base.html` の `<link>` を差し替えてください。ダークモードは `prefers-color-scheme` で自動的に切り替わります。
- **項目の増減**: `generate.py` の `normalize()` で API の応答をテンプレート向けに整えています。表示したいフィールドはここで足します。
- **認定基準 HTML**: `criteria_html` は OBF 側で編集された HTML をエスケープせず埋め込んでいます（`badge.html` の `| safe`）。自組織のデータを信頼する前提なので、外部から取り込んだバッジを混ぜる場合はサニタイズを検討してください。

## 一覧ページの絞り込みと並び替え

一覧ページには、素の JavaScript（ビルド不要・ライブラリなし）で次の機能を入れてあります。

- **絞り込み**: 入力欄に文字を入れると、バッジ名・説明・タグ・カテゴリを対象に絞り込む
- **並び替え**: 名前 / 作成日 / 更新日 の昇順・降順。既定は名前の昇順

バッジの情報は各 `<li>` の `data-` 属性に埋め込んであるため、
別ファイルの JSON を読み込む必要がありません。`file://` で開いても動きます。

JavaScript が無効な環境では操作 UI 自体が表示されず、
名前の昇順で静的に並んだ一覧がそのまま読めます。

並び替えは `Intl.Collator("ja")` を使っていますが、
漢字の読み仮名までは考慮できません（OBF に読み仮名の項目がないため）。
厳密な五十音順が必要な場合は、バッジ名の先頭にソート用の記号を入れるなどの運用が要ります。

## 画像の扱い

バッジ画像は必ず `dist/assets/` へ保存し、HTML からは相対パスで参照します。
OBF 上の画像 URL を直接埋め込むと、公開後の表示が OBF 側の設定に依存してしまうためです。
生成物一式をそのまま配布・設置できる状態を保っています。

## テスト

```bash
pip install pytest
python -m pytest tests
```

## ライセンス

MIT License / Copyright (c) 2026 Infosign, Inc.

詳細は [LICENSE](LICENSE) を参照してください。
