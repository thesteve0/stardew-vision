# Images: preserve the verified deployment

Normal deployments **do not build images**. Run `./deploy/deploy-to-openshift.sh`
using the digest-pinned coordinator v0.8.2, unified OCR v0.3.5 and TTS v0.4.0
manifests. See [the canonical guide](README.md).

For intentional source changes only, build a new, unique tag on a host with
Podman or Docker and registry authentication:

```bash
CONTAINER_ENGINE=podman ./deploy/build-images.sh <new-unique-version>
```

The build helper covers only the three active services and never overwrites
`latest`. Building is not deployment: audit the resulting package/assets and
resolved dependencies, run regressions and end-to-end tests, push the unique tag,
resolve its registry digest, then review manifest changes explicitly.

## Locked service builds

Each active service has its own committed `uv.lock`, recovered from the audited
production image: coordinator v0.8.2, OCR v0.3.4 (the unchanged dependency base of
v0.3.5), and TTS v0.4.0. These are **not** the root development/training lockfile,
which excludes dependencies and must not be used for service builds. Existing
locked dependency versions were preserved. TTS additionally declares the exact
`en_core_web_sm` 3.8.0 wheel previously installed outside its lockfile; its URL
and SHA256 are now in the lock.

The Dockerfiles pin Python 3.12 and uv 0.11.8 by image digest, copy both project
metadata and the service lock, install with `uv sync --frozen --no-dev`, and
check lock freshness offline after installation (direct-URL metadata must be
cached first). A stale lock fails the build. Runtime commands are frozen, and
`UV_NO_SYNC=1` prevents dependency installation at startup, including arbitrary
OpenShift UIDs. The coordinator defaults to the fine-tuned application.
`.dockerignore` restricts build context to active service inputs, excluding
local environments, datasets, Git metadata and credentials.

Before building, run the offline contract checks:

```bash
python3 -m unittest discover -s tests -p 'test_*contract.py' -v
```

For an intentional dependency update, use uv 0.11.8 in the service directory,
update `pyproject.toml` as needed, regenerate **that service's** lock, and review
all changed versions and hashes. `uv lock --check` validates freshness; it may
need network access to inspect direct-URL metadata on a cold cache. Do not use
`--upgrade` for routine builds. Local source runs use service locks too.

### Remaining reproducibility limits

This pins the Python dependency graph and build-tool/base image identities,
not byte-for-byte container output. OCR/TTS system packages still come from
live Debian repositories. A future OS reproducibility step would use a reviewed
Debian snapshot or digest-pinned system-dependency base images. Runtime OCR and
Kokoro model downloads are also separate from Python locks and are not yet
fully artifact-pinned. Source distributions may depend on build tooling outside
the runtime lock. Newly built images still need source/dependency audits and
functional tests before production promotion.

OCR v0.3.5 was built from the audited v0.3.4 image to preserve its environment
while fixing low-confidence background OCR. These build improvements do **not**
replace that verified image or any production digest. Never embed registry/HF
tokens in commands, Dockerfiles, manifests, or Git.
