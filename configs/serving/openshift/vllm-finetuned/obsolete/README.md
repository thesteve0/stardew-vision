# Historical EFS manifest — not part of deployment

`00-pv-lora-adapter.yaml` records the old static EFS access-point binding for
historical reference only. **Do not apply it**, or apply this directory
recursively. The active adapter PVC is dynamically provisioned by `gp3-csi` and
populated from the private, pinned Hugging Face repository instead.

The historical EFS adapter's byte identity with the local v1/Hugging Face
artifact is unproven. This manifest is not evidence of provenance or of current
EFS availability. Do not recreate the historical path as part of this flow.
