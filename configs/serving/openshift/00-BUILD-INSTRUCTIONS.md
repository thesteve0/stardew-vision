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

The current Dockerfiles resolve dependencies during builds and are not fully
reproducible from lockfiles. OCR v0.3.5 was built from the audited v0.3.4 image to
preserve its dependency environment while fixing low-confidence background OCR.
A normal Dockerfile rebuild may not recreate that environment. Do not casually
replace the verified image just to redeploy. Never embed registry/HF tokens in
commands, Dockerfiles, manifests, or Git.
