"""HTTP client for the UN Comtrade API."""

from __future__ import annotations

import re
import time
from functools import lru_cache
from typing import Any

import httpx

from tradenet.settings import Settings, get_settings

FLOW_EXPORT = "X"
FLOW_IMPORT = "M"
VALID_FLOWS = (FLOW_EXPORT, FLOW_IMPORT)
REPORTERS_REFERENCE_URL = "https://comtradeapi.un.org/files/v1/app/reference/Reporters.json"
RETRYABLE_STATUS_CODES = {429, 503}
_RETRY_AFTER_MESSAGE = re.compile(r"try again in (\d+(?:\.\d+)?)\s*seconds?", re.IGNORECASE)


class ComtradeClient:
    """Thin wrapper around the UN Comtrade v1 REST API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = httpx.Client(
            base_url=self.settings.comtrade_base_url.rstrip("/"),
            headers={"User-Agent": self.settings.http_user_agent},
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        self._last_request_at = 0.0

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ComtradeClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_trade_data(
        self,
        *,
        reporter_code: str,
        period: str,
        cmd_code: str,
        flow_code: str,
        partner_code: str | None = None,
        preview: bool = False,
        max_records: int = 250_000,
    ) -> list[dict[str, Any]]:
        if flow_code not in VALID_FLOWS:
            raise ValueError(f"flow_code must be one of {VALID_FLOWS}, got {flow_code!r}")

        path = "/public/v1/preview/C/A/HS" if preview else "/data/v1/get/C/A/HS"
        params: dict[str, str | int] = {
            "reporterCode": reporter_code,
            "period": period,
            "cmdCode": cmd_code,
            "flowCode": flow_code,
            "maxRecords": min(max_records, 500 if preview else max_records),
            "includeDesc": "true",
        }
        if partner_code:
            params["partnerCode"] = partner_code

        headers: dict[str, str] = {}
        if not preview:
            headers["Ocp-Apim-Subscription-Key"] = self.settings.require_subscription_key()

        return self._paginate(path, params, headers, preview=preview)

    def lookup_reporters(self, search: str | None = None) -> list[dict[str, str]]:
        records = _load_reporters()
        if search:
            needle = search.casefold()
            records = [
                row
                for row in records
                if needle in row.get("text", "").casefold()
                or needle in str(row.get("id", "")).casefold()
                or needle in row.get("isoCode", "").casefold()
                or needle in row.get("isoCode2", "").casefold()
            ]
        return records

    def resolve_reporter_code(self, country: str) -> str:
        needle = country.strip()
        if needle.isdigit():
            return needle

        needle_cf = needle.casefold()
        reporters = _load_reporters()

        if len(needle) == 3 and needle.isalpha():
            iso_matches = [
                row for row in reporters if row.get("isoCode", "").casefold() == needle_cf
            ]
            if iso_matches:
                return _prefer_current_reporter(iso_matches)["id"]

        for row in reporters:
            if needle_cf == row.get("text", "").casefold():
                return row["id"]

        raise ValueError(f"Could not resolve country code for {country!r}")

    def _paginate(
        self,
        path: str,
        params: dict[str, str | int],
        headers: dict[str, str],
        *,
        preview: bool,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        page_size = int(params["maxRecords"])

        while True:
            page_params = {**params, "offset": offset}
            payload = self._request_json(path, page_params, headers)
            batch = payload.get("data") or []
            rows.extend(batch)

            if preview or len(batch) < page_size:
                break

            offset += len(batch)

        return rows

    def _throttle(self) -> None:
        delay = self.settings.comtrade_request_delay
        if delay <= 0:
            return

        elapsed = time.monotonic() - self._last_request_at
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def _request_json(
        self,
        path: str,
        params: dict[str, str | int],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        last_error: httpx.HTTPStatusError | None = None

        for attempt in range(self.settings.comtrade_max_retries + 1):
            self._throttle()
            response = self._client.get(path, params=params, headers=headers)
            self._last_request_at = time.monotonic()

            if response.status_code not in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return self._parse_payload(response)

            last_error = httpx.HTTPStatusError(
                f"Rate limited ({response.status_code})",
                request=response.request,
                response=response,
            )
            if attempt >= self.settings.comtrade_max_retries:
                break

            wait_seconds = _retry_after_seconds(response, attempt)
            time.sleep(wait_seconds)

        assert last_error is not None
        raise last_error

    def _parse_payload(self, response: httpx.Response) -> dict[str, Any]:
        payload = response.json()

        if payload.get("errors"):
            messages = "; ".join(str(err) for err in payload["errors"])
            raise RuntimeError(f"Comtrade API error: {messages}")

        if payload.get("error"):
            raise RuntimeError(f"Comtrade API error: {payload['error']}")

        return payload


def _retry_after_seconds(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(float(retry_after), 1.0)
        except ValueError:
            pass

    try:
        message = response.json().get("message", "")
        if match := _RETRY_AFTER_MESSAGE.search(str(message)):
            return max(float(match.group(1)), 1.0)
    except (ValueError, AttributeError):
        pass

    return min(2.0**attempt, 30.0)


@lru_cache
def _load_reporters() -> list[dict[str, str]]:
    response = httpx.get(REPORTERS_REFERENCE_URL, timeout=30.0)
    response.raise_for_status()
    rows = response.json()["results"]
    return [
        {
            "id": str(row["reporterCode"]),
            "text": row["reporterDesc"],
            "isoCode": row.get("reporterCodeIsoAlpha3", ""),
            "isoCode2": row.get("reporterCodeIsoAlpha2", ""),
        }
        for row in rows
        if not row.get("isGroup")
    ]


def _prefer_current_reporter(rows: list[dict[str, str]]) -> dict[str, str]:
    current = [row for row in rows if "(..." not in row.get("text", "")]
    if current:
        return current[-1]
    return rows[-1]
