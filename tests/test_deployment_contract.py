"""Guard the single verified OpenShift deployment against manifest drift.

Run: python3 -m unittest discover -s tests -p test_deployment_contract.py -v
Requires PyYAML; does not contact the cluster.
"""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "configs/serving/openshift"


class DeploymentContractTests(unittest.TestCase):
    def setUp(self):
        self.resources = [obj for path in MANIFESTS.rglob("*.yaml")
                          for obj in yaml.safe_load_all(path.read_text())]

    def resource(self, kind, name):
        return next(obj for obj in self.resources
                    if obj["kind"] == kind and obj["metadata"]["name"] == name)

    def test_only_primary_finetuned_route(self):
        routes = [obj for obj in self.resources if obj["kind"] == "Route"]
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0]["metadata"]["name"], "stardew-vision")
        self.assertEqual(routes[0]["spec"]["to"]["name"], "coordinator-finetuned")

    def test_only_finetuned_predictor_and_active_services(self):
        self.assertEqual({obj["metadata"]["name"] for obj in self.resources
                          if obj["kind"] == "InferenceService"}, {"stardew-vlm-finetuned"})
        self.assertEqual({obj["metadata"]["name"] for obj in self.resources
                          if obj["kind"] == "Deployment"},
                         {"coordinator-finetuned", "ocr-tools", "tts-tool"})
        self.assertFalse((MANIFESTS / "vllm").exists())
        self.assertFalse(any(path.name == "obsolete" for path in MANIFESTS.rglob("*")))

    def test_all_images_digest_pinned_and_storage_gp3(self):
        for obj in self.resources:
            if obj["kind"] in ("Deployment", "Job"):
                pod = obj["spec"]["template"]["spec"]
            elif obj["kind"] == "ServingRuntime":
                pod = obj["spec"]
            else:
                pod = {}
            for container in pod.get("containers", []) + pod.get("initContainers", []):
                self.assertRegex(container["image"], r"@sha256:[0-9a-f]{64}$")
            if obj["kind"] == "PersistentVolumeClaim":
                self.assertEqual(obj["spec"]["storageClassName"], "gp3-csi")
                self.assertEqual(obj["spec"]["accessModes"], ["ReadWriteOnce"])

    def test_finetuned_entrypoint_and_discovery(self):
        deployment = self.resource("Deployment", "coordinator-finetuned")
        command = deployment["spec"]["template"]["spec"]["containers"][0]["command"]
        self.assertIn("stardew_coordinator.app_finetuned:app", command)
        data = self.resource("ConfigMap", "service-endpoints-finetuned")["data"]
        self.assertEqual(data["AGENT_MODE"], "finetuned")
        self.assertEqual(data["VLLM_MODEL"], "stardew-vlm-finetuned")
        self.assertEqual(data["OCR_TOOL_URL"], "http://ocr-tools:8004")

    def test_verified_images_and_artifact_contract(self):
        versions = {"coordinator-finetuned": "v0.8.2", "ocr-tools": "v0.3.5", "tts-tool": "v0.4.0"}
        for name, version in versions.items():
            deployment = self.resource("Deployment", name)
            image = deployment["spec"]["template"]["spec"]["containers"][0]["image"]
            self.assertIn(":" + version + "@sha256:", image)
        runtime = self.resource("ServingRuntime", "stardew-vlm-finetuned")
        args = runtime["spec"]["containers"][0]["args"]
        self.assertIn("--served-model-name=qwen-base", args)
        self.assertIn("--lora-modules={{.Name}}=/mnt/lora-adapter/model-output", args)
        job = self.resource("Job", "download-lora-adapter")
        code = job["spec"]["template"]["spec"]["containers"][0]["args"][0]
        self.assertIn("73cb70b1718e2a09af55d823701fcd26b3c6a333", code)
        self.assertIn("373c475669049191527b3d8e8a330f347f236855482bb2282f9604177a915a63", code)
        self.assertIn("449c057c21c46e3bc0d32d4d7a3590112927c756ae4a7e0ec6326cdc91e2e478", code)


if __name__ == "__main__":
    unittest.main()
