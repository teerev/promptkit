"""Tests for the CLI module."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from pk.cli import main


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestListCommand:
    """Tests for the list command."""

    def test_lists_templates(self, runner):
        """Should list available templates."""
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "audit" in result.output
        assert "security" in result.output
        assert "readme" in result.output

    def test_shows_descriptions(self, runner):
        """Should show template descriptions."""
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        # Check for some description text
        assert "Template" in result.output
        assert "Description" in result.output


class TestShowCommand:
    """Tests for the show command."""

    def test_shows_template_details(self, runner):
        """Should show template details."""
        result = runner.invoke(main, ["show", "audit"])
        assert result.exit_code == 0
        assert "Template: audit" in result.output
        assert "Schema:" in result.output
        assert "Parameters:" in result.output

    def test_shows_presets(self, runner):
        """Should show available presets."""
        result = runner.invoke(main, ["show", "audit"])
        assert result.exit_code == 0
        assert "Presets:" in result.output or "default" in result.output

    def test_fails_for_missing_template(self, runner):
        """Should fail for missing template."""
        result = runner.invoke(main, ["show", "nonexistent_xyz"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestPresetsCommand:
    """Tests for the presets command."""

    def test_lists_presets(self, runner):
        """Should list presets for a template."""
        result = runner.invoke(main, ["presets", "audit"])
        assert result.exit_code == 0
        assert "default" in result.output

    def test_fails_for_missing_template(self, runner):
        """Should fail for missing template."""
        result = runner.invoke(main, ["presets", "nonexistent_xyz"])
        assert result.exit_code != 0


class TestRenderCommand:
    """Tests for the render command."""

    def test_renders_template_with_preset(self, runner):
        """Should render template with preset."""
        result = runner.invoke(main, ["render", "audit", "--preset", "default"])
        assert result.exit_code == 0
        assert "Role & Mission" in result.output

    def test_renders_template_with_defaults(self, runner):
        """Should render template with schema defaults."""
        result = runner.invoke(main, ["render", "audit"])
        assert result.exit_code == 0
        assert "Role & Mission" in result.output

    def test_applies_cli_overrides(self, runner):
        """Should apply CLI overrides."""
        result = runner.invoke(main, [
            "render", "audit",
            "--set", "time_budget_minutes=120",
        ])
        assert result.exit_code == 0
        assert "120" in result.output

    def test_writes_to_output_file(self, runner):
        """Should write output to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            outfile = Path(tmpdir) / "output.md"
            result = runner.invoke(main, [
                "render", "audit",
                "--preset", "default",
                "--out", str(outfile),
            ])
            assert result.exit_code == 0
            assert outfile.exists()
            content = outfile.read_text()
            assert "Role & Mission" in content

    def test_creates_run_packet(self, runner):
        """Should create run packet directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(main, [
                "render", "audit",
                "--preset", "default",
                "--run-dir", tmpdir,
            ])
            assert result.exit_code == 0
            
            # Check run packet was created
            run_dirs = list(Path(tmpdir).iterdir())
            assert len(run_dirs) == 1
            
            packet_dir = run_dirs[0]
            assert (packet_dir / "prompt.md").exists()
            assert (packet_dir / "params.resolved.json").exists()
            assert (packet_dir / "meta.json").exists()

    def test_fails_for_missing_template(self, runner):
        """Should fail for missing template."""
        result = runner.invoke(main, ["render", "nonexistent_xyz"])
        assert result.exit_code != 0

    def test_fails_for_missing_preset(self, runner):
        """Should fail for missing preset."""
        result = runner.invoke(main, [
            "render", "audit",
            "--preset", "nonexistent_preset_xyz",
        ])
        assert result.exit_code != 0

    def test_format_flag_overrides_output_format(self, runner):
        """--format flag should override output_format param."""
        result = runner.invoke(main, [
            "render", "audit",
            "--format", "json",
        ])
        assert result.exit_code == 0
        # JSON format should produce different output
        assert "json" in result.output.lower()


class TestDoctorCommand:
    """Tests for the doctor command."""

    def test_runs_doctor(self, runner):
        """Should run doctor checks."""
        result = runner.invoke(main, ["doctor"])
        assert "PROMPTKIT DOCTOR REPORT" in result.output

    def test_all_checks_pass(self, runner):
        """All doctor checks should pass."""
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "All checks passed" in result.output

    def test_validates_single_template(self, runner):
        """Should validate a single template with --template flag."""
        result = runner.invoke(main, ["doctor", "--template", "audit"])
        assert result.exit_code == 0
        assert "audit" in result.output

    def test_fails_for_missing_template(self, runner):
        """Should fail for missing template."""
        result = runner.invoke(main, ["doctor", "--template", "nonexistent_xyz"])
        assert result.exit_code != 0


class TestVersionFlag:
    """Tests for the --version flag."""

    def test_shows_version(self, runner):
        """Should show version."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestHelpFlag:
    """Tests for the --help flag."""

    def test_shows_help(self, runner):
        """Should show help."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "pk" in result.output.lower()
        assert "list" in result.output
        assert "render" in result.output
        assert "doctor" in result.output

    def test_command_help(self, runner):
        """Should show command-specific help."""
        result = runner.invoke(main, ["render", "--help"])
        assert result.exit_code == 0
        assert "--preset" in result.output
        assert "--params" in result.output
        assert "--set" in result.output
