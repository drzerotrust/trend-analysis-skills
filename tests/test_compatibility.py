"""Check the installed news CLI offline, without importing its source checkout."""

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "trend-analisis"
COMPATIBILITY_PATH = ROOT / "compatibility.json"
COMPATIBILITY_TEXT = COMPATIBILITY_PATH.read_text(encoding="utf-8")
COMPATIBILITY = json.loads(COMPATIBILITY_TEXT)


class CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = shutil.which("trend-engine")
        if cls.binary is None:
            raise RuntimeError("Install a compatible trend-engine and put it on PATH.")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.config = self.directory / "operator config.toml"
        self.config.write_text(
            'sources = ["hacker_news"]\ndatabase = "unused.db"\n', encoding="utf-8"
        )
        self.environment = dict(os.environ)

        # YouTube is the only optional provider key used by the current CLI.
        for key in ("YOUTUBE_API_KEY", "PYTHONPATH", "PYTHONHOME"):
            self.environment.pop(key, None)

        # Explicit selection isolates tests from the installed CLI's real credentials.
        self.env_file = self.directory / "private test.env"
        self.env_file.write_text("", encoding="utf-8")
        self.environment["TREND_ENGINE_ENV_FILE"] = str(self.env_file)
        self.environment.pop("PYTHON_DOTENV_DISABLED", None)

    def run_cli(self, *argv):
        return subprocess.run(
            [self.binary, *argv],
            cwd=self.directory,
            env=self.environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            check=False,
        )

    def preflight_args(self):
        versions = COMPATIBILITY["trend_engine"]
        args = [
            "doctor",
            "--json",
            "--config",
            str(self.config),
            "--min-version",
            versions["minimum"],
            "--max-version",
            versions["maximum_exclusive"],
        ]

        for name, version in COMPATIBILITY["contracts"].items():
            args += ["--require-%s-schema" % name, str(version)]

        return args

    def test_supported_installation_and_version_command(self):
        args = self.preflight_args()
        result = self.run_cli(*args)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        document = json.loads(result.stdout)

        self.assertEqual(
            document["doctor_version"], COMPATIBILITY["contracts"]["doctor"]
        )
        self.assertEqual(document["status"], "success")
        self.assertEqual(document["contracts"], COMPATIBILITY["contracts"])
        self.assertEqual(document["configuration"]["status"], "ok")
        self.assertEqual(document["errors"], [])
        self.assertFalse(document["network_checked"])
        version = self.run_cli("--version")

        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertEqual(
            version.stdout.strip(), "trend-engine %s" % document["version"]
        )
        database_path = self.directory / "unused.db"

        self.assertFalse(database_path.exists())

    def test_bundled_contracts_match_installed_cli(self):
        for name, version in COMPATIBILITY["contracts"].items():
            with self.subTest(contract=name):
                filename = "%s.schema.json" % name
                path = SKILL / "references" / filename
                text = path.read_text(encoding="utf-8")
                expected = json.loads(text)

                result = self.run_cli("schema", name)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), expected)
                self.assertEqual(
                    expected["$id"], "urn:trend-engine:%s:%s" % (name, version)
                )

    def test_supported_news_sources_can_be_checked_offline(self):
        sources = ["hacker_news", "google_trends", "tiktok", "youtube"]

        # Doctor validates source names without collecting or checking live keys.
        for source in sources:
            with self.subTest(source=source):
                config_text = 'sources = ["%s"]\ndatabase = "unused.db"\n' % source
                self.config.write_text(config_text, encoding="utf-8")
                args = self.preflight_args()
                result = self.run_cli(*args)

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                document = json.loads(result.stdout)
                configuration = document["configuration"]

                self.assertEqual(configuration["status"], "ok")
                self.assertEqual(configuration["enabled_sources"], [source])
                self.assertFalse(configuration["youtube_key_present"])
                self.assertFalse(document["network_checked"])
                self.assertEqual(document["errors"], [])

        files = list(self.directory.iterdir())
        self.assertCountEqual(files, [self.config, self.env_file])

    def test_skill_preflight_example_matches_compatibility_manifest(self):
        path = SKILL / "SKILL.md"
        content = path.read_text(encoding="utf-8")

        # Find the documented doctor command without executing any Markdown text.
        blocks = re.findall(r"```bash\n(.*?)\n```", content, re.DOTALL)
        preflights = []

        for block in blocks:
            words = shlex.split(block)
            if words[:2] == ["trend-engine", "doctor"]:
                preflights.append(words)

        self.assertEqual(len(preflights), 1)

        # Substitute only our trusted temporary config path, not shell variables.
        actual = []

        for word in preflights[0][1:]:
            if word == "$TREND_ENGINE_CONFIG":
                word = str(self.config)

            actual.append(word)

        expected = self.preflight_args()

        self.assertEqual(actual, expected)
        result = self.run_cli(*actual)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_skill_metadata_requires_only_the_installed_binary(self):
        path = SKILL / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        sections = content.split("---", 2)
        frontmatter = sections[1]

        # The skill's metadata fields are single-line values, not arbitrary YAML.
        fields = {}
        lines = frontmatter.splitlines()

        for line in lines:
            if ":" not in line:
                continue

            name, value = line.split(":", 1)
            fields[name] = value

        self.assertEqual(fields["name"].strip(), SKILL.name)
        metadata = json.loads(fields["metadata"])

        self.assertEqual(metadata["openclaw"]["requires"], {"bins": ["trend-engine"]})

    def test_incompatible_version_and_contract_fail_closed(self):
        for flag, value, code in (
            ("--min-version", "999.0.0", "version_too_old"),
            ("--max-version", "0.0.0", "version_too_new"),
            ("--require-report-schema", "999", "report_schema_mismatch"),
            ("--require-doctor-schema", "999", "doctor_schema_mismatch"),
        ):
            with self.subTest(flag=flag):
                result = self.run_cli("doctor", "--json", flag, value)

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                document = json.loads(result.stdout)

                self.assertEqual(document["status"], "error")
                self.assertIn(code, document["errors"])

    def test_empty_report_is_read_only_and_json_on_exit_one(self):
        result = self.run_cli("report", "--config", str(self.config), "--json")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)

        self.assertEqual(report["schema_version"], COMPATIBILITY["contracts"]["report"])
        self.assertIsNone(report["collected_at"])
        self.assertTrue(report["stale"])
        self.assertEqual(report["source_health"], [])
        self.assertEqual(report["global_trends"], [])
        self.assertEqual(report["regional_trends"], {"north_america": [], "asia": []})
        self.assertEqual(report["platform_trends"], {})
        self.assertIn("No stored snapshot", result.stderr)
        files = list(self.directory.iterdir())

        self.assertCountEqual(files, [self.config, self.env_file])

    def test_config_error_is_local_and_redacted(self):
        self.config.write_text("test-private-setting = true", encoding="utf-8")
        result = self.run_cli("doctor", "--json", "--config", str(self.config))

        self.assertEqual(result.returncode, 2)
        document = json.loads(result.stdout)

        self.assertIn("configuration_invalid", document["errors"])
        self.assertNotIn("test-private-setting", result.stdout + result.stderr)
        files = list(self.directory.iterdir())

        self.assertCountEqual(files, [self.config, self.env_file])

    def test_explicit_env_file_loads_without_revealing_keys(self):
        self.env_file.write_text(
            "YOUTUBE_API_KEY=test-private-file\n", encoding="utf-8"
        )
        result = self.run_cli("doctor", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        configuration = document["configuration"]

        self.assertTrue(configuration["youtube_key_present"])
        self.assertFalse(document["network_checked"])
        self.assertNotIn("test-private", result.stdout + result.stderr)

        # Even an explicitly empty process variable takes precedence over the file.
        self.environment["YOUTUBE_API_KEY"] = ""
        result = self.run_cli("doctor", "--json")
        document = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(document["configuration"]["youtube_key_present"])

    def test_invalid_env_is_redacted_but_does_not_block_stored_reports(self):
        self.env_file.write_text('YOUTUBE_API_KEY="test-private\n', encoding="utf-8")
        result = self.run_cli("doctor", "--json", "--config", str(self.config))

        self.assertEqual(result.returncode, 2)
        document = json.loads(result.stdout)

        self.assertIn("environment_invalid", document["errors"])
        self.assertNotIn("test-private", result.stdout + result.stderr)
        self.assertNotIn(str(self.env_file), result.stdout + result.stderr)

        result = self.run_cli("report", "--json", "--config", str(self.config))
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIsNone(report["collected_at"])

    def test_presence_checks_ignore_unselected_dotenv_and_never_reveal_keys(self):
        dotenv_path = self.directory / ".env"
        dotenv_path.write_text("YOUTUBE_API_KEY=test-dotenv\n", encoding="utf-8")
        result = self.run_cli("doctor", "--json")

        self.assertEqual(result.returncode, 0)
        document = json.loads(result.stdout)
        config = document["configuration"]

        self.assertEqual(config["status"], "not_checked")
        self.assertFalse(config["youtube_key_present"])

        # Inject a dummy YouTube key; doctor must report presence, never its value.
        self.environment["YOUTUBE_API_KEY"] = "test-private-youtube"
        result = self.run_cli("doctor", "--json")

        self.assertEqual(result.returncode, 0)
        document = json.loads(result.stdout)
        config = document["configuration"]

        self.assertTrue(config["youtube_key_present"])
        self.assertEqual(config["enabled_sources"], [])
        self.assertFalse(document["network_checked"])
        self.assertNotIn("test-private", result.stdout + result.stderr)

    def test_documented_commands_exist_without_collecting(self):
        for command in ("report", "run", "doctor", "schema"):
            result = self.run_cli(command, "--help")

            self.assertEqual(result.returncode, 0, result.stderr)

        files = list(self.directory.iterdir())

        self.assertCountEqual(files, [self.config, self.env_file])


if __name__ == "__main__":
    unittest.main()
