"""最小限の回帰テスト。`python -m pytest` で実行する。"""

import json
from pathlib import Path

from obf_catalog.client import OBFClient
from obf_catalog.generate import (
    badge_page_name,
    normalize,
    render_site,
    slugify,
    to_timestamp,
)


def test_parse_multi_accepts_json_array():
    assert OBFClient._parse_multi('[{"id": "a"}]') == [{"id": "a"}]


def test_parse_multi_accepts_ndjson():
    text = '{"id": "a"}\n{"id": "b"}\n'
    assert OBFClient._parse_multi(text) == [{"id": "a"}, {"id": "b"}]


def test_parse_multi_empty():
    assert OBFClient._parse_multi("  ") == []


def test_slugify_strips_unsafe_characters():
    assert slugify("../../etc/passwd") == "etc-passwd"
    assert slugify("!!!") == "badge"


def test_normalize_wraps_scalar_tags():
    badge = normalize({"id": 1, "tags": "solo", "category": "cat"})
    assert badge["tags"] == ["solo"]
    assert badge["categories"] == ["cat"]
    assert badge["page"] == badge_page_name(badge)


def test_to_timestamp_handles_seconds_milliseconds_and_junk():
    assert to_timestamp(1704067200) == 1704067200
    assert to_timestamp(1704067200000) == 1704067200
    assert to_timestamp("1704067200") == 1704067200
    assert to_timestamp(None) == 0
    assert to_timestamp("") == 0


def test_normalize_builds_lowercased_search_text():
    badge = normalize(
        {"id": 1, "name": "Badge A", "description": "Desc", "tags": ["Tag"], "category": "Cat"}
    )
    assert badge["search_text"] == "badge a desc tag cat"


def test_render_site_from_sample_data(tmp_path: Path):
    badges = json.loads(Path("sample_data/badges.json").read_text(encoding="utf-8"))
    prepared = render_site(
        badges,
        tmp_path,
        site_title="テスト",
        site_description="説明",
        client=None,
    )
    assert len(prepared) == len(badges)
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    for badge in prepared:
        assert badge["page"] in index
        assert (tmp_path / badge["page"]).exists()
    assert (tmp_path / "style.css").exists()
    assert (tmp_path / "catalog.js").exists()
    # 絞り込み・並び替えが参照する data 属性が出ていること
    assert 'data-search="' in index
    assert 'data-ctime="' in index
