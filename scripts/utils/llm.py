"""Öğretmen ve yargıç modelleri için ortak istemci: dakika/gün kotası, bekleme, yeniden deneme, istek günlüğü.

09_generate_instructions (öğretmen) ve 10_verify_instructions (yargıç) aynı sınıfı farklı config bölümüyle
kullanır. Ayarlar: provider (gemini | local), model, requests_per_minute, requests_per_day, temperature,
top_p, max_output_tokens, local.{base_url, model}.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

QUOTA_TZ = ZoneInfo("America/Los_Angeles")  # Gemini günlük kotası Pasifik saatiyle gece yarısı sıfırlanır


class DailyQuotaExhausted(Exception):
    pass


class EmptyResponse(Exception):
    """API hata vermeden boş metin döndürdü (pilotta 1/7 istek; aynı istek tekrarlanınca düzgün yanıt geldi)."""


def is_daily_quota(exc: Exception) -> bool:
    text = str(exc)
    return "429" in text and ("PerDay" in text or "per day" in text.lower())


# Ağ hataları (httpx/requests sınıf adları). 20.10.2026'da internet kesintisinde DNS çözülemedi, bağlantı zaman
# aşımına uğradı, sunucu bağlantıyı kesti: bunlar modelin değil bağlantının sorunu, beklenip yeniden denenir.
NETWORK_ERRORS = {"ConnectError", "ConnectTimeout", "ReadError", "ReadTimeout", "WriteError", "WriteTimeout",
                  "PoolTimeout", "RemoteProtocolError", "ConnectionError", "Timeout", "ChunkedEncodingError"}
# Eski hata kayıtlarında (kind alanından önce) API/ağ hatası "SınıfAdı: mesaj" biçiminde yazıldı.
LEGACY_API_ERROR = re.compile(r"^[A-Z]\w*(?:Error|Timeout|Exception): ")
API_ERROR = "api_error"


def is_network_error(exc: Exception) -> bool:
    return any(cls.__name__ in NETWORK_ERRORS for cls in type(exc).__mro__)


def counts_as_attempt(entry: dict[str, Any]) -> bool:
    """Hata kaydı bir deneme sayılır mı? Yalnızca modelin geçersiz çıktısı sayılır; API ve ağ hataları sayılmaz:
    bağlantı koptu diye örnek elenmesin."""
    if entry.get("kind") == API_ERROR:
        return False
    return not LEGACY_API_ERROR.match(entry.get("error", ""))


def is_transient(exc: Exception) -> bool:
    """Dakikalık kota (429), sunucu hataları (5xx) ve ağ hataları beklenip yeniden denenir; günlük kota denenmez."""
    if is_daily_quota(exc):
        return False
    if isinstance(exc, EmptyResponse) or is_network_error(exc):
        return True
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    text = str(exc)
    return code in (429, 500, 502, 503, 504) or any(f"{c} " in text[:6] for c in (429, 500, 502, 503, 504))


class LLMClient:
    def __init__(self, settings: dict[str, Any], log_path: Path, logger, response_schema: dict[str, Any]) -> None:
        self.cfg, self.logger, self.log_path, self.schema = settings, logger, log_path, response_schema
        self.provider = settings["provider"]
        self.model = settings["model"] if self.provider == "gemini" else settings["local"]["model"]
        self.interval = 60.0 / settings["requests_per_minute"]
        self.last = 0.0
        if self.provider == "gemini":
            key = os.getenv("GEMINI_API_KEY", "").strip()
            if not key:
                raise SystemExit("GEMINI_API_KEY bulunamadı. Proje kökündeki .env dosyasına GEMINI_API_KEY=... "
                                 "satırını ekleyin (anahtar: https://aistudio.google.com/apikey).")
            from google import genai
            self.client = genai.Client(api_key=key)
        elif self.provider == "local":
            if not self.model:
                raise SystemExit("provider=local için config'teki local.model boş.")
        else:
            raise SystemExit(f"Bilinmeyen provider: {self.provider}")

    def used_today(self) -> int:
        if not self.log_path.exists():
            return 0
        start = datetime.now(QUOTA_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        used = 0
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry["model"] == self.model and datetime.fromisoformat(entry["timestamp"]) >= start:
                used += 1
        return used

    def _log(self, ok: bool, detail: str = "") -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "model": self.model, "ok": ok, "detail": detail[:200]}) + "\n")

    def generate(self, system: str, user: str) -> str:
        if self.provider == "gemini" and self.used_today() >= self.cfg["requests_per_day"]:
            raise DailyQuotaExhausted()
        return self._call(system, user)

    @retry(retry=retry_if_exception(is_transient), wait=wait_exponential(multiplier=2, min=10, max=120),
           stop=stop_after_attempt(6), reraise=True)
    def _call(self, system: str, user: str) -> str:
        wait = self.interval - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()
        try:
            text = self._request(system, user)
        except Exception as exc:
            self._log(False, f"{type(exc).__name__}: {exc}")
            if is_daily_quota(exc):
                raise DailyQuotaExhausted() from exc
            if is_transient(exc):
                self.logger.warning("Geçici hata, beklenip yeniden denenecek: %s", str(exc)[:150])
            raise
        self._log(True)
        return text

    def _request(self, system: str, user: str) -> str:
        t = self.cfg
        if self.provider == "gemini":
            from google.genai import types
            response = self.client.models.generate_content(
                model=self.model, contents=user,
                config=types.GenerateContentConfig(system_instruction=system, temperature=t["temperature"],
                                                   top_p=t["top_p"], max_output_tokens=t["max_output_tokens"],
                                                   response_mime_type="application/json",
                                                   response_schema=self.schema))
            if not (response.text or "").strip():
                reason = getattr(response.candidates[0], "finish_reason", None) if response.candidates else None
                raise EmptyResponse(f"boş yanıt (finish_reason={reason})")
            return response.text
        import requests
        r = requests.post(t["local"]["base_url"].rstrip("/") + "/chat/completions", timeout=600, json={
            "model": self.model, "temperature": t["temperature"], "top_p": t["top_p"],
            "max_tokens": t["max_output_tokens"], "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------------------------------
# JSONL yardımcıları
# ---------------------------------------------------------------------------------------------------
def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Ekle + flush + fsync: script kesilse de yazılmış kayıtlar diskte kalır (resume bunlara güvenir)."""
    with path.open("a", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Atomik yazma: önce .tmp, sonra yer değiştir."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8", newline="\n")
    tmp.replace(path)
