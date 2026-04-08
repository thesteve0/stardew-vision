# Container Image Build Instructions

## ⚠️ CRITICAL: Run on Host Machine Only

**All Docker build and push operations MUST be performed on your host machine**, not inside the devcontainer.

### Why?

The devcontainer environment:
- Does not have Docker-in-Docker configured for builds
- May have network/authentication issues for registry pushes
- Is optimized for development, not image building

### How to Build and Push

1. **Exit the devcontainer** (if you're currently inside it)
   - In VS Code: Use Command Palette → "Dev Containers: Reopen Folder Locally"
   - Or close VS Code and open a terminal on your host machine

2. **Navigate to the repository root** on your host machine
   ```bash
   cd /path/to/stardew-vision
   ```

3. **Run the build script**
   ```bash
   ./deploy/build-images.sh v0.1.0
   ```

4. **Login to GitHub Container Registry**
   ```bash
   docker login ghcr.io
   # Username: thesteve0
   # Password: <GitHub Personal Access Token with write:packages scope>
   ```

5. **Push all images**
   ```bash
   docker push ghcr.io/thesteve0/stardew-coordinator:v0.1.0
   docker push ghcr.io/thesteve0/stardew-ocr-tool:v0.1.0
   docker push ghcr.io/thesteve0/stardew-tts-tool:v0.1.0
   docker push ghcr.io/thesteve0/stardew-coordinator:latest
   docker push ghcr.io/thesteve0/stardew-ocr-tool:latest
   docker push ghcr.io/thesteve0/stardew-tts-tool:latest
   ```

6. **Make packages public** (they're private by default)
   - Go to https://github.com/thesteve0?tab=packages
   - For each package (stardew-coordinator, stardew-ocr-tool, stardew-tts-tool):
     - Click on the package name
     - Click "Package settings" (right sidebar)
     - Scroll to "Danger Zone"
     - Click "Change visibility" → Select "Public" → Confirm

## Verification

After pushing, verify the images are accessible:

```bash
# Should work without authentication if packages are public
docker pull ghcr.io/thesteve0/stardew-coordinator:v0.1.0
docker pull ghcr.io/thesteve0/stardew-ocr-tool:v0.1.0
docker pull ghcr.io/thesteve0/stardew-tts-tool:v0.1.0
```

If you get "unauthorized" errors, the packages are still private.

## Alternative: Use Pull Secrets

If you prefer to keep packages private, you can create a Kubernetes pull secret:

```bash
oc create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=thesteve0 \
  --docker-password=<your-PAT> \
  --namespace=stardew-vision

# Then update deployments to reference the secret:
# spec.template.spec.imagePullSecrets:
#   - name: ghcr-pull-secret
```

However, public packages are simpler for MVP deployment.

## Troubleshooting

### "docker: command not found" in devcontainer
✅ **Expected behavior** - exit the devcontainer and run on host

### "permission denied while trying to connect to Docker daemon"
Run: `sudo usermod -aG docker $USER` then log out and back in

### "unauthorized: unauthenticated" when pushing
Run: `docker login ghcr.io` and provide GitHub username + PAT

### Images build but fail to push
Check your GitHub Personal Access Token has `write:packages` scope
