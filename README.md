<!--
SPDX-FileCopyrightText: 2025 Pierre-Noel Bouteville  <pnb990@gmail.com>

SPDX-License-Identifier: BSD-3-Clause
-->

Docker Images Repository
========================

**Overview**
- **Purpose:** This repository generates and builds Docker images from templates and Dockerfile generators. The generator writes Dockerfiles into the `images/` directory and the CI workflow builds and pushes them.

**Prerequisites**
- **OS:** Tested on Debian/Ubuntu-like systems.
- **Tools:** `python3`, `pipenv`, `jq`, `git`, and `docker` (for building/pushing).
- **Install minimal deps (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv pipenv jq git docker-cli
```

**Regenerate the Dockerfiles**
- **What it does:** Runs the repository's generator script which writes Dockerfiles to `images/`.
- **Command (local):**
```bash
pipenv install --deploy
pipenv run python3 ./src/main.py
```
- After this the `images/` directory contains `*.Dockerfile` files created by the generator.

**Add a new Dockerfile**
- **Manual:** create a file named `images/<your-name>.Dockerfile`, commit and push. The CI will pick it up.
- **Via template/generator:**
  - Add a template under `ressources/templates/` (there are existing templates to copy from).
  - Update the generator (`src/main.py`) to include the new template or generation rule.
  - Run the generator locally to create the Dockerfile, verify, then commit the generated file and generator changes.

**CI workflow & outputs**
- The CI workflow file is at [.forgejo/workflows/build.yaml](.forgejo/workflows/build.yaml).
- One step collects the list of Dockerfiles and writes an output block into the runner outputs file using the runner variable `FORGEJO_OUTPUT`.
- Important: the name used when emitting the output must match the job output key used later. For example, if the job sets

- Job outputs (prepare job) use `dockerfiles:` in the workflow header. Ensure the step emits `dockerfiles<<EOF` rather than `files<<EOF`.

Example corrected snippet (inside the step that lists Dockerfiles):
```bash
files=$(printf '"%s"\n' images/*.Dockerfile | jq -R . | jq -s .)
{
  echo "dockerfiles<<EOF"
  echo "$files"
  echo "EOF"
} >> "$FORGEJO_OUTPUT"
```

**Notes & troubleshooting**
- If the glob `images/*.Dockerfile` matches nothing the shell might pass the literal pattern. To be robust use `find` or enable `nullglob`.
  Example robust command:
```bash
files=$(find images -name '*.Dockerfile' -print0 | xargs -0 -r printf '"%s"\n' | jq -R . | jq -s .)
```
- If CI still reports an empty matrix, verify the output name (see previous section) and that the `images/` files exist and are committed before the listing step runs.

**Run a single image build locally (quick test)**
```bash
docker build -f images/example.Dockerfile -t local/example:latest .
```

**Contributing**
- Update `src/main.py` when changing generation logic.
- Add or update templates under `ressources/templates/`.

**Useful files**
- Generator script: [src/main.py](src/main.py)
- CI workflow: [.forgejo/workflows/build.yaml](.forgejo/workflows/build.yaml)

Thank you — if you want, I can also update the workflow to emit `dockerfiles` instead of `files` to match the job output key.
