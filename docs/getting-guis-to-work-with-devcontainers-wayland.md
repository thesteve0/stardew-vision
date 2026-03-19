# Getting GUI Windows Working in a Devcontainer on Wayland

## Context

This project uses a VS Code devcontainer on a Linux host running a native Wayland session
(Fedora 43, GNOME-Wayland). We need `cv2.selectROI()` and `cv2.imshow()` to open real GUI
windows for interactive use (e.g., anchor template extraction).

Flatpaks are the conceptual model: they are containers that access the host Wayland compositor
by being given a bind-mounted socket. Docker devcontainers can do the same thing.

---

## How Wayland Socket Forwarding Works

The Wayland compositor (e.g., GNOME Shell) creates a Unix socket that clients connect to.
Its path is:

```
$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY
# typically: /run/user/1000/wayland-0
```

To give a container access, you:
1. Bind-mount that socket file into the container
2. Set `WAYLAND_DISPLAY` and `XDG_RUNTIME_DIR` so the container app can find it

No X server, no VNC, no XWayland needed.

---

## Why X11 Forwarding Was Not Used

The host runs a pure Wayland session. `$DISPLAY` is not set and `/tmp/.X11-unix` does not
exist. Configuring XWayland just to forward X11 back into the container adds unnecessary
complexity. Native Wayland forwarding is simpler and more correct.

---

## UID Consideration

Wayland socket files are owned by the host user and `XDG_RUNTIME_DIR` has `0700` permissions.
If the container user UID does not match the host user UID, the container cannot access the
socket.

In this project the container user (`stpousty-devcontainer`) runs as **UID 1000**, which
matches the host user UID, so there is no mismatch. Verify with `id` inside the container.

If your container user has a different UID, the workaround is to mount the socket to `/tmp/`
(world-accessible) and set `XDG_RUNTIME_DIR=/tmp` — which is what this project does anyway
to avoid depending on `/run/user/1000/` existing inside the container.

---

## OpenCV Backend

`cv2.imshow` / `cv2.selectROI` need a GUI backend. Check which one OpenCV was built with:

```python
import cv2
bi = cv2.getBuildInformation()
print([l for l in bi.splitlines() if any(x in l for x in ('GUI', 'QT', 'GTK', 'Wayland'))])
```

In this project, `opencv-python` (installed via `uv`) uses **Qt5**. The Qt5 Wayland platform
plugin (`qtwayland5`) was already present in the container image. No Dockerfile changes were
needed.

If you get `Could not find the Qt platform plugin "wayland"`, install `qtwayland5`:
```bash
sudo apt-get install qtwayland5
```

---

## Configuration Applied to This Project

### `devcontainer.json` changes

**In `runArgs`** — bind-mount the host Wayland socket:
```json
"--volume=/run/user/1000/wayland-0:/tmp/wayland-0"
```

**In `containerEnv`** — point apps at the mounted socket:
```json
"WAYLAND_DISPLAY": "wayland-0",
"XDG_RUNTIME_DIR": "/tmp",
"QT_QPA_PLATFORM": "wayland",
"GDK_BACKEND": "wayland"
```

`QT_QPA_PLATFORM=wayland` tells Qt5 (and therefore OpenCV) to use the Wayland backend.
`GDK_BACKEND=wayland` does the same for any GTK3 applications.

### No Dockerfile changes required

The container image already had:
- `libwayland-client0`
- `libqt5waylandclient5`
- `qtwayland5`
- `libgtk-3-0`

---

## Steps to Enable After Cloning / Rebuilding

1. **Verify socket path on your host** (run on the host, outside the container):
   ```bash
   echo $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY
   # Expected: /run/user/1000/wayland-0
   ```
   If the socket name or UID differs, update the `--volume` line in `devcontainer.json`.

2. **Rebuild the devcontainer**:
   `Ctrl+Shift+P` → `Dev Containers: Rebuild Container`

3. **Verify inside the container** after rebuild:
   ```bash
   echo $WAYLAND_DISPLAY      # wayland-0
   echo $XDG_RUNTIME_DIR      # /tmp
   ls /tmp/wayland-0          # socket file should exist
   ```

4. **Smoke test** with a minimal Python script:
   ```python
   import cv2
   import numpy as np
   img = np.zeros((200, 400, 3), dtype=np.uint8)
   cv2.putText(img, "Wayland works!", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
   cv2.imshow("test", img)
   cv2.waitKey(0)
   cv2.destroyAllWindows()
   ```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ls /tmp/wayland-0` — no such file | Socket not mounted | Check `--volume` path; verify socket exists on host |
| `Could not find Qt platform plugin "wayland"` | `qtwayland5` not installed | `sudo apt-get install qtwayland5` |
| Window opens but immediately crashes | UID mismatch on socket | Mount socket to `/tmp`, set `XDG_RUNTIME_DIR=/tmp` |
| `GDK_BACKEND` warning in GTK apps | Irrelevant if using Qt5 backend | Ignore or unset `GDK_BACKEND` |
| Works in terminal, not in VS Code integrated terminal | VS Code may override env vars | Run from an external terminal or check `remoteEnv` in devcontainer.json |

---

## References

- [x11docker wiki: How to provide Wayland socket to docker container](https://github.com/mviereck/x11docker/wiki/How-to-provide-Wayland-socket-to-docker-container)
- [jasoncg.dev: Developing GUI App in VSCode DevContainer (Wayland)](https://jasoncg.dev/blog/2023/developing-gui-app-bevy-in-vscode-devcontainer-wayland/)
- [Wayland Apps in WireGuard Docker Containers](https://www.procustodibus.com/blog/2024/10/wayland-wireguard-containers/)
- [How I Built a Dev Container Workflow with Flatpak VSCode, Devcontainer and Podman on Wayland](https://zihad.com.bd/posts/setup-flatpak-vscode-devcontainer-podman-wayland-gui/)
- [opencv-python Wayland Qt platform plugin issue tracker](https://github.com/opencv/opencv-python/issues/729)
