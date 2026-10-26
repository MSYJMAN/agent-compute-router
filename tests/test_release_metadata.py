"""Release gates that are checked locally, not only in CI.

GitHub Actions is currently blocked by account billing, so the gates the release
workflow enforces are duplicated here. A local suite that passes is then real
evidence about release readiness rather than a claim resting on a workflow that
has never run.
"""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


class VersionConsistencyTests(unittest.TestCase):
    def test_changelog_has_an_entry_for_the_declared_version(self):
        """Mirrors the release workflow's changelog gate."""
        version = pyproject()["project"]["version"]
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{version}]", changelog)

    def test_declared_version_is_the_newest_changelog_section(self):
        version = pyproject()["project"]["version"]
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        sections = re.findall(r"^## \[([^\]]+)\]", changelog, flags=re.MULTILINE)
        dated = [s for s in sections if s.lower() != "unreleased"]
        self.assertTrue(dated, "changelog has no released sections")
        self.assertEqual(dated[0], version)

    def test_cli_entry_point_resolves(self):
        import importlib

        target = pyproject()["project"]["scripts"]["compute-router"]
        module_name, _, attribute = target.partition(":")
        module = importlib.import_module(module_name)
        self.assertTrue(callable(getattr(module, attribute)))


class ClassifierTests(unittest.TestCase):
    def test_ci_python_matrix_matches_the_declared_classifiers(self):
        """A version CI tests but does not advertise is a metadata bug."""
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        matrix = set(re.findall(r'"(3\.\d+)"', workflow))
        classifiers = {
            line.rsplit("::", 1)[1].strip()
            for line in pyproject()["project"]["classifiers"]
            if line.startswith("Programming Language :: Python :: 3.")
        }
        self.assertTrue(matrix, "no python versions found in the CI workflow")
        self.assertEqual(matrix, classifiers)

    def test_requires_python_floor_is_advertised(self):
        data = pyproject()["project"]
        floor = data["requires-python"].lstrip(">=")
        self.assertIn(f"Programming Language :: Python :: {floor}", data["classifiers"])


class LicenseTests(unittest.TestCase):
    def test_license_is_the_complete_apache_2_text(self):
        """A declared SPDX expression must match the shipped text."""
        self.assertEqual(pyproject()["project"]["license"], "Apache-2.0")
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Apache License", text)
        self.assertIn("Version 2.0, January 2004", text)
        self.assertIn("APPENDIX: How to apply the Apache License", text)
        # The full license body has nine numbered sections.
        sections = re.findall(r"^\s+(\d)\. [A-Z]", text, flags=re.MULTILINE)
        self.assertEqual(sorted(set(sections)), [str(n) for n in range(1, 10)])

    def test_license_has_no_unfilled_placeholders(self):
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        for placeholder in ("[yyyy]", "[name of copyright owner]"):
            self.assertNotIn(placeholder, text)


class SecretHygieneTests(unittest.TestCase):
    TRACKED_SUFFIXES = (".py", ".md", ".toml", ".yml", ".yaml", ".json")
    PATTERNS = (
        re.compile(r"\bDEV-[0-9a-fA-F]{20,}\b"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"(?i)\bdwave_api_token\s*[:=]\s*['\"]?[A-Za-z0-9\-]{12,}"),
    )

    def test_repository_contains_no_credential_shaped_strings(self):
        offenders: list[str] = []
        skip = {".git", ".venv", "dist", "build", "__pycache__"}
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in self.TRACKED_SUFFIXES:
                continue
            if any(part in skip for part in path.parts):
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            for pattern in self.PATTERNS:
                for match in pattern.finditer(content):
                    # The sanitizer test deliberately contains a fake token.
                    if path.name in {"test_provider_states.py", "test_hybrid_orchestration.py"}:
                        continue
                    offenders.append(f"{path.relative_to(ROOT)}: {match.group()[:24]}")
        self.assertEqual(offenders, [])

    def test_no_env_files_are_tracked(self):
        for name in (".env", ".env.local", "dwave.conf"):
            self.assertFalse((ROOT / name).exists(), f"{name} must not be committed")


if __name__ == "__main__":
    unittest.main()
