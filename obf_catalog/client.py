"""Open Badge Factory REST API の薄いクライアント。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Iterator

import requests

DEFAULT_API_BASE = "https://openbadgefactory.com"


class OBFError(RuntimeError):
    """API 呼び出しが失敗したときに送出する。"""


@dataclass
class OBFClient:
    """OBF の Client API を叩くための最小限のクライアント。

    OBF は client_id / client_secret を access token に交換したうえで、
    以降のリクエストに ``Authorization: Bearer <token>`` を付ける方式をとる。
    """

    client_id: str
    client_secret: str
    api_base: str = DEFAULT_API_BASE
    timeout: float = 30.0

    def __post_init__(self) -> None:
        self.api_base = self.api_base.rstrip("/")
        self._session = requests.Session()
        self._token: str | None = None

    # ------------------------------------------------------------------ auth

    @classmethod
    def from_env(cls, env_file: str | os.PathLike[str] | None = None) -> "OBFClient":
        """環境変数 (OBF_CLIENT_ID / OBF_CLIENT_SECRET / OBF_API_BASE) から生成する。

        カレントディレクトリから遡って `.env` を探し、あれば読み込む。
        すでに設定済みの環境変数は上書きしない（CI の Secrets を優先させるため）。
        """
        try:
            from dotenv import load_dotenv
        except ImportError:  # .env を使わず環境変数だけで運用する場合は無くてもよい
            if env_file:
                raise OBFError("--env-file を使うには python-dotenv が必要です") from None
        else:
            load_dotenv(dotenv_path=env_file, override=False)
        client_id = os.environ.get("OBF_CLIENT_ID")
        client_secret = os.environ.get("OBF_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise OBFError(
                "OBF_CLIENT_ID と OBF_CLIENT_SECRET を .env か環境変数に設定してください "
                "(.env.example を参照)"
            )
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            api_base=os.environ.get("OBF_API_BASE", DEFAULT_API_BASE),
        )

    @property
    def token(self) -> str:
        if self._token is None:
            self._token = self._fetch_token()
        return self._token

    def _fetch_token(self) -> str:
        url = f"{self.api_base}/v1/client/oauth2/token"
        res = self._session.post(
            url,
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=self.timeout,
        )
        if res.status_code != 200:
            raise OBFError(f"トークン取得に失敗しました ({res.status_code}): {res.text[:200]}")
        try:
            return res.json()["access_token"]
        except (ValueError, KeyError) as exc:
            raise OBFError(f"トークン応答を解釈できません: {res.text[:200]}") from exc

    # ------------------------------------------------------------------- http

    def _get(self, path: str, **params: Any) -> requests.Response:
        url = f"{self.api_base}{path}"
        res = self._session.get(
            url,
            params={k: v for k, v in params.items() if v is not None},
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=self.timeout,
        )
        if res.status_code != 200:
            raise OBFError(f"GET {path} に失敗しました ({res.status_code}): {res.text[:200]}")
        return res

    @staticmethod
    def _parse_multi(text: str) -> list[dict[str, Any]]:
        """OBF は一覧系で JSON 配列と NDJSON のどちらも返しうるので両方を受ける。"""
        text = text.strip()
        if not text:
            return []
        try:
            data = json.loads(text)
        except ValueError:
            pass
        else:
            return data if isinstance(data, list) else [data]

        items: list[dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                items.append(json.loads(line))
        return items

    # ------------------------------------------------------------------- api

    def list_badges(
        self,
        *,
        draft: int | None = 0,
        external: int | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """クライアントが保有するバッジの一覧を返す。

        draft=0 で下書きを除外する。category を渡すとそのカテゴリのみに絞る。
        """
        res = self._get(
            f"/v1/badge/{self.client_id}",
            draft=draft,
            external=external,
            category=category,
            query=query,
        )
        return self._parse_multi(res.text)

    def get_badge(self, badge_id: str) -> dict[str, Any]:
        """バッジ 1 件の詳細を返す。"""
        res = self._get(f"/v1/badge/{self.client_id}/{badge_id}")
        items = self._parse_multi(res.text)
        if not items:
            raise OBFError(f"バッジが見つかりません: {badge_id}")
        return items[0]

    def iter_badge_details(self, badges: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
        """一覧の各要素について詳細を取り直して返す。

        一覧応答にも大半のフィールドは含まれるが、criteria_html など詳細側にしか
        入らない項目があるため、詳細ページ生成では取り直す。
        """
        for badge in badges:
            badge_id = badge.get("id")
            if not badge_id:
                continue
            detail = dict(badge)
            detail.update(self.get_badge(badge_id))
            yield detail

    def download(self, url: str) -> bytes:
        """バッジ画像などのバイナリを取得する。"""
        headers = {}
        if url.startswith(self.api_base):
            headers["Authorization"] = f"Bearer {self.token}"
        res = self._session.get(url, headers=headers, timeout=self.timeout)
        if res.status_code != 200:
            raise OBFError(f"ダウンロードに失敗しました ({res.status_code}): {url}")
        return res.content
