"""Tests for the doctor module."""


from pk.doctor import (
    DoctorReport,
    ValidationResult,
    normalize_text,
    validate_all_templates,
    validate_golden_test,
    validate_presets,
    validate_schema_json,
    validate_template,
    validate_template_renders,
    validate_variable_coverage,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_creates_passed_result(self):
        """Should create a passed result."""
        result = ValidationResult(
            template="test",
            check="test_check",
            passed=True,
            message="All good",
        )
        assert result.passed is True
        assert result.template == "test"

    def test_creates_failed_result_with_details(self):
        """Should create a failed result with details."""
        result = ValidationResult(
            template="test",
            check="test_check",
            passed=False,
            message="Failed",
            details=["Detail 1", "Detail 2"],
        )
        assert result.passed is False
        assert len(result.details) == 2


class TestDoctorReport:
    """Tests for DoctorReport dataclass."""

    def test_empty_report_passes(self):
        """Empty report should pass by default."""
        report = DoctorReport()
        assert report.passed is True
        assert report.passed_count == 0
        assert report.failed_count == 0

    def test_all_passed(self):
        """Report with all passed should pass."""
        report = DoctorReport()
        report.add(ValidationResult("t1", "c1", True, "ok"))
        report.add(ValidationResult("t1", "c2", True, "ok"))
        assert report.passed is True
        assert report.passed_count == 2
        assert report.failed_count == 0

    def test_any_failed(self):
        """Report with any failed should fail."""
        report = DoctorReport()
        report.add(ValidationResult("t1", "c1", True, "ok"))
        report.add(ValidationResult("t1", "c2", False, "fail"))
        assert report.passed is False
        assert report.passed_count == 1
        assert report.failed_count == 1

    def test_format_report(self):
        """Should format report as string."""
        report = DoctorReport()
        report.add(ValidationResult("test", "check", True, "passed"))
        formatted = report.format_report()
        assert "PROMPTKIT DOCTOR REPORT" in formatted
        assert "test" in formatted


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_normalizes_line_endings(self):
        """Should normalize different line endings."""
        text1 = "line1\r\nline2\r\n"
        text2 = "line1\nline2\n"
        text3 = "line1\rline2\r"

        assert normalize_text(text1) == normalize_text(text2)
        assert normalize_text(text2) == normalize_text(text3)

    def test_strips_trailing_whitespace(self):
        """Should strip trailing whitespace from lines."""
        text = "line1   \nline2  \n"
        normalized = normalize_text(text)
        assert "   " not in normalized

    def test_removes_trailing_blank_lines(self):
        """Should remove trailing blank lines."""
        text = "content\n\n\n"
        normalized = normalize_text(text)
        assert not normalized.endswith("\n\n")


class TestValidateSchemaJson:
    """Tests for validate_schema_json function."""

    def test_valid_schema_passes(self):
        """Valid schema should pass."""
        result = validate_schema_json("audit")
        assert result.passed is True

    def test_all_templates_have_valid_schemas(self):
        """All templates should have valid schemas."""
        from pk.render import list_templates

        for template_info in list_templates():
            result = validate_schema_json(template_info["name"])
            assert result.passed is True, f"Schema failed for {template_info['name']}: {result.message}"


class TestValidatePresets:
    """Tests for validate_presets function."""

    def test_valid_presets_pass(self):
        """Valid presets should pass."""
        results = validate_presets("audit")
        for result in results:
            assert result.passed is True, f"Preset failed: {result.message}"

    def test_all_templates_have_valid_presets(self):
        """All templates should have valid presets."""
        from pk.render import list_templates

        for template_info in list_templates():
            results = validate_presets(template_info["name"])
            for result in results:
                assert result.passed is True, f"Preset failed for {template_info['name']}: {result.message}"


class TestValidateVariableCoverage:
    """Tests for validate_variable_coverage function."""

    def test_covered_variables_pass(self):
        """Templates with all variables in schema should pass."""
        result = validate_variable_coverage("audit")
        assert result.passed is True, f"Variable coverage failed: {result.message}"

    def test_all_templates_have_covered_variables(self):
        """All templates should have covered variables."""
        from pk.render import list_templates

        for template_info in list_templates():
            result = validate_variable_coverage(template_info["name"])
            assert result.passed is True, f"Variable coverage failed for {template_info['name']}: {result.message}"


class TestValidateTemplateRenders:
    """Tests for validate_template_renders function."""

    def test_templates_render_successfully(self):
        """Templates should render with their presets."""
        results = validate_template_renders("audit")
        for result in results:
            assert result.passed is True, f"Render failed: {result.message}"


class TestValidateGoldenTest:
    """Tests for validate_golden_test function."""

    def test_golden_test_passes(self):
        """Golden tests should pass for valid templates."""
        result = validate_golden_test("audit")
        assert result.passed is True, f"Golden test failed: {result.message}\n{result.details}"

    def test_all_templates_pass_golden_test(self):
        """All templates should pass their golden tests."""
        from pk.render import list_templates

        for template_info in list_templates():
            result = validate_golden_test(template_info["name"])
            assert result.passed is True, f"Golden test failed for {template_info['name']}: {result.message}\n{result.details}"


class TestValidateTemplate:
    """Tests for validate_template function."""

    def test_validates_all_aspects(self):
        """Should validate all aspects of a template."""
        results = validate_template("audit")

        # Should have multiple results
        assert len(results) > 0

        # Check we have different types of checks
        checks = {r.check for r in results}
        assert "schema_json" in checks
        assert "variable_coverage" in checks
        assert "golden_test" in checks


class TestValidateAllTemplates:
    """Tests for validate_all_templates function."""

    def test_validates_all_templates(self):
        """Should validate all templates."""
        report = validate_all_templates()

        # Should have results for multiple templates
        templates = {r.template for r in report.results}
        assert len(templates) >= 3  # At least audit, security, readme

        # All should pass
        assert report.passed is True, report.format_report()

    def test_report_includes_all_template_types(self):
        """Report should include all template types."""
        report = validate_all_templates()
        templates = {r.template for r in report.results}

        expected = {"audit", "security", "readme"}
        assert expected.issubset(templates)
