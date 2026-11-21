#!/usr/bin/env python3
"""Copy a binary's non-glibc shared-library closure next to it.

The root binary must already have a DT_RPATH/DT_RUNPATH containing ``$ORIGIN``.
Copied libraries are given ``DT_RPATH=$ORIGIN`` (old-style RPATH, not RUNPATH)
so SaxonC-HE's dependency on ``libsaxonc-core-he`` resolves beside the binary.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

GLIBC_MAX = (2, 35, 0)
GLIBC_SONAME_PREFIXES = (
    "libc.so",
    "libm.so",
    "libdl.so",
    "libpthread.so",
    "librt.so",
    "libutil.so",
    "libresolv.so",
    "libnsl.so",
    "libanl.so",
    "ld-linux",
)
COMPILER_SONAMES = ("libstdc++.so.6", "libgcc_s.so.1")
_RPATH_RE = re.compile(
    r"\((?:RPATH|RUNPATH)\)\s+Library (?:rpath|runpath): \[([^\]]*)\]"
)
_GLIBC_RE = re.compile(r"GLIBC_(\d+)\.(\d+)(?:\.(\d+))?")


def fail(message: str) -> None:
    raise SystemExit(f"bundle_runtime_deps: {message}")


def is_glibc_runtime(soname: str) -> bool:
    base = soname.rsplit("/", 1)[-1]
    return base.startswith(GLIBC_SONAME_PREFIXES)


def is_elf(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"\x7fELF"
    except OSError:
        return False


def run_text(command: list[str], *, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
        env=env,
    )
    if proc.returncode != 0:
        fail(
            f"{' '.join(command)} failed ({proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def rpath_text(path: Path) -> str:
    return " ".join(_RPATH_RE.findall(run_text(["readelf", "-d", str(path)])))


def require_origin_rpath(path: Path) -> None:
    text = rpath_text(path)
    if "$ORIGIN" not in text and "${ORIGIN}" not in text:
        fail(f"{path} RPATH does not contain $ORIGIN (got {text!r})")


def required_glibc(path: Path) -> tuple[int, int, int]:
    proc = subprocess.run(
        ["objdump", "-T", str(path)],
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )
    best = (0, 0, 0)
    for line in proc.stdout.splitlines():
        if "*UND*" not in line:
            continue
        match = _GLIBC_RE.search(line)
        if match is None:
            continue
        version = (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3) or 0),
        )
        if version > best:
            best = version
    return best


def require_glibc(path: Path, ceiling: tuple[int, int, int]) -> None:
    found = required_glibc(path)
    if found > ceiling:
        found_s = ".".join(str(part) for part in found)
        ceiling_s = ".".join(str(part) for part in ceiling)
        fail(f"{path} requires GLIBC_{found_s}, ceiling is GLIBC_{ceiling_s}")


def compiler_runtime_map(cxx: str) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for soname in COMPILER_SONAMES:
        printed = run_text([cxx, f"-print-file-name={soname}"]).strip()
        if not printed or printed == soname:
            continue
        path = Path(printed)
        if path.is_file() and is_elf(path):
            found[soname] = path.resolve()
    return found


def ldd_needed(path: Path) -> dict[str, Path | None]:
    env = os.environ.copy()
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("LD_PRELOAD", None)
    stdout = run_text(["ldd", str(path)], env=env)
    needed: dict[str, Path | None] = {}
    for line in stdout.splitlines():
        if "=>" not in line:
            continue
        left, right = line.split("=>", 1)
        soname = left.strip()
        resolved = right.strip().split()[0] if right.strip() else ""
        if not soname or soname.startswith("linux-vdso"):
            continue
        if resolved == "not":
            needed[soname] = None
            continue
        candidate = Path(resolved)
        needed[soname] = candidate if candidate.is_file() else None
    return needed


def place_dependency(source: Path, soname: str, dest: Path) -> Path:
    """Copy ``source`` into ``dest`` under ``soname``.

    Never returns a path outside ``dest``. An existing file or symlink that
    already resolves inside ``dest`` is reused so Saxon SONAME links installed
    by CMake are patched in place instead of overwritten.
    """
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    source = source.resolve()
    target = dest / soname

    def inside_dest(path: Path) -> bool:
        resolved = path.resolve()
        return resolved == dest or dest in resolved.parents

    if target.exists() or target.is_symlink():
        current = target.resolve()
        if inside_dest(current) and is_elf(current):
            return current
        target.unlink()
    if source.parent == dest and source.name == soname:
        return source
    shutil.copy2(source, target, follow_symlinks=True)
    placed = target.resolve()
    if not inside_dest(placed):
        fail(f"refusing to use {placed} outside {dest}")
    return placed


def patchelf_origin(path: Path) -> None:
    proc = subprocess.run(
        ["patchelf", "--set-rpath", r"$ORIGIN", "--force-rpath", str(path)],
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )
    if proc.returncode != 0:
        fail(
            f"patchelf {path} failed ({proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )


def parse_glibc_max(text: str) -> tuple[int, int, int]:
    parts = text.split(".")
    if len(parts) < 2 or len(parts) > 3 or not all(part.isdigit() for part in parts):
        fail(f"invalid glibc ceiling {text!r}")
    while len(parts) < 3:
        parts.append("0")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def bundle_runtime_deps(
    roots: list[Path],
    dest: Path,
    *,
    cxx: str | None = None,
    glibc_max: tuple[int, int, int] = GLIBC_MAX,
) -> None:
    if not roots:
        fail("no root binaries")
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    resolved_roots = [path.resolve() for path in roots]
    for root in resolved_roots:
        if not root.is_file():
            fail(f"missing binary {root}")
        require_origin_rpath(root)
        require_glibc(root, glibc_max)

    preferred = compiler_runtime_map(cxx) if cxx else {}
    scanned: set[Path] = set()
    patched: set[Path] = set()
    queue = list(resolved_roots)
    root_set = set(resolved_roots)
    while queue:
        current = queue.pop()
        if current in scanned:
            continue
        scanned.add(current)
        for soname, resolved in ldd_needed(current).items():
            if is_glibc_runtime(soname):
                continue
            source = preferred.get(soname) or resolved
            if source is None:
                fail(f"{current} needs {soname}, which was not found")
            placed = place_dependency(source, soname, dest)
            if placed not in root_set and placed not in patched:
                patchelf_origin(placed)
                require_origin_rpath(placed)
                require_glibc(placed, glibc_max)
                patched.add(placed)
            if placed not in scanned:
                queue.append(placed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, required=True, help="Directory for copied libraries")
    parser.add_argument("--cxx", default="", help="C++ compiler used to locate libstdc++/libgcc_s")
    parser.add_argument(
        "--glibc-max",
        default="2.35",
        help="Fail when a shipped binary needs a newer GLIBC_ symbol (default 2.35)",
    )
    parser.add_argument("binaries", nargs="+", type=Path)
    args = parser.parse_args(argv)
    bundle_runtime_deps(
        args.binaries,
        args.dest,
        cxx=args.cxx or None,
        glibc_max=parse_glibc_max(args.glibc_max),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
