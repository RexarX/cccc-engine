# CCCR Engine

**CCCR** (Context-Compute-Construct-Recursive) is a declarative JSON DSL and C++ engine that maps weakly structured input (XML first; CSV via XML projection) into an RDF triple graph.
[CCCR article](http://a.roz37.ru/lipers/%D1%81%D0%B5%D0%BC%D0%B0%D0%BD%D1%82%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9.%D0%BA%D0%BE%D0%BD%D1%82%D1%80%D0%B0%D0%BA%D1%82/%D0%BC%D0%B8%D1%81%D0%B8%D1%81/cccr/%D1%81%D1%85%D0%B5%D0%BC%D0%B0).

Pipeline:

```text
[context-unbound data] + [CCCR JSON schema] → engine → RDF graph / RDF/XML
```

The engine walks the schema recursively, evaluates `compute` blocks (`xquery` | `sparql` | `include`), constructs subject/property IRIs, and emits triples. Optional seed knowledge graphs support in-pipeline SPARQL; a CLI exposes `run` and `query`.

---

## Platform

| OS | Status |
| --- | --- |
| **Linux** (native or **WSL2**) | Supported (primary) |
| macOS | SaxonC-HE can be fetched; Redland stack is Linux-oriented — treat as experimental |
| Windows | **Unsupported** for the Redland (raptor2 / rasqal / librdf) path — configure will fail |

Requirements: **CMake ≥ 3.25**, **C++23** compiler (GCC or Clang recommended), **Ninja** (used by Linux/macOS presets).

---

## Dependencies

### Always required (system)

Install these on the host before configuring:

| Package (Debian/Ubuntu) | Why |
| --- | --- |
| `build-essential` or `g++` / `clang` | C/C++ toolchain |
| `cmake` (≥ 3.25) | Build system |
| `ninja-build` | Generator used by presets |
| `pkg-config` | Locate system libraries |
| **`libxml2-dev`** | **Required** — raptor/XML stack (`pkg-config` name `libxml-2.0`). Needed for the vendored Redland build and typically present when using system Redland as well |
| `make` | Required when building the **vendored** Redland stack (`ExternalProject` + autotools) |

Recommended when falling back to vendored Redland:

| Package (Debian/Ubuntu) | Why |
| --- | --- |
| `libpcre3-dev`/`libpcre2-dev` | PCRE1 for rasqal (`pkg-config` `libpcre`); configure may fail without it |
| `libcurl4-openssl-dev` | Optional raptor features (picked up if present) |
| `libicu-dev` | Optional raptor/ICU support if present |

Example (minimum + recommended for vendored Redland):

```bash
sudo apt update
sudo apt install -y \
  build-essential cmake ninja-build pkg-config make \
  libxml2-dev libpcre3-dev \
  libcurl4-openssl-dev libicu-dev
```

Is may be possible that `libpcre3-dev` won't be found on some distros (for example Ubuntu 26.04). In that case, you can try to install `libpcre2-dev` instead.

### Optional: system Redland (preferred when available)

Core always needs the Redland stack (**raptor2**, **rasqal**, **librdf**). Resolution order:

1. **System packages** via pkg-config when `CCCR_REDLAND_USE_SYSTEM=ON` (default)
2. Else **vendored static** build from [`third-party/`](third-party/) (sources already in-tree; no download)

| Package (Debian/Ubuntu) | pkg-config |
| --- | --- |
| `libraptor2-dev` | `raptor2` |
| `librasqal3-dev` | `rasqal` |
| `librdf0-dev` | `redland` |

```bash
sudo apt install -y libraptor2-dev librasqal3-dev librdf0-dev
```

If any of these are missing, CMake prints a status message and **falls back to the vendored build**. To skip the system probe and force vendored:

```bash
cmake --preset linux-gcc-release -DCCCR_REDLAND_USE_SYSTEM=OFF
```

Details: [`third-party/README.md`](third-party/README.md), [`cmake/BuildRedland.cmake`](cmake/BuildRedland.cmake).

### Fetched at configure time

| Dependency | Role | How |
| --- | --- | --- |
| **SaxonC-HE 13** | XML / XQuery (mandatory) | [`FindOrFetchSaxonCHE.cmake`](cmake/FindOrFetchSaxonCHE.cmake): use an existing install, or download + extract into `${CCCR_CACHE_DIR}/saxonc-he` (default `cccr-engine/.cache/saxonc-he`). |

Overrides:

```bash
# Pre-extracted SaxonC-HE root (dirs SaxonCHE/ and SaxonCCoreHE/)
cmake --preset linux-gcc-release -DCCCR_SAXON_CHE_ROOT=/path/to/saxonc

# Persistent download/build cache (default: <project>/.cache)
cmake --preset linux-gcc-release -DCCCR_CACHE_DIR=/path/to/cache
```

First configure needs network access unless Saxon is already cached or pointed at with `CCCR_SAXON_CHE_ROOT` / `SAXONC_HOME` / `CMAKE_PREFIX_PATH`.

---

## Build

From the `cccr-engine/` directory (this folder):

```bash
cmake --preset linux-gcc-release
cmake --build --preset linux-gcc-release
ctest --preset linux-gcc-release --output-on-failure
```

Other useful presets: `linux-gcc-debug`, `linux-clang-relwithdebinfo` (see [`CMakePresets.json`](CMakePresets.json)).

Manual configure (equivalent):

```bash
cmake -S . -B build/linux-gcc-release -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=gcc \
  -DCMAKE_CXX_COMPILER=g++
cmake --build build/linux-gcc-release
```

### CMake options

| Option | Default (top-level) | Meaning |
| --- | --- | --- |
| `CCCR_BUILD_CLI` | `ON` | Build `cccr_cli` |
| `CCCR_BUILD_TESTS` | `ON` | doctest suites + CTest |
| `CCCR_BUILD_EXAMPLES` | `ON` | Example drivers under `examples/` |
| `CCCR_BUILD_BINDINGS_C` | `ON` | Shared C library `cccr_bindings_c` |
| `CCCR_BUILD_BINDINGS_PYTHON` | `ON` | pybind11 module `cccr_py` |
| `CCCR_REDLAND_USE_SYSTEM` | `ON` | Prefer pkg-config Redland; else vendored |
| `CCCR_ENABLE_LTO` | `ON` | LTO for Release / RelWithDebInfo when supported |
| `CCCR_ENABLE_INSTALL` | `OFF` | Install rules (API still unstable) |
| `CCCR_BUILD_SHARED` | `OFF` | Build `cccr::cccr` as `libcccr_core.so` instead of a static archive. Defines `CCCR_BUILD_SHARED` for the library and its consumers |
| `CCCR_CACHE_DIR` | `<project>/.cache` | Saxon (and related) persistent cache |
| `CCCR_SAXON_CHE_ROOT` | _(empty)_ | Pre-extracted SaxonC-HE root |

Core-only example:

```bash
cmake --preset linux-gcc-release \
  -DCCCR_BUILD_CLI=OFF \
  -DCCCR_BUILD_BINDINGS_C=OFF \
  -DCCCR_BUILD_BINDINGS_PYTHON=OFF \
  -DCCCR_BUILD_EXAMPLES=OFF
```

### Outputs

Binaries land under `bin/` (config/OS/arch suffix), for example:

```text
bin/cli/release-linux-x86_64/cccr_cli
bin/bindings/c/release-linux-x86_64/libcccr_bindings_c.so
bin/bindings/python/release-linux-x86_64/cccr_py*.so
bin/examples/...
```

Build trees: `build/<presetName>/`.

---

## Install (optional)

Install is off by default (`CCCR_ENABLE_INSTALL=OFF`) while the public API is unstable. When enabled:

```bash
cmake --preset linux-gcc-release -DCCCR_ENABLE_INSTALL=ON
cmake --build --preset linux-gcc-release
cmake --install build/linux-gcc-release --prefix /path/to/prefix
```

SaxonC-HE runtime libraries are redistributed with the install so installed tools can resolve them via RPATH. See [`cmake/Install.cmake`](cmake/Install.cmake).

Exported CMake targets (NAMESPACE `cccr::`): `cccr::cccr`, `cccr::bindings::c`. `cccr::cccr` is a shared library when `CCCR_BUILD_SHARED=ON` and a static archive otherwise. A static install still expects the consumer to link Redland and SaxonC-HE. A shared install keeps those inside `libcccr_core.so`.

### Python wheel (scikit-build)

[`pyproject.toml`](pyproject.toml) builds a wheel that installs the `cccr_py` extension (CMake `SKBUILD` path). Requires the same native deps as a normal build (SaxonC-HE cache, Redland, `python3-dev`).

```bash
# Prefer the same Python ABI CMake/pybind11 will use (e.g. 3.11)
python3.11 -m venv .venv-skbuild
source .venv-skbuild/bin/activate
pip install -U pip
pip install .          # or: pip wheel . -w dist/

python -c 'import cccr_py; print(cccr_py.__version__)'
python src/bindings/python/tests/smoke.py examples/data/base
```

A local `pip install .` installs SaxonC-HE next to `cccr_py` and records `$ORIGIN` as the extension RPATH, so the module loads Saxon without `LD_LIBRARY_PATH`. Other system libraries Redland needs (`libxml2`, ICU, curl) still come from the machine you built on. Release wheels vendor that closure too; see [GitHub releases](#github-releases).

---

## Bindings

Bindings build by default with top-level presets (`CCCR_BUILD_BINDINGS_C` / `CCCR_BUILD_BINDINGS_PYTHON`). They need the same core deps as the engine. For the Python module, also have a Python 3 interpreter and development headers available (pybind11 is vendored under `third-party/`).

```bash
# Debian/Ubuntu (in addition to the core packages above)
sudo apt install -y python3-dev
```

### Build only the binding libraries

```bash
cmake --preset linux-gcc-release
cmake --build --preset linux-gcc-release \
  --target cccr_bindings_c cccr_py

# Optional surface checks
ctest --preset linux-gcc-release -L bindings --output-on-failure
```

Adjust the preset name (`linux-gcc-debug`, `linux-gcc-relwithdebinfo`, …) to match your build. Artifact paths use a lowercase config suffix, e.g. `release-linux-x86_64` or `relwithdebinfo-linux-x86_64`.

Disable either binding at configure time with `-DCCCR_BUILD_BINDINGS_C=OFF` and/or `-DCCCR_BUILD_BINDINGS_PYTHON=OFF`.

### C shared library

**Artifact:** `bin/bindings/c/<config>-linux-<arch>/libcccr_bindings_c.so`

**Headers:** `src/bindings/c/include/` (umbrella: `cccr/bindings/c/cccr.h`)

The shared library is built with an RPATH that locates the SaxonC-HE runtime used by the engine. Link against the `.so` and add the public include tree:

```bash
BIND_C=bin/bindings/c/release-linux-x86_64   # adjust config/arch
INC=src/bindings/c/include

# Example: compile a small C program against the built library
cc -std=c11 app.c \
  -I"$INC" \
  -L"$BIND_C" -Wl,-rpath,"$PWD/$BIND_C" \
  -lcccr_bindings_c \
  -o app

./app
```

CMake consumers in-tree or after install can link `cccr::bindings::c`.

### Python extension module

**Artifact:** `bin/bindings/python/<config>-linux-<arch>/cccr_py*.so`  
(exact name includes the Python ABI tag, e.g. `cccr_py.cpython-311-x86_64-linux-gnu.so`)

Import by putting that directory on `PYTHONPATH` (and using the same Python major.minor the module was built against):

```bash
BIND_PY=bin/bindings/python/release-linux-x86_64   # adjust config/arch
export PYTHONPATH="$PWD/$BIND_PY${PYTHONPATH:+:$PYTHONPATH}"

python3 -c 'import cccr_py as cccr; print(cccr.__version__)'
```

The module `.so` also carries an RPATH for SaxonC-HE. A tiny smoke script used by CTest lives at [`src/bindings/python/tests/smoke.py`](src/bindings/python/tests/smoke.py):

```bash
python3 src/bindings/python/tests/smoke.py examples/data/base
```

---

## CLI quick start

After a CLI-enabled build:

```bash
CLI=bin/cli/release-linux-x86_64/cccr_cli   # adjust path
DATA=examples/data

"$CLI" --help
"$CLI" run --help
"$CLI" query --help

# Schema + XML + seed → RDF/XML
"$CLI" run \
  -s "$DATA/base/schema.json" \
  -i "$DATA/base/input.xml" \
  --seed "$DATA/base/seed.nt" \
  -o /tmp/out.rdf

# CSV input
"$CLI" run \
  -s "$DATA/kug/schema.json" \
  -i "$DATA/kug/input.csv" \
  --input-format csv \
  -o /tmp/kug.rdf

# SPARQL over RDF (json | xml | html)
"$CLI" query \
  -g "$DATA/base/seed.nt" \
  -q 'SELECT ?s ?p ?o WHERE { ?s ?p ?o }' \
  --format json
```

More recipes: [`examples/cli/README.md`](examples/cli/README.md).

### `run` flags (summary)

| Flag | Meaning |
| --- | --- |
| `-s` / `--schema` | CCCR JSON schema (required) |
| `-i` / `--input` | One or more XML/CSV inputs (merged) |
| `--input-format {xml,csv}` | Force format for all inputs (default: infer per extension) |
| `--seed` | Zero or more N-Triples seeds (merged knowledge) |
| `-o` / `--output` | RDF/XML path (default: stdout) |

### `query` flags (summary)

| Flag | Meaning |
| --- | --- |
| `-g` / `--graph` | One or more RDF files (N-Triples / Turtle / RDF/XML) |
| `-q` / `--query` | SPARQL text or path to a `.rq` file |
| `--format {json,xml,html}` | Result serialization (default: `json`) |
| `-o` / `--output` | Output path (default: stdout) |

---

## GitHub releases

Tagged releases (`vX.Y.Z`, matching `project(VERSION)` in `CMakeLists.txt` and `pyproject.toml`) publish Linux x86_64 artifacts for glibc 2.35 or newer (Ubuntu 22.04 and newer). They are built with GCC 14 and the vendored static Redland stack. SaxonC-HE is included. Redland is distributed under its Apache-2.0 license alternative; SaxonC-HE is MPL-2.0. Each archive has a `LICENSES/` directory.

| Download | What you get |
| --- | --- |
| `cccr-cli-<version>-linux-x86_64.tar.gz` | `bin/cccr_cli` plus the shared libraries it needs, including Saxon and the GCC 14 `libstdc++` |
| `cccr-c-<version>-linux-x86_64.tar.gz` | `libcccr_bindings_c.so`, `include/cccr/bindings/c/`, and the same bundled runtime |
| `cccr-cpp-<version>-linux-x86_64.tar.gz` | `libcccr_core.so` (SONAME 0), headers, Saxon, and a CMake package (`cccr::cccr`) |
| `cccr_py-<version>-cp3xx-cp3xx-manylinux_2_35_x86_64.whl` | One wheel each for CPython 3.10, 3.11, 3.12, and 3.13 |

The CLI and the C library bundle GCC 14's `libstdc++`. Use them from C or from a process that is not already linked to a different `libstdc++`. The C++ shared library uses the caller's GCC 14 `libstdc++`, so link it with `g++-14`. The C++ API is still unstable (`SOVERSION` 0). `CCCR_BUILD_SHARED` selects that shared `cccr::cccr`; the release build turns it on.

```bash
# CLI
tar -xzf cccr-cli-0.1.0-linux-x86_64.tar.gz
./cccr-cli-0.1.0-linux-x86_64/bin/cccr_cli --help

# C
tar -xzf cccr-c-0.1.0-linux-x86_64.tar.gz
cc -std=c11 app.c \
  -I cccr-c-0.1.0-linux-x86_64/include \
  -L cccr-c-0.1.0-linux-x86_64/lib \
  -Wl,-rpath,'$ORIGIN/../lib' -Wl,--disable-new-dtags \
  -lcccr_bindings_c

# C++ (g++-14, plus libxml2 and zlib)
cmake -S your_app -B build \
  -DCMAKE_PREFIX_PATH=$PWD/cccr-cpp-0.1.0-linux-x86_64 \
  -DCMAKE_CXX_COMPILER=g++-14
# target_link_libraries(your_app PRIVATE cccr::cccr)

# Python
pip install cccr_py-0.1.0-cp311-cp311-manylinux_2_35_x86_64.whl
```
