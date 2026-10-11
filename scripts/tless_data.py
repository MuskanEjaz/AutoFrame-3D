"""Download, inspect, and safely extract the bounded T-LESS benchmark subset."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
import zlib
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from huggingface_hub import HfApi, hf_hub_download
from tqdm.auto import tqdm

REPOSITORY = "bop-benchmark/tless"
REVISION = "5fd309a04476a842d93abfb584fba9ee7caecdf1"
LICENSE = "CC-BY-4.0"
FILES = {
    "tless_base.zip": 49_597,
    "tless_models.zip": 33_468_762,
    "tless_test_primesense_bop19.zip": 825_276_992,
}
DATA_ROOT = ROOT / "data" / "tless"
RAW_ROOT = DATA_ROOT / "downloads"
EXTRACT_ROOT = DATA_ROOT / "bop"
PROVENANCE_PATH = DATA_ROOT / "provenance.json"
ARCHIVE_CONTENTS_PATH = DATA_ROOT / "archive_contents.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_archive(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        for entry in tqdm(entries, desc=f"CRC {path.name}", unit="member"):
            if entry.is_dir():
                continue
            actual_crc = 0
            with archive.open(entry) as member:
                for chunk in iter(lambda: member.read(1024 * 1024), b""):
                    actual_crc = zlib.crc32(chunk, actual_crc)
            if actual_crc & 0xFFFFFFFF != entry.CRC:
                raise ValueError(f"ZIP CRC validation failed for {path.name}: {entry.filename}")
        return {
            "file": path.name,
            "archive_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "entry_count": len(entries),
            "uncompressed_bytes": sum(entry.file_size for entry in entries),
            "entries": [
                {
                    "name": entry.filename,
                    "bytes": entry.file_size,
                    "compressed_bytes": entry.compress_size,
                    "is_directory": entry.is_dir(),
                }
                for entry in entries
            ],
        }


def download_and_inspect() -> dict[str, object]:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    info = HfApi().dataset_info(REPOSITORY, revision=REVISION, files_metadata=True)
    if info.sha != REVISION:
        raise RuntimeError(f"Pinned dataset revision mismatch: {info.sha}")
    siblings = {item.rfilename: item for item in info.siblings}
    downloaded: list[Path] = []
    for name, expected_size in FILES.items():
        sibling = siblings.get(name)
        if sibling is None:
            raise FileNotFoundError(f"{name} not found at pinned revision {REVISION}")
        if sibling.size is not None and sibling.size != expected_size:
            raise ValueError(f"Remote size mismatch for {name}: {sibling.size} != {expected_size}")
        file_path = Path(
            hf_hub_download(
                repo_id=REPOSITORY,
                filename=name,
                repo_type="dataset",
                revision=REVISION,
                local_dir=RAW_ROOT,
                force_download=False,
                token=False,
            )
        )
        if file_path.stat().st_size != expected_size:
            raise ValueError(f"Downloaded size mismatch for {name}: {file_path.stat().st_size}")
        downloaded.append(file_path)

    archive_inspections = [inspect_archive(path) for path in downloaded]
    ARCHIVE_CONTENTS_PATH.write_text(
        json.dumps({
            "repository": REPOSITORY,
            "revision": REVISION,
            "archives": [
                {"file": item["file"], "entries": item["entries"]}
                for item in archive_inspections
            ],
        }, indent=2),
        encoding="utf-8",
    )
    archive_reports = [
        {key: value for key, value in item.items() if key != "entries"}
        for item in archive_inspections
    ]
    report: dict[str, object] = {
        "repository": REPOSITORY,
        "revision": REVISION,
        "license": LICENSE,
        "source_url": f"https://huggingface.co/datasets/{REPOSITORY}/tree/{REVISION}",
        "download_method": "huggingface_hub.hf_hub_download with explicit filenames and pinned revision",
        "download_resume": "Hub local_dir download metadata is retained; rerunning skips validated existing files.",
        "archive_contents": str(ARCHIVE_CONTENTS_PATH.relative_to(ROOT)),
        "archives": archive_reports,
    }
    PROVENANCE_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def inspect_local(validate_crc: bool = True) -> dict[str, object]:
    if not PROVENANCE_PATH.exists():
        raise FileNotFoundError("Run `python scripts/tless_data.py download` first")
    report = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    for archive_record in report["archives"]:
        path = RAW_ROOT / archive_record["file"]
        if not path.is_file() or path.stat().st_size != archive_record["archive_bytes"]:
            raise ValueError(f"Archive missing or size changed: {path}")
        if sha256_file(path) != archive_record["sha256"]:
            raise ValueError(f"Archive SHA-256 changed: {path}")
        if validate_crc:
            inspect_archive(path)
    return report


def safe_extract() -> dict[str, object]:
    report = inspect_local(validate_crc=False)
    required_bytes = sum(record["uncompressed_bytes"] for record in report["archives"])
    free_bytes = shutil.disk_usage(DATA_ROOT.drive or ROOT.drive).free
    reserve_bytes = 2 * 1024**3
    if free_bytes - required_bytes < reserve_bytes:
        raise OSError(
            f"Insufficient extraction headroom: need {required_bytes:,} bytes plus "
            f"{reserve_bytes:,} bytes reserve, have {free_bytes:,} bytes free"
        )
    EXTRACT_ROOT.mkdir(parents=True, exist_ok=True)
    for archive_record in report["archives"]:
        archive_path = RAW_ROOT / archive_record["file"]
        with zipfile.ZipFile(archive_path) as archive:
            for item in archive.infolist():
                relative = PurePosixPath(item.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"Unsafe archive member path: {item.filename}")
                destination = (EXTRACT_ROOT / Path(*relative.parts)).resolve()
                if EXTRACT_ROOT.resolve() not in destination.parents and destination != EXTRACT_ROOT.resolve():
                    raise ValueError(f"Unsafe archive member path: {item.filename}")
            archive.extractall(EXTRACT_ROOT)
    report["extracted_to"] = str(EXTRACT_ROOT.relative_to(ROOT))
    report["extracted_bytes_uncompressed"] = required_bytes
    PROVENANCE_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"download", "inspect", "extract"}:
        raise SystemExit("Usage: python scripts/tless_data.py download|inspect|extract")
    action = sys.argv[1]
    report = download_and_inspect() if action == "download" else (
        inspect_local() if action == "inspect" else safe_extract()
    )
    print(json.dumps({
        key: value for key, value in report.items() if key != "archives"
    }, indent=2))
    for record in report.get("archives", []):
        print(json.dumps({key: value for key, value in record.items() if key != "entries"}, indent=2))
        for entry in record.get("entries", [])[:20]:
            print(json.dumps(entry))


if __name__ == "__main__":
    main()