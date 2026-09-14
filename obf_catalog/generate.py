"""バッジカタログの静的 HTML を生成する。

使い方:
    python -m obf_catalog.generate --out dist
    python -m obf_catalog.generate --out dist --input sample_data/badges.json  # API を叩かない
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .client import OBFClient, OBFError

TEMPLATE_DIR = Path(__file__).parent / "templates"
DATA_URI_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<payload>.+)$", re.DOTALL)
MIME_EXT = {"image/png": ".png", "image/svg+xml": ".svg", "image/jpeg": ".jpg", "image/gif": ".gif"}


# --------------------------------------------------------------------- helpers


def slugify(value: str) -> str:
    """ファイル名に使える文字列へ落とす。バッジ ID は英数字想定だが念のため。"""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return slug or "badge"


def badge_page_name(badge: dict[str, Any]) -> str:
    return f"badge-{slugify(str(badge.get('id', '')))}.html"


def normalize(badge: dict[str, Any]) -> dict[str, Any]:
    """テンプレートが扱いやすい形に整える。"""
    tags = badge.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    categories = badge.get("category") or []
    if isinstance(categories, str):
        categories = [categories]

    return {
        **badge,
        "id": str(badge.get("id", "")),
        "name": badge.get("name") or "(名称未設定)",
        "description": badge.get("description") or "",
        "criteria_html": badge.get("criteria_html") or "",
        "criteria_url": badge.get("criteria") or badge.get("criteria_url") or "",
        "tags": list(tags),
        "categories": list(categories),
        "page": badge_page_name(badge),
        "image_src": badge.get("image") or "",
    }


def save_image(badge: dict[str, Any], assets_dir: Path, client: OBFClient | None) -> str | None:
    """バッジ画像をローカルへ保存し、HTML から参照する相対パスを返す。"""
    image = badge.get("image")
    if not image:
        return None

    match = DATA_URI_RE.match(image)
    if match:
        ext = MIME_EXT.get(match.group("mime"), ".png")
        data = base64.b64decode(match.group("payload"))
    elif image.startswith(("http://", "https://")):
        if client is None:
            return None  # API なしのオフライン生成では外部 URL をそのまま使う
        data = client.download(image)
        suffix = Path(image.split("?", 1)[0]).suffix.lower()
        ext = suffix if suffix in set(MIME_EXT.values()) else ".png"
    else:
        return None

    assets_dir.mkdir(parents=True, exist_ok=True)
    path = assets_dir / f"{slugify(str(badge.get('id', '')))}{ext}"
    path.write_bytes(data)
    return f"assets/{path.name}"


# ------------------------------------------------------------------- rendering


def build_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_site(
    badges: Iterable[dict[str, Any]],
    out_dir: Path,
    *,
    site_title: str,
    site_description: str,
    client: OBFClient | None,
) -> list[dict[str, Any]]:
    env = build_env()
    out_dir.mkdir(parents=True, exist_ok=True)

    prepared: list[dict[str, Any]] = []
    for raw in badges:
        badge = normalize(raw)
        local = save_image(raw, out_dir / "assets", client)
        if local:
            badge["image_src"] = local
        prepared.append(badge)

    prepared.sort(key=lambda b: b["name"])

    index_tpl = env.get_template("index.html")
    (out_dir / "index.html").write_text(
        index_tpl.render(
            badges=prepared,
            site_title=site_title,
            site_description=site_description,
        ),
        encoding="utf-8",
    )

    badge_tpl = env.get_template("badge.html")
    for badge in prepared:
        (out_dir / badge["page"]).write_text(
            badge_tpl.render(badge=badge, site_title=site_title),
            encoding="utf-8",
        )

    shutil.copyfile(TEMPLATE_DIR / "style.css", out_dir / "style.css")
    return prepared


# ------------------------------------------------------------------------ cli


def load_badges(args: argparse.Namespace) -> tuple[list[dict[str, Any]], OBFClient | None]:
    if args.input:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        badges = data if isinstance(data, list) else data.get("badges", [])
        return badges, None

    client = OBFClient.from_env(env_file=args.env_file)
    listed = client.list_badges(draft=0 if not args.include_drafts else None, category=args.category)
    badges = list(client.iter_badge_details(listed))
    if args.dump:
        Path(args.dump).write_text(
            json.dumps(badges, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return badges, client


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open Badge Factory のバッジカタログを静的生成する")
    parser.add_argument("--out", default="dist", help="出力ディレクトリ (既定: dist)")
    parser.add_argument("--input", help="API の代わりに読み込む JSON ファイル")
    parser.add_argument("--dump", help="API から取得した JSON をこのパスへ保存する")
    parser.add_argument("--env-file", help="読み込む .env のパス (既定: 上位ディレクトリを探索)")
    parser.add_argument("--category", help="このカテゴリのバッジだけに絞る")
    parser.add_argument("--include-drafts", action="store_true", help="下書きバッジも含める")
    parser.add_argument("--title", default="オープンバッジカタログ", help="サイトタイトル")
    parser.add_argument(
        "--description",
        default="当組織が発行しているオープンバッジの一覧です。",
        help="一覧ページのリード文",
    )
    args = parser.parse_args(argv)

    try:
        badges, client = load_badges(args)
    except OBFError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    prepared = render_site(
        badges,
        out_dir,
        site_title=args.title,
        site_description=args.description,
        client=client,
    )
    print(f"{len(prepared)} 件のバッジを {out_dir}/ に生成しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
