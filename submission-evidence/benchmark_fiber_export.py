"""Paired native CLI measurements on frozen real-scroll databases (macOS)."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import re
import statistics
import subprocess
import time
import uuid


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=5)
    args = parser.parse_args()
    if args.trials < 3:
        raise ValueError("at least three paired trials required")
    p = Path(__file__).resolve().parent
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    executables = {"baseline": p / "evidence/baseline-bin/vc_object_export",
                   "optimized": p / "build-export/bin/vc_object_export"}
    provenance = json.loads((p / "evidence/export-databases/provenance.json").read_text())
    cases = [("0332", "dj_20260810T113807458_000001.json", 184),
             ("0139", "dj_20260902T151037604_000001.json", 602),
             ("0139", "lt_20261007T084812276_000336.json", 1)]
    summary = {"platform": platform.platform(), "machine": platform.machine(),
               "binary_sha256": {k: digest(v) for k, v in executables.items()},
               "method": "One warmup per binary and case; then paired trials with alternating order. Elapsed time includes process launch. RSS from macOS /usr/bin/time -l. Local, non-concurrent runs; no universal speed claim.",
               "trials_per_binary_per_case": args.trials, "cases": []}
    for scroll, source, component in cases:
        original = json.loads((p / "data" / (scroll + "_fibers") / source).read_bytes())
        ident = original.get("uuid") or str(uuid.uuid5(uuid.UUID("e14f6968-9145-494d-8b06-ab2f2fac7f3b"), "vc3d_fiber/" + source))
        case = out / (scroll + "-" + str(component))
        case.mkdir()
        db = p / "evidence/export-databases" / (scroll + ".vcobj")
        expected_db = provenance["datasets"][scroll]["sha256"]
        if digest(db) != expected_db:
            raise RuntimeError("input database changed")
        expected_output = digest(p / "evidence/export-validation" / scroll / "reference" / (ident + ".json"))
        runs = []
        for trial in range(-1, args.trials):
            order = ["baseline", "optimized"] if trial % 2 == 0 else ["optimized", "baseline"]
            for variant in order:
                output = case / f"{variant}-{trial}.json"
                command = ["/usr/bin/time", "-l", str(executables[variant]), "--db", str(db),
                           "--uuid", ident, "--output", str(output)]
                start = time.perf_counter()
                result = subprocess.run(command, capture_output=True, text=True)
                elapsed = time.perf_counter() - start
                (case / f"{variant}-{trial}.log").write_text(result.stdout + result.stderr)
                if result.returncode or digest(output) != expected_output:
                    raise RuntimeError("failed export or unequal output: " + str(output))
                match = re.search(r"^\s*(\d+)\s+maximum resident set size", result.stderr, re.M)
                if not match:
                    raise RuntimeError("missing RSS measurement")
                runs.append({"variant": variant, "trial": trial, "warmup": trial == -1,
                             "command": command, "seconds": elapsed, "max_rss_bytes": int(match.group(1)),
                             "exit": result.returncode, "output_sha256": expected_output})
        stats = {}
        for variant in executables:
            selected = [r for r in runs if r["variant"] == variant and not r["warmup"]]
            stats[variant] = {"median_seconds": statistics.median(r["seconds"] for r in selected),
                              "min_seconds": min(r["seconds"] for r in selected),
                              "max_seconds": max(r["seconds"] for r in selected),
                              "median_max_rss_bytes": statistics.median(r["max_rss_bytes"] for r in selected)}
        stats["speedup"] = stats["baseline"]["median_seconds"] / stats["optimized"]["median_seconds"]
        if digest(db) != expected_db:
            raise RuntimeError("export changed the input database")
        record = {"scroll": scroll, "source_file": source, "uuid": ident,
                  "component_fibers": component, "root_line_points": len(original["line_points"]),
                  "statistics": stats, "runs": runs, "input_database_unchanged": True,
                  "all_outputs_byte_identical": True}
        summary["cases"].append(record)
        (case / "measurements.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"scroll": scroll, "component": component, **stats}), flush=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
