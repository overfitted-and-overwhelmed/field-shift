"""Copy the files configured in config.DATASETS from z_processed into data/processed/<dataset>/.

z_processed is only ever READ. Each file is copied individually; source checksums are verified
before and after, and every copy is verified against its source.

Usage (from anywhere):
    uv run python data/cleaning-scripts/build_datasets.py                    # all datasets
    uv run python data/cleaning-scripts/build_datasets.py climate_data       # one dataset
    uv run python data/cleaning-scripts/build_datasets.py --dry-run          # show only
    uv run python data/cleaning-scripts/build_datasets.py --prune            # also delete files in the
                                                                             # OUTPUT folder that are no longer configured (README.md is kept)
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

import config


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:  # read-only
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def is_inside(path: Path, parent: Path) -> bool:
    return path.resolve() == parent.resolve() or parent.resolve() in path.resolve().parents


def build(name: str, files: list[str], dry_run: bool, prune: bool) -> None:
    src_dir, out_dir = config.SOURCE_DIR, config.OUTPUT_ROOT / name
    if is_inside(out_dir, src_dir):
        sys.exit(f"ABORT: output folder {out_dir} lies inside the read-only source {src_dir}")
    sources = [src_dir / f for f in files]
    missing = [str(s) for s in sources if not s.is_file()]
    if missing:
        sys.exit(f"ABORT: configured files not found in z_processed: {missing}")
    for s in sources:
        if not is_inside(s, src_dir):
            sys.exit(f"ABORT: {s} is not inside z_processed")

    before = {s: sha256(s) for s in sources}
    print(f"[{name}] {len(files)} files -> {out_dir}{'  (dry run)' if dry_run else ''}")
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
    for s in sources:
        dst = out_dir / s.name
        print(f"  copy {s.name}  ({s.stat().st_size / 1e6:.2f} MB)")
        if dry_run:
            continue
        shutil.copyfile(s, dst)  # copies content only, source is opened read-only
        if sha256(dst) != before[s]:
            sys.exit(f"ABORT: copy of {s.name} does not match its source")

    keep = set(files) | {"README.md"}  # README.md in the output folder is hand-written and never touched
    stale = sorted(p for p in out_dir.glob("*") if p.is_file() and p.name not in keep) if out_dir.exists() else []
    for p in stale:
        if prune and not dry_run:
            p.unlink()  # only ever inside the output folder (checked above)
            print(f"  pruned {p.name}")
        else:
            print(f"  note: {p.name} is in the output folder but not configured (use --prune to remove)")

    after = {s: sha256(s) for s in sources}
    if before != after:
        sys.exit("ALARM: a file in z_processed changed during the run!")
    print(f"  ok: z_processed unchanged, {len(files)} files verified")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("datasets", nargs="*", help="dataset names from config.DATASETS (default: all)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--prune", action="store_true")
    a = p.parse_args()
    unknown = [d for d in a.datasets if d not in config.DATASETS]
    if unknown:
        sys.exit(f"unknown dataset(s) {unknown}; available: {list(config.DATASETS)}")
    for name in a.datasets or config.DATASETS:
        build(name, config.DATASETS[name], a.dry_run, a.prune)


if __name__ == "__main__":
    main()
