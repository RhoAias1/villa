"""Fetch the frozen public corpus and import it with the unmodified baseline."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse
from urllib.request import urlopen


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    importer = root / "audit/scratch/base-build/bin/vc_object_ingest"
    provenance_path = root / "evidence/export-databases/provenance.json"
    provenance = json.loads(provenance_path.read_text()) if provenance_path.exists() else {
        "source_method": "Frozen originals; copies change only version 4 to version 3; unmodified baseline importer.",
        "method_credit": "ChaseHendrick, ScrollPrize/villa issue 2320 and PR 2321",
        "base_commit": "39a8cf3a124bdd5540ee826e1cb30047c8dc8c85", "datasets": {},
    }
    for scroll in ("0332", "0139"):
        manifest = json.loads((root / f"data/{scroll}_manifest.json").read_text())
        original_dir = root / f"data/{scroll}_fibers"
        converted_dir = root / f"audit/scratch/relabel-v3-{scroll}"
        if not args.verify_only:
            original_dir.mkdir(parents=True, exist_ok=True)
            converted_dir.mkdir(parents=True, exist_ok=True)

        def fetch_and_check(entry):
            name = entry["filename"]
            assert Path(name).name == name and name.endswith(".json")
            source = original_dir / name
            if not source.exists():
                if args.verify_only:
                    raise RuntimeError(f"Missing original: {source}")
                url = urlparse(entry["url"])
                assert url.scheme == "https" and url.hostname == "dl.ash2txt.org"
                data = urlopen(entry["url"], timeout=90).read()
                assert len(data) == entry["bytes"]
                assert hashlib.sha256(data).hexdigest() == entry["sha256"]
                source.write_bytes(data)
            assert source.stat().st_size == entry["bytes"] and sha(source) == entry["sha256"], source
            obj = json.loads(source.read_bytes())
            if obj["version"] == 4:
                obj["version"] = 3
            converted = converted_dir / name
            if args.verify_only or converted.exists():
                assert json.loads(converted.read_bytes()) == obj, converted
            else:
                converted.write_text(json.dumps(obj) + "\n")

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(fetch_and_check, manifest["files"]))
        db = root / f"evidence/export-databases/{scroll}.vcobj"
        if db.exists():
            assert sha(db) == provenance["datasets"][scroll]["sha256"], db
        else:
            if args.verify_only:
                raise RuntimeError(f"Missing store: {db}")
            db.parent.mkdir(parents=True, exist_ok=True)
            command = [str(importer), "--db", str(db), "--author", "export-study",
                       "--fiber", str(converted_dir), "--no-progress"]
            subprocess.run(command, check=True)
            provenance["datasets"][scroll] = {
                "command": command, "exit": 0, "sha256": sha(db),
                "fibers": len(manifest["files"]),
            }
            provenance["import_binary_sha256"] = sha(importer)
            provenance_path.write_text(json.dumps(provenance, indent=2) + "\n")
        print(f"{scroll}: {len(manifest['files'])} source hashes and migration copies verified; store hash verified")


if __name__ == "__main__":
    main()
