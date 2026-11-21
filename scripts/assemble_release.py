#!/usr/bin/env python3
"""Install the dist build and pack CLI, C, and C++ release tarballs."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bundle_runtime_deps  # noqa: E402

SOURCE_ROOT = Path(__file__).resolve().parents[1]
ARCH = "linux-x86_64"


def fail(message: str) -> None:
    raise SystemExit(f"assemble_release: {message}")


def project_version(source: Path) -> str:
    text = (source / "CMakeLists.txt").read_text(encoding="utf-8")
    match = re.search(
        r"project\s*\(\s*cccr-engine\b.*?VERSION\s+([0-9]+\.[0-9]+\.[0-9]+)",
        text,
        re.DOTALL,
    )
    if match is None:
        fail("project VERSION not found in CMakeLists.txt")
    return match.group(1)


def pyproject_version(source: Path) -> str:
    text = (source / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if match is None:
        fail("version not found in pyproject.toml")
    return match.group(1)


def cmake_cache(build_dir: Path, name: str) -> str:
    cache = build_dir / "CMakeCache.txt"
    if not cache.is_file():
        fail(f"missing {cache}")
    prefix = name + ":"
    for line in cache.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix) or line.startswith(name + "="):
            return line.split("=", 1)[1]
    fail(f"{name} not set in {cache}")
    return ""


def copy_symlink_tree(src: Path, dest: Path) -> None:
    if not src.is_dir():
        fail(f"missing {src}")
    dest.mkdir(parents=True, exist_ok=True)
    for path in src.iterdir():
        target = dest / path.name
        if path.is_symlink():
            if target.exists() or target.is_symlink():
                target.unlink()
            target.symlink_to(os.readlink(path))
        elif path.is_dir():
            shutil.copytree(path, target, symlinks=True, dirs_exist_ok=True)
        else:
            shutil.copy2(path, target)


def write_licenses(dest: Path, source: Path, saxon_root: Path) -> None:
    licenses = dest / "LICENSES"
    licenses.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "LICENSE", licenses / "CCCR-MIT.txt")
    saxon_license = saxon_root / "notices" / "LICENSE.txt"
    if not saxon_license.is_file():
        fail(f"missing SaxonC-HE license at {saxon_license}")
    shutil.copy2(saxon_license, licenses / "SaxonC-HE-MPL-2.0.txt")
    for name in ("redland", "raptor2", "rasqal"):
        apache = source / "third-party" / name / "LICENSE-2.0.txt"
        if not apache.is_file():
            fail(f"missing {apache}")
        shutil.copy2(apache, licenses / f"{name}-Apache-2.0.txt")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def make_tarball(tree: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    with tarfile.open(dest, "w:gz") as archive:
        archive.add(tree, arcname=tree.name)


def require_x86_64() -> None:
    machine = os.uname().machine
    if machine not in {"x86_64", "amd64"}:
        fail(f"release archives are {ARCH} only (this host is {machine})")


def assemble(
    build_dir: Path,
    output_dir: Path,
    cxx: str,
    source: Path,
    glibc_max: tuple[int, int, int],
) -> list[Path]:
    require_x86_64()
    version = project_version(source)
    py_version = pyproject_version(source)
    if py_version != version:
        fail(f"pyproject.toml version {py_version} != CMake version {version}")

    saxon_root = Path(cmake_cache(build_dir, "CCCR_SAXON_CHE_ROOT"))
    if not saxon_root.is_dir():
        fail(f"CCCR_SAXON_CHE_ROOT is not a directory: {saxon_root}")

    output_dir.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="cccr-stage-"))
    try:
        subprocess.run(
            ["cmake", "--install", str(build_dir), "--prefix", str(stage)],
            check=True,
        )
        return pack_stage(
            stage, output_dir, version, cxx, source, saxon_root, glibc_max
        )
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def pack_stage(
    stage: Path,
    output_dir: Path,
    version: str,
    cxx: str,
    source: Path,
    saxon_root: Path,
    glibc_max: tuple[int, int, int],
) -> list[Path]:
    cli_src = stage / "bin" / "cccr_cli"
    c_src = stage / "lib" / "libcccr_bindings_c.so"
    core_a = stage / "lib" / "libcccr_core.a"
    core_so = stage / "lib" / "libcccr_core.so"
    for path in (cli_src, c_src):
        if not path.exists():
            fail(f"install prefix is missing {path}")
    if not core_a.exists() and not core_so.exists():
        fail("install prefix is missing libcccr_core.a and libcccr_core.so")

    archives: list[Path] = []
    archives.append(
        pack_cli(stage, output_dir, version, cxx, source, saxon_root, glibc_max)
    )
    archives.append(
        pack_c(stage, output_dir, version, cxx, source, saxon_root, glibc_max)
    )
    archives.append(pack_cpp(stage, output_dir, version, source, saxon_root))
    return archives


def pack_cli(
    stage: Path,
    output_dir: Path,
    version: str,
    cxx: str,
    source: Path,
    saxon_root: Path,
    glibc_max: tuple[int, int, int],
) -> Path:
    name = f"cccr-cli-{version}-{ARCH}"
    tree = output_dir / name
    if tree.exists():
        shutil.rmtree(tree)
    lib = tree / "lib"
    lib.mkdir(parents=True)
    (tree / "bin").mkdir()
    shutil.copy2(stage / "bin" / "cccr_cli", tree / "bin" / "cccr_cli")
    copy_symlink_tree(stage / "lib", lib)
    # The CLI links the static core. Drop SDK archives and the C/C++ libraries.
    for path in list(lib.iterdir()):
        if path.name.startswith(("libsaxonc", "libcccr_core.so")):
            continue
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    bundle_runtime_deps.bundle_runtime_deps(
        [tree / "bin" / "cccr_cli"],
        lib,
        cxx=cxx,
        glibc_max=glibc_max,
    )
    write_licenses(tree, source, saxon_root)
    write_text(
        tree / "README.txt",
        f"""
CCCR CLI {version} ({ARCH})

Requires glibc 2.35 or newer (Ubuntu 22.04 and newer). SaxonC-HE and the
GCC 14 C++ runtime are in lib/. Load this executable only in a process that
is not already using a different libstdc++.

  bin/cccr_cli --help
  bin/cccr_cli run -s schema.json -i input.xml -o out.rdf

Redland is linked into the executable under the Apache-2.0 alternative.
SaxonC-HE is MPL-2.0. See LICENSES/.
""",
    )
    dest = output_dir / f"{name}.tar.gz"
    make_tarball(tree, dest)
    return dest


def pack_c(
    stage: Path,
    output_dir: Path,
    version: str,
    cxx: str,
    source: Path,
    saxon_root: Path,
    glibc_max: tuple[int, int, int],
) -> Path:
    name = f"cccr-c-{version}-{ARCH}"
    tree = output_dir / name
    if tree.exists():
        shutil.rmtree(tree)
    include = tree / "include" / "cccr" / "bindings" / "c"
    include.parent.mkdir(parents=True)
    shutil.copytree(stage / "include" / "cccr" / "bindings" / "c", include)
    lib = tree / "lib"
    lib.mkdir()
    copy_symlink_tree(stage / "lib", lib)
    for path in list(lib.iterdir()):
        keep = path.name.startswith(
            ("libsaxonc", "libcccr_bindings_c.so", "libcccr_core.so")
        )
        if keep:
            continue
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    binding = lib / "libcccr_bindings_c.so"
    bundle_runtime_deps.bundle_runtime_deps(
        [binding], lib, cxx=cxx, glibc_max=glibc_max
    )
    write_licenses(tree, source, saxon_root)
    write_text(
        tree / "README.txt",
        f"""
CCCR C library {version} ({ARCH})

Headers: include/cccr/bindings/c/cccr.h
Libraries: lib/libcccr_bindings_c.so and lib/libcccr_core.so

  cc -std=c11 app.c \\
    -I include \\
    -L lib -Wl,-rpath,'$ORIGIN/../lib' -Wl,--disable-new-dtags \\
    -lcccr_bindings_c

Put the executable in a bin/ directory next to lib/ so the RPATH resolves.
Requires glibc 2.35 or newer. This library bundles GCC 14's libstdc++ for C
callers; do not load it into a process that already uses a different
libstdc++.

Redland is linked into the shared library under the Apache-2.0 alternative.
SaxonC-HE is MPL-2.0. See LICENSES/.
""",
    )
    dest = output_dir / f"{name}.tar.gz"
    make_tarball(tree, dest)
    return dest


def pack_cpp(
    stage: Path,
    output_dir: Path,
    version: str,
    source: Path,
    saxon_root: Path,
) -> Path:
    name = f"cccr-cpp-{version}-{ARCH}"
    tree = output_dir / name
    if tree.exists():
        shutil.rmtree(tree)
    shutil.copytree(stage, tree, symlinks=True)
    bin_dir = tree / "bin"
    if bin_dir.exists():
        shutil.rmtree(bin_dir)
    for path in (tree / "lib").glob("libcccr_bindings_c.so*"):
        path.unlink()
    bindings = tree / "include" / "cccr" / "bindings"
    if bindings.exists():
        shutil.rmtree(bindings)
    write_licenses(tree, source, saxon_root)
    write_text(
        tree / "README.txt",
        f"""
CCCR C++ SDK {version} ({ARCH})

Built with GCC 14. cccr::cccr is one library: libcccr_core.so when
CCCR_BUILD_SHARED is on (SOVERSION 0, this compiler's libstdc++), or
libcccr_core.a when it is off. A shared build does not bundle a private
libstdc++; link it with the same GCC 14 so there is one libstdc++ in the process.

  cmake -S your_app -B build -DCMAKE_PREFIX_PATH=/path/to/{name} \\
    -DCMAKE_CXX_COMPILER=g++-14
  target_link_libraries(your_app PRIVATE cccr::cccr)

Install libxml2, zlib, and any other system libraries listed when the static
archive is linked (ICU and curl when Redland was built against them).
SaxonC-HE ships in lib/. Requires glibc 2.35 or newer.

Redland static archives are Apache-2.0. SaxonC-HE is MPL-2.0. See LICENSES/.
""",
    )
    dest = output_dir / f"{name}.tar.gz"
    make_tarball(tree, dest)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cxx", default="g++-14")
    parser.add_argument("--source-dir", type=Path, default=SOURCE_ROOT)
    parser.add_argument(
        "--glibc-max",
        default="2.35",
        help="GLIBC_ ceiling for shipped binaries (default 2.35, the Ubuntu 22.04 baseline)",
    )
    args = parser.parse_args(argv)
    archives = assemble(
        args.build_dir.resolve(),
        args.output_dir.resolve(),
        args.cxx,
        args.source_dir.resolve(),
        bundle_runtime_deps.parse_glibc_max(args.glibc_max),
    )
    for archive in archives:
        print(archive)
    return 0


if __name__ == "__main__":
    sys.exit(main())
