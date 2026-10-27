"""Compare every single-fiber export with unmodified upstream's full-network codec."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time
import uuid

NAMESPACE = uuid.UUID("e14f6968-9145-494d-8b06-ab2f2fac7f3b")


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def require(condition, explanation):
    if not condition:
        raise RuntimeError(explanation)


def run(command, log):
    start = time.perf_counter()
    result = subprocess.run([str(c) for c in command], text=True, capture_output=True)
    log.write_text(result.stdout + result.stderr)
    require(result.returncode == 0, str(log))
    return {"command": [str(c) for c in command], "exit": result.returncode,
            "seconds": time.perf_counter() - start, "log": str(log)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    p = Path(__file__).resolve().parent
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    baseline = p / "audit/scratch/base-build/verify_fiber_exports"
    optimized = p / "build-export/verify_fiber_exports"
    provenance = json.loads((p / "evidence/export-databases/provenance.json").read_text())
    summary = {"reference_binary_sha256": digest(baseline), "optimized_binary_sha256": digest(optimized),
               "datasets": {}}
    for scroll in ["0332", "0139"]:
        target = output / scroll
        target.mkdir()
        db = p / "evidence/export-databases" / (scroll + ".vcobj")
        db_hash = digest(db)
        require(db_hash == provenance["datasets"][scroll]["sha256"], "input database changed")
        receipts = {}
        for label, binary, mode in [("reference", baseline, "network"),
                                    ("network", optimized, "network"),
                                    ("individual", optimized, "individual")]:
            receipts[label] = run([binary, mode, db, target / label], target / (label + ".log"))
        manifest = json.loads((p / "data" / (scroll + "_manifest.json")).read_text())
        expected_names = set()
        control_points = line_points = bound = total_bytes = 0
        files = []
        for entry in manifest["files"]:
            raw = p / "data" / (scroll + "_fibers") / entry["filename"]
            require(digest(raw) == entry["sha256"], "original source changed: " + str(raw))
            original = json.loads(raw.read_bytes())
            migrated = dict(original)
            if migrated["version"] == 4:
                migrated["version"] = 3
            migration_input = p / "audit/scratch" / ("relabel-v3-" + scroll) / entry["filename"]
            require(json.loads(migration_input.read_bytes()) == migrated, "migration changed more than version")
            ident = str(uuid.UUID(original["uuid"])) if "uuid" in original else str(uuid.uuid5(NAMESPACE, "vc3d_fiber/" + entry["filename"]))
            name = ident + ".json"
            expected_names.add(name)
            reference = target / "reference" / name
            expected_hash = digest(reference)
            for variant in ["network", "individual"]:
                require(digest(target / variant / name) == expected_hash, "export bytes differ: " + variant + "/" + name)
            exported = json.loads(reference.read_bytes())
            for field in ["control_points", "line_points"]:
                positions = lambda points: [x["position"] if isinstance(x, dict) else x for x in points]
                require(positions(exported.get(field, [])) == positions(original.get(field, [])), "geometry changed: " + name)
            if "vc_open_data_coordinate_space" in original:
                frame = original["vc_open_data_coordinate_space"]
                require(frame.endswith("@L0"), "unexpected source frame")
                require(exported["coordinates"] == {"volume_uuid": frame.split("/", 1)[1][:-3], "scale_factor": 1}, "coordinate binding changed")
                bound += 1
            control_points += len(original.get("control_points", []))
            line_points += len(original.get("line_points", []))
            total_bytes += reference.stat().st_size
            files.append({"uuid": ident, "source": entry["filename"], "export_sha256": expected_hash})
        for variant in ["reference", "network", "individual"]:
            require({f.name for f in (target / variant).iterdir()} == expected_names, "export file set differs")
        require(digest(db) == db_hash, "export modified the input database")
        (target / "files.json").write_text(json.dumps(files, indent=2) + "\n")
        summary["datasets"][scroll] = {"fibers": len(files), "all_export_bytes_identical": True,
            "control_points": control_points, "line_points": line_points, "known_coordinate_bindings_verified": bound,
            "total_export_bytes": total_bytes, "input_database_unchanged": True, "source_hashes_unchanged": True,
            "runs": receipts}
        print(scroll, len(files), "byte-identical exports", flush=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
