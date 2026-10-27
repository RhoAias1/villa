# Reproduction from a clean checkout

This recipe preserves the layout used by the published measurement scripts. Use a new scratch directory. The tested code is commit `2c50a2d40dbe4ed48a9e4b5e4ecf7511d94283e2`; its only changes from upstream `39a8cf3a124bdd5540ee826e1cb30047c8dc8c85` are the four files in `submission.patch`.

## 1. Obtain code and this evidence package

Clone the fork's `evidence/single-fiber-export-20261027` branch. Its `submission-evidence/` directory contains this file. Copy that directory's contents into a fresh work directory, then run all commands below from that work directory.

```sh
git clone https://github.com/RhoAias1/villa.git villa-export
git -C villa-export checkout 2c50a2d40dbe4ed48a9e4b5e4ecf7511d94283e2
mkdir -p audit/scratch
git clone https://github.com/ScrollPrize/villa.git audit/scratch/base-src
git -C audit/scratch/base-src checkout 39a8cf3a124bdd5540ee826e1cb30047c8dc8c85
```

Keep the published `evidence/` as the historical results. When creating fresh stores, first move the historical `evidence/export-databases/provenance.json` to `published-store-provenance.json`; `prepare_inputs.py` writes a new receipt for the newly imported stores. Store files may differ because import history contains generated identifiers/timestamps. Comparisons must use the same newly built store for both implementations, and verify source files against the published manifests.

## 2. Build

Dependencies: C++20 compiler, CMake, Ninja, SQLite3, OpenSSL Crypto, nlohmann-json, zstd, and OpenCV core. Linking/Python additionally require the reader dependencies shown in the Dockerfile. The tested Linux environment is documented in [export-environment.json](evidence/export-environment.json) and [Dockerfile](linux-env/Dockerfile).

For the published Linux image recipe, place the OpenCV archive at `linux-env/opencv-4.14.0.tar.gz`:

```sh
curl -fL https://github.com/opencv/opencv/archive/refs/tags/4.14.0.tar.gz -o linux-env/opencv-4.14.0.tar.gz
docker build --platform linux/arm64 -t fiber-export-review linux-env
```

The Dockerfile checks SHA-256 `ee8fb9b30eb60850431b4656447080e3737b56e45719c92b67f245950609f86e`. Its Python dependency installation is not fully locked; the exact versions from the tested image are recorded in `export-environment.json`. Linux distribution packages are also not byte-for-byte locked. A fresh dependency build is a reproduction environment, not a claim that its binaries match the published macOS hashes.

On Linux in that environment, configure the two independent builds:

```sh
cmake -S audit/scratch/base-src/vc_object_store -B audit/scratch/base-build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/opt/opencv -DVC_OBJECT_STORE_BUILD_PYTHON=ON
cmake --build audit/scratch/base-build -j 2
cmake -S villa-export/vc_object_store -B build-export -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/opt/opencv -DVC_OBJECT_STORE_BUILD_PYTHON=ON
cmake --build build-export -j 2
ctest --test-dir build-export --output-on-failure
VC_OBJECT_STORE_BUILD_PYTHON_PATH="$PWD/build-export/python" PYTHONDONTWRITEBYTECODE=1 python -m pytest -q villa-export/vc_object_store/tests/python
```

For macOS, point `CMAKE_PREFIX_PATH` at your OpenCV installation and configure both builds with `-DVC_OBJECT_STORE_BUILD_LINKING=OFF -DVC_OBJECT_STORE_BUILD_PYTHON=OFF`. That matches the native benchmark setup and avoids the unrelated reader build issue in upstream PR #2300. Run CTest there as well.

When using Docker, mount this work directory as `/work` and execute the Linux commands inside the container. No network is needed for tests after dependencies and data have been obtained.

## 3. Prepare identical real inputs

`prepare_inputs.py` downloads **only the files in the frozen manifests**, verifies every original hash, and creates copies in `audit/scratch/relabel-v3-{0332,0139}` changing only version 4 to version 3. It then invokes the **unmodified baseline importer** and records each resulting store hash. The migration route is credited in the main report; it is not part of the proposed code change.

```sh
python3 -I prepare_inputs.py
python3 -I prepare_inputs.py --verify-only
```

Expected source counts: 255 files for PHerc0332 and 620 for PHerc0139. Original annotations remain untouched. The downloader fails if the public files no longer match their recorded hashes; it does not silently update the dataset.

## 4. Compare every export

```sh
python3 -I build_export_helper.py audit/scratch/base-build audit/scratch/base-src/vc_object_store
python3 -I build_export_helper.py build-export villa-export/vc_object_store
python3 -I verify_export_corpus.py --output evidence/export-validation
```

`build_export_helper.py` reuses each build's Ninja link command, substituting the identical verification source. Its extra `/opt/homebrew/include` search path is unused on Linux. `verify_export_corpus.py` refuses to overwrite an existing output directory. It checks all output bytes against the unmodified upstream network encoder, XYZ positions, known coordinate bindings, original source hashes, migration contents, and unchanged store hashes.

The published completed run is under `evidence/export-final-validation/`. A clean run uses `evidence/export-validation/`, which is also where the timing script reads its expected output hashes.

## 5. Run the native macOS timing benchmark

```sh
mkdir -p evidence/baseline-bin
cp audit/scratch/base-build/bin/vc_object_export evidence/baseline-bin/vc_object_export
python3 -I benchmark_fiber_export.py --output evidence/reproduction-benchmark
```

This script uses macOS `/usr/bin/time -l` and must be run natively on macOS for comparable RSS units and timing behavior. It is not a Linux timing script. It checks each exported file against the independently generated reference, measures one excluded warmup and five paired trials, alternates order, and verifies the input store remains unchanged. Do not run concurrent workloads during measurement. Timings include process startup and depend on hardware, filesystem cache, compiler and dependencies.

The three recorded roots are the 184-fiber PHerc0332 component, 602-fiber PHerc0139 component, and isolated PHerc0139 control; exact UUIDs and source filenames appear in the measurement JSON. Do not extrapolate these three ratios to all fibers or a complete scroll-reading pipeline.

## Scope of the packaged recipe

The benchmark, corpus verifier, helper source and helper compiler are the same scripts used in the reported experiments. `prepare_inputs.py` is a packaging convenience for the documented import procedure; its verification-only path was checked against the original 875 files, migration copies and frozen stores. The fresh-directory download/build recipe has not been rerun as a third complete experiment. The historical test and corpus results are preserved, rather than represented as a new run of this packaging recipe.
