"""FAZ 1: download_manifest.csv'deki dokümanları data/raw/ altına indirir ve registry'ye kaydeder.

Çalıştırma (proje kökünden): python -m scripts.01_download [--config ...] [--limit N]

- pdf / html / txt: `requests` ile indirilir; robots.txt'e uyulur, istekler arasında beklenir.
- pdf + `pages` sütunu: PDF bir kez iner, her sayfa aralığı ayrı doküman olarak kaydedilir.
  Ham dosya bölünmez; aralığı FAZ 2 okur.
- git: depo geçici klasöre klonlanır, `include_glob`'a uyan dosyalardan en fazla `max_files`
  tanesi seed'li seçilip kopyalanır. Seçim ve commit `_git_source.json` içinde saklanır ki
  sonraki çalıştırmalar aynı dosyaları görsün.
- Registry'de zaten olan doküman yeniden indirilmez.
- document_id: her çalıştırmanın sonunda (kaynak adı, dosya yolu, sayfa) sırasına göre verilir;
  böylece aynı manifest, indirmeler hangi sırayla başarılı olursa olsun aynı numaraları üretir.
  Sonraki fazlar başladıktan sonra numaralar sabitlenir, yeni dokümanlar sona eklenir.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import robotparser
from urllib.parse import unquote, urlsplit

import pandas as pd
import requests
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path, set_seed
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import format_document_id, load_registry, save_registry

LOG_COLUMNS = ["document_id", "url", "http_status", "bytes", "sha256", "timestamp", "error"]
URL_TYPES = {"pdf": ".pdf", "html": ".html", "txt": ".txt"}  # manifest type -> dosya uzantısı
GIT_MARKER = "_git_source.json"


class RetryableError(Exception):
    """Yeniden denemeye değer sunucu cevabı (429 veya 5xx)."""


def read_rows(path: Path) -> list[dict[str, str]]:
    """CSV'yi başlık -> değer sözlükleri olarak okur (boş hücre = boş string)."""
    with path.open(encoding="utf-8", newline="") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def rel(path: Path) -> str:
    """Registry'ye yazılacak yol: proje köküne göreli ve / ayraçlı."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_name(url: str, ext: str) -> str:
    """URL'nin son parçasından dosya adı üretir; Windows'un kabul etmediği karakterleri _ yapar."""
    parts = urlsplit(url)
    name = unquote(parts.path.rstrip("/").rsplit("/", 1)[-1]) or parts.netloc
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name if name.lower().endswith(ext) else name + ext


def validate(manifest: list[dict[str, str]], sources: dict[str, dict[str, str]]) -> list[str]:
    """Manifest satırlarındaki hataları toplar; boş liste = sorun yok."""
    errors = []
    for i, row in enumerate(manifest, start=2):  # 1. satır başlık
        where = f"download_manifest.csv satır {i}"
        if row["source_name"] not in sources:
            # Lisans ve external_api_ok yalnızca sources.csv'den gelir; orada olmayan kaynak indirilmez.
            errors.append(f"{where}: '{row['source_name']}' sources.csv içinde yok")
        if row["type"] == "wikipedia":
            errors.append(f"{where}: 'wikipedia' tipi desteklenmiyor; Vikipedi robots.txt'i API yolunu "
                          "(/w/api.php) kapatıyor. Maddeyi 'html' tipiyle ve /wiki/ adresiyle yazın")
        elif row["type"] == "git":
            if not row["include_glob"] or not row["max_files"].isdigit():
                errors.append(f"{where}: git için include_glob ve sayısal max_files zorunlu")
        elif row["type"] not in URL_TYPES:
            errors.append(f"{where}: bilinmeyen type '{row['type']}'")
        pages = row.get("pages", "")
        if pages and (row["type"] != "pdf" or not re.fullmatch(r"\d+-\d+", pages)):
            errors.append(f"{where}: pages yalnızca pdf için ve 'başlangıç-bitiş' biçiminde olabilir")
    return errors


class Downloader:
    """Bekleme, yeniden deneme ve robots.txt kontrolüyle HTTP istekleri yapar."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        d = cfg["download"]
        self.user_agent: str = d["user_agent"]
        self.delay: float = d["delay_seconds"]
        self.timeout: float = d["timeout_seconds"]
        self.max_retries: int = d["max_retries"]
        self.respect_robots: bool = d["respect_robots_txt"]
        self.session = requests.Session()
        self.session.headers["User-Agent"] = self.user_agent
        self._robots: dict[str, robotparser.RobotFileParser] = {}

    def get(self, url: str) -> requests.Response:
        """Her denemeden önce delay_seconds bekler; bağlantı hatası, 429 ve 5xx'te üstel beklemeyle yeniden dener."""
        retrying = Retrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=self.delay),
            retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout, RetryableError)),
            reraise=True,
        )
        for attempt in retrying:
            with attempt:
                time.sleep(self.delay)  # siteyi yormamak için
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 429 or response.status_code >= 500:
                    raise RetryableError(f"HTTP {response.status_code}")
        return response

    def robots_verdict(self, url: str) -> str:
        """Sitenin robots.txt'ine göre karar: 'allowed' | 'blocked_by_robots' | 'robots_unreachable'."""
        if not self.respect_robots:
            return "allowed"
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            rp: robotparser.RobotFileParser | None = robotparser.RobotFileParser()
            try:
                response = self.get(host + "/robots.txt")
                if response.status_code in (401, 403):
                    rp.disallow_all = True      # robots.txt'e erişim yasaksa site kapalı sayılır
                elif response.status_code >= 400:
                    rp.allow_all = True         # robots.txt yoksa kısıt yok
                else:
                    rp.parse(response.text.splitlines())
            except (requests.RequestException, RetryableError):
                rp = None                       # kural okunamadı: izin varsayma, bu çalıştırmada indirme
            self._robots[host] = rp
        rp = self._robots[host]
        if rp is None:
            return "robots_unreachable"
        return "allowed" if rp.can_fetch(self.user_agent, url) else "blocked_by_robots"


class Recorder:
    """Registry'ye doküman satırı ekler ve download_log.csv'ye olay yazar."""

    def __init__(self, cfg: dict[str, Any], sources: dict[str, dict[str, str]]) -> None:
        self.cfg = cfg
        self.sources = sources
        self.log_path = resolve_path(cfg, "download_log")
        self.registry = load_registry(cfg)
        if "pages" not in self.registry.columns:
            self.registry["pages"] = ""
        # Bir dokümanın kimliği: ham dosya yolu + (varsa) sayfa aralığı.
        self.known = set(zip(self.registry["original_path"], self.registry["pages"]))
        numbers = self.registry["document_id"].str.extract(r"(\d+)$")[0].dropna().astype(int)
        self.next_number = int(numbers.max()) + 1 if len(numbers) else 1

    def has(self, path: Path, pages: str = "") -> bool:
        return (rel(path), pages) in self.known

    def add(self, row: dict[str, str], source_type: str, url: str, path: Path, pages: str = "") -> str:
        """Yeni dokümana sıradaki document_id'yi verir, registry'yi atomik olarak kaydeder."""
        document_id = format_document_id(self.next_number)
        self.next_number += 1
        source = self.sources[row["source_name"]]
        new = {
            "document_id": document_id, "source_name": row["source_name"], "source_type": source_type,
            "url": url, "license": source["license"], "external_api_ok": source["external_api_ok"],
            "original_path": rel(path), "language": row["language"], "document_type": row["document_type"],
            "publication_year": row["publication_year"], "status": "downloaded", "pages": pages,
        }
        self.registry = pd.concat([self.registry, pd.DataFrame([new])], ignore_index=True).fillna("")
        self.known.add((rel(path), pages))
        save_registry(self.registry, self.cfg)
        return document_id

    def renumber(self) -> bool:
        """document_id'leri (kaynak adı, dosya yolu, sayfa) sırasına göre baştan verir.

        Numaralar indirme sırasına değil yalnızca içeriğe bağlı olsun diye: bir doküman ilk denemede
        inemeyip sonradan inse bile aynı manifest hep aynı numaraları üretir. Sonraki fazlar numaraları
        kullanmaya başladıysa (status artık 'downloaded' değilse) dokunulmaz.
        """
        if not len(self.registry) or not (self.registry["status"] == "downloaded").all():
            return False
        start_page = self.registry["pages"].str.split("-").str[0].replace("", "0").astype(int)
        order = (self.registry.assign(_page=start_page)
                 .sort_values(["source_name", "original_path", "_page"]).drop(columns="_page").reset_index(drop=True))
        new_ids = [format_document_id(n) for n in range(1, len(order) + 1)]
        mapping = dict(zip(order["document_id"], new_ids))
        order["document_id"] = new_ids
        self.registry = order
        save_registry(self.registry, self.cfg)
        if self.log_path.exists():  # log'daki numaralar registry ile aynı kalsın
            rows = read_rows(self.log_path)
            with self.log_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
                writer.writeheader()
                writer.writerows({**row, "document_id": mapping.get(row["document_id"], row["document_id"])}
                                 for row in rows)
        self.next_number = len(order) + 1
        return True

    def log(self, document_id: str, url: str, http_status: Any, path: Path | None = None, error: str = "") -> None:
        """İndirme olayını ekler. http_status: HTTP kodu, 'git' veya 'local' (dosya zaten diskteydi)."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not self.log_path.exists()
        with self.log_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(LOG_COLUMNS)
            writer.writerow([document_id, url, http_status, path.stat().st_size if path else "",
                             sha256_file(path) if path else "",
                             datetime.now().isoformat(timespec="seconds"), error])


def plan_url_documents(rows: list[dict[str, str]], raw_dir: Path) -> list[dict[str, Any]]:
    """pdf/html/txt satırlarını (dosya adı, sayfa) sırasına dizer; her biri bir dokümandır."""
    docs, names = [], {}
    for row in rows:
        name = safe_name(row["url_or_title"], URL_TYPES[row["type"]])
        # Farklı iki adres aynı dosya adına düşerse biri diğerinin üzerine yazardı.
        if names.setdefault(name, row["url_or_title"]) != row["url_or_title"]:
            raise SystemExit(f"{row['source_name']}: iki farklı adres aynı dosya adını veriyor: {name}")
        pages = row.get("pages", "")
        docs.append({"row": row, "path": raw_dir / row["source_name"] / name, "pages": pages,
                     "sort": (name, int(pages.split("-")[0]) if pages else 0)})
    return sorted(docs, key=lambda d: d["sort"])


def download_url_document(doc: dict[str, Any], downloader: Downloader, recorder: Recorder) -> str:
    """Tek dokümanı indirir ve kaydeder. Döner: 'ok' | 'failed' | 'blocked'."""
    row, path, url = doc["row"], doc["path"], doc["row"]["url_or_title"]
    status: Any = "local"  # dosya diskte: aynı PDF'in başka sayfa aralığı ya da önceki çalıştırma
    if not path.exists():
        verdict = downloader.robots_verdict(url)
        if verdict != "allowed":
            recorder.log("", url, "", error=verdict)
            # Yasak kalıcıdır (elenen); robots.txt'e ulaşılamaması geçicidir (başarısız, sonra yeniden denenir).
            return "blocked" if verdict == "blocked_by_robots" else "failed"
        try:
            response = downloader.get(url)
        except (requests.RequestException, RetryableError) as exc:
            recorder.log("", url, "", error=f"{type(exc).__name__}: {exc}")
            return "failed"
        if response.status_code != 200:
            recorder.log("", url, response.status_code, error=f"HTTP {response.status_code}")
            return "failed"
        if row["type"] == "pdf" and not response.content.startswith(b"%PDF"):
            # Bazı siteler bulunamayan PDF yerine 200 koduyla HTML hata sayfası döndürür.
            recorder.log("", url, response.status_code, error="not_a_pdf")
            return "failed"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(response.content)  # ham bayt: içerik hiçbir şekilde değiştirilmez
        tmp.replace(path)
        status = response.status_code
    document_id = recorder.add(row, row["type"], url, path, doc["pages"])
    recorder.log(document_id, url, status, path)
    return "ok"


def git(*args: str, cwd: Path | None = None) -> str:
    # Windows'ta git satır sonlarını CRLF'ye çevirmesin, ham dosya depodakiyle bayt bayt aynı kalsın.
    # autocrlf tek başına yetmez: deponun .gitattributes dosyası "text" diyorsa core.eol devreye girer.
    result = subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf", *args], cwd=cwd,
                            check=True, capture_output=True, text=True)
    return result.stdout.strip()


def clone(url: str, dest: Path, commit: str | None = None) -> str:
    """Deponun yalnızca tek commit'ini alır; commit verilirse tam o commit'i. Commit kimliğini döndürür."""
    if commit is None:
        git("clone", "--depth", "1", url, str(dest))
    else:
        dest.mkdir(parents=True)
        git("init", "--quiet", cwd=dest)
        git("remote", "add", "origin", url, cwd=dest)
        git("fetch", "--depth", "1", "origin", commit, cwd=dest)
        git("checkout", "--quiet", "FETCH_HEAD", cwd=dest)
    return git("rev-parse", "HEAD", cwd=dest)


def select_files(repo: Path, rows: list[dict[str, str]], seed: int) -> dict[str, list[str]]:
    """Her include_glob için en fazla max_files dosyayı seed'li rastgele seçer.

    Alfabetik ilk N yerine rastgele: seçim dosya adının baş harfine göre yanlı olmasın.
    __init__.py atlanır: paket işaretidir, içerik taşımaz.
    """
    selected: dict[str, list[str]] = {}
    taken: set[str] = set()
    for row in rows:
        files = sorted(p.relative_to(repo).as_posix() for p in repo.glob(row["include_glob"])
                       if p.is_file() and p.name != "__init__.py")
        files = [f for f in files if f not in taken]
        chosen = sorted(random.Random(seed).sample(files, min(int(row["max_files"]), len(files))))
        selected[row["include_glob"]] = chosen
        taken.update(chosen)
    return selected


def download_git_source(url: str, rows: list[dict[str, str]], raw_dir: Path, seed: int,
                        recorder: Recorder, budget: list[int | None]) -> tuple[int, int]:
    """Bir deponun seçilen dosyalarını kopyalar. Döner: (başarılı, başarısız). budget[0]: kalan --limit."""
    source_dir = raw_dir / rows[0]["source_name"]
    marker = source_dir / GIT_MARKER
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        repo, cloned = Path(tmp) / "repo", False
        try:
            if marker.exists():
                meta = json.loads(marker.read_text(encoding="utf-8"))
            else:
                commit = clone(url, repo)
                cloned = True
                meta = {"url": url, "commit": commit, "seed": seed, "selected": select_files(repo, rows, seed)}
                source_dir.mkdir(parents=True, exist_ok=True)
                for license_file in repo.glob("LICENSE*"):
                    shutil.copy2(license_file, source_dir / license_file.name)
                marker.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            if set(meta["selected"]) != {r["include_glob"] for r in rows}:
                raise SystemExit(f"{rows[0]['source_name']}: manifest'teki include_glob'lar {rel(marker)} "
                                 "ile uyuşmuyor. Seçimi yenilemek için o dosyayı kaldırın.")
            ok = 0
            for row in rows:
                for relpath in meta["selected"][row["include_glob"]]:
                    path = source_dir / relpath
                    if recorder.has(path):
                        continue
                    if budget[0] is not None and budget[0] <= 0:
                        return ok, 0
                    if not path.exists():
                        if not cloned:  # seçim önceki çalıştırmada yapılmış: aynı commit'i getir
                            clone(url, repo, meta["commit"])
                            cloned = True
                        path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(repo / relpath, path)
                    file_url = f"{url}/blob/{meta['commit']}/{relpath}"
                    document_id = recorder.add(row, "code", file_url, path)
                    recorder.log(document_id, file_url, "git", path)
                    ok += 1
                    if budget[0] is not None:
                        budget[0] -= 1
            return ok, 0
        except subprocess.CalledProcessError as exc:
            recorder.log("", url, "git", error=f"git hatası: {exc.stderr.strip()[:300]}")
            return 0, 1


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("01_download", cfg)
    seed = set_seed(cfg)

    if "{CONTACT_EMAIL}" in cfg["download"]["user_agent"]:
        raise SystemExit(".env içinde CONTACT_EMAIL boş. İndirme yapılan siteler sorun olursa size "
                         "ulaşabilsin diye isteklerde bu adres gönderilir; doldurup yeniden çalıştırın.")

    sources = {r["source_name"]: r for r in read_rows(resolve_path(cfg, "sources_csv"))}
    manifest = read_rows(resolve_path(cfg, "download_manifest"))
    if errors := validate(manifest, sources):
        raise SystemExit("Manifest hataları:\n  " + "\n  ".join(errors))

    raw_dir = resolve_path(cfg, "raw_dir")
    downloader, recorder = Downloader(cfg), Recorder(cfg, sources)
    budget: list[int | None] = [args.limit]
    ok = failed = blocked = 0

    for source_name in sorted({r["source_name"] for r in manifest}):
        rows = [r for r in manifest if r["source_name"] == source_name]
        for doc in plan_url_documents([r for r in rows if r["type"] in URL_TYPES], raw_dir):
            if recorder.has(doc["path"], doc["pages"]):
                continue
            if budget[0] is not None and budget[0] <= 0:
                break
            result = download_url_document(doc, downloader, recorder)
            ok, failed, blocked = ok + (result == "ok"), failed + (result == "failed"), blocked + (result == "blocked")
            logger.info("%s | %s %s", result, doc["row"]["url_or_title"], doc["pages"])
            if budget[0] is not None:
                budget[0] -= 1
        for url in sorted({r["url_or_title"] for r in rows if r["type"] == "git"}):
            if budget[0] is not None and budget[0] <= 0:
                break  # --limit doldu: depoyu boşuna klonlama
            git_ok, git_failed = download_git_source(
                url, [r for r in rows if r["type"] == "git" and r["url_or_title"] == url],
                raw_dir, seed, recorder, budget)
            ok, failed = ok + git_ok, failed + git_failed
            logger.info("git | %s | %d dosya kaydedildi%s", url, git_ok, " | HATA" if git_failed else "")

    if not recorder.renumber():
        logger.info("Numaralar yeniden verilmedi: sonraki fazlar mevcut document_id'leri kullanıyor")
    logger.info("Registry: %d doküman | log: %s", len(recorder.registry), rel(recorder.log_path))
    log_summary(logger, ok + failed + blocked, ok, failed, blocked)


if __name__ == "__main__":
    main()
