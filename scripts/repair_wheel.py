#!/usr/bin/env python3
"""Vendor the non-glibc closure into a cccr_py wheel and retag it manylinux.

auditwheel refuses to vendor a GCC 14 libstdc++, so release wheels are
repaired here. The platform tag is manylinux_2_35_x86_64 (glibc 2.35).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bundle_runtime_deps  # noqa: E402

PLATFORM = "manylinux_2_35_x86_64"
_TAG_LINE = re.compile(r"^(Tag:\s*)(\S+)\s*$", re.MULTILINE)


def fail(message: str) -> None:
    raise SystemExit(f"repair_wheel: {message}")


def retag_value(tag: str) -> str:
    parts = tag.split("-")
    if len(parts) < 3:
        fail(f"wheel tag {tag!r} is too short")
    parts[-1] = PLATFORM
    return "-".join(parts)


def retag_filename(name: str) -> str:
    if not name.endswith(".whl"):
        fail(f"{name} is not a wheel")
    parts = name[: -len(".whl")].split("-")
    if len(parts) < 5:
        fail(f"unexpected wheel name {name}")
    parts[-1] = PLATFORM
    return "-".join(parts) + ".whl"


def update_wheel_metadata(root: Path) -> None:
    matches = list(root.glob("*.dist-info/WHEEL"))
    if len(matches) != 1:
        fail(f"expected one *.dist-info/WHEEL, found {matches}")
    path = matches[0]
    text = path.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        return match.group(1) + retag_value(match.group(2))

    updated, count = _TAG_LINE.subn(replace, text)
    if count < 1:
        fail(f"no Tag: lines in {path}")
    path.write_text(updated, encoding="utf-8")


def file_hash(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    digest = hashlib.sha256(data).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return encoded, len(data)


def write_record(root: Path) -> None:
    distinfo = next(root.glob("*.dist-info"))
    record = distinfo / "RECORD"
    rows: list[str] = []
    record_rel = record.relative_to(root).as_posix()
    for path in sorted(root.rglob("*")):
        if not path.is_file() and not path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == record_rel:
            continue
        encoded, size = file_hash(path)
        rows.append(f"{rel},sha256={encoded},{size}")
    rows.append(f"{record_rel},,")
    record.write_text("\n".join(rows) + "\n", encoding="utf-8")


def pack_wheel(root: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file() or path.is_symlink():
                archive.write(path, path.relative_to(root).as_posix())


def repair_wheel(
    wheel: Path,
    output_dir: Path,
    cxx: str | None,
    glibc_max: tuple[int, int, int],
) -> Path:
    if not wheel.is_file():
        fail(f"missing {wheel}")
    with tempfile.TemporaryDirectory(prefix="cccr-wheel-") as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(root)
        extensions = sorted(root.glob("cccr_py*.so"))
        if len(extensions) != 1:
            fail(f"expected one cccr_py*.so in {wheel.name}, found {extensions}")
        bundle_runtime_deps.bundle_runtime_deps(
            [extensions[0]],
            extensions[0].parent,
            cxx=cxx,
            glibc_max=glibc_max,
        )
        update_wheel_metadata(root)
        write_record(root)
        dest = output_dir / retag_filename(wheel.name)
        pack_wheel(root, dest)
        return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--cxx", default="g++-14")
    parser.add_argument("--glibc-max", default="2.35")
    args = parser.parse_args(argv)
    dest = repair_wheel(
        args.wheel,
        args.output_dir,
        args.cxx or None,
        bundle_runtime_deps.parse_glibc_max(args.glibc_max),
    )
    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
