"""Offline guards for the three active services' locked container builds."""
from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("coordinator", "ocr-tools", "tts-tool")


class ServiceBuildContractTests(unittest.TestCase):
    def test_each_service_has_complete_hashed_lock(self):
        for name in SERVICES:
            with self.subTest(service=name):
                directory = ROOT / "services" / name
                project = tomllib.loads((directory / "pyproject.toml").read_text())
                lock = tomllib.loads((directory / "uv.lock").read_text())
                package = next(p for p in lock["package"]
                               if p["name"] == project["project"]["name"])
                self.assertEqual(package["version"], project["project"]["version"])
                self.assertNotIn("exclude-dependencies", lock.get("options", {}))
                for dependency in lock["package"]:
                    if dependency is package:
                        continue
                    artifacts = dependency.get("wheels", [])
                    if "sdist" in dependency:
                        artifacts = artifacts + [dependency["sdist"]]
                    self.assertTrue(artifacts, dependency["name"])
                    for artifact in artifacts:
                        self.assertRegex(artifact["hash"], r"^sha256:[0-9a-f]{64}$")

    def test_dockerfiles_pin_inputs_and_never_resolve_at_runtime(self):
        for name in SERVICES:
            with self.subTest(service=name):
                text = (ROOT / "services" / name / "Dockerfile").read_text()
                self.assertRegex(text, r"FROM python:3\.12-slim@sha256:[0-9a-f]{64}\n")
                self.assertRegex(text, r"COPY --from=ghcr.io/astral-sh/uv:0\.11\.8@sha256:[0-9a-f]{64} ")
                self.assertIn(f"services/{name}/uv.lock", text)
                self.assertIn("uv lock --check --offline", text)
                self.assertIn("uv sync --frozen --no-dev", text)
                self.assertIn('"run", "--frozen", "--no-dev"', text)
                self.assertIn("ENV UV_NO_SYNC=1", text)
                self.assertNotIn("pip install", text)
                self.assertNotIn("spacy download", text)
        coordinator = (ROOT / "services/coordinator/Dockerfile").read_text()
        self.assertIn("stardew_coordinator.app_finetuned:app", coordinator)

    def test_spacy_model_is_an_explicit_hashed_dependency(self):
        lock = tomllib.loads((ROOT / "services/tts-tool/uv.lock").read_text())
        model = next(p for p in lock["package"] if p["name"] == "en-core-web-sm")
        self.assertEqual(model["version"], "3.8.0")
        self.assertIn("en_core_web_sm-3.8.0", model["source"]["url"])
        self.assertTrue(model["wheels"])
        self.assertRegex(model["wheels"][0]["hash"], r"^sha256:[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
