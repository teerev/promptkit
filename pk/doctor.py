"""
Doctor tooling for template validation.

Validates:
- Schema JSON validity
- Preset validation against schemas
- Template rendering with presets
- Variable coverage (no undeclared variables)
- Golden test comparison
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from jsonschema import Draft7Validator

from pk.render import (
    TemplateError,
    get_schema_variables,
    get_template_dir,
    get_template_variables,
    get_templates_dir,
    list_presets,
    list_templates,
    load_preset,
    load_schema,
    load_template,
    merge_params,
    render,
    validate_params,
)


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    template: str
    check: str
    passed: bool
    message: str
    details: list[str] = field(default_factory=list)


@dataclass
class DoctorReport:
    """Complete doctor validation report."""

    results: list[ValidationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Whether all checks passed."""
        return all(r.passed for r in self.results)

    @property
    def failed_count(self) -> int:
        """Number of failed checks."""
        return sum(1 for r in self.results if not r.passed)

    @property
    def passed_count(self) -> int:
        """Number of passed checks."""
        return sum(1 for r in self.results if r.passed)

    def add(self, result: ValidationResult) -> None:
        """Add a validation result."""
        self.results.append(result)

    def format_report(self) -> str:
        """Format the report as a human-readable string."""
        lines = []
        lines.append("=" * 60)
        lines.append("PROMPTKIT DOCTOR REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Group by template
        by_template: dict[str, list[ValidationResult]] = {}
        for result in self.results:
            if result.template not in by_template:
                by_template[result.template] = []
            by_template[result.template].append(result)

        for template, results in sorted(by_template.items()):
            lines.append(f"Template: {template}")
            lines.append("-" * 40)

            for result in results:
                status = "✓" if result.passed else "✗"
                lines.append(f"  {status} {result.check}: {result.message}")
                for detail in result.details:
                    lines.append(f"      {detail}")

            lines.append("")

        # Summary
        lines.append("=" * 60)
        lines.append(f"SUMMARY: {self.passed_count} passed, {self.failed_count} failed")
        if self.passed:
            lines.append("All checks passed!")
        else:
            lines.append("Some checks failed. Please fix the issues above.")
        lines.append("=" * 60)

        return "\n".join(lines)


def validate_schema_json(template_name: str) -> ValidationResult:
    """Validate that schema.json is valid JSON and valid JSON Schema."""
    template_dir = get_template_dir(template_name)
    schema_file = template_dir / "schema.json"

    if not schema_file.exists():
        return ValidationResult(
            template=template_name,
            check="schema_json",
            passed=False,
            message="schema.json not found",
        )

    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ValidationResult(
            template=template_name,
            check="schema_json",
            passed=False,
            message=f"Invalid JSON: {e}",
        )

    # Validate it's a valid JSON Schema
    try:
        Draft7Validator.check_schema(schema)
    except Exception as e:
        return ValidationResult(
            template=template_name,
            check="schema_json",
            passed=False,
            message=f"Invalid JSON Schema: {e}",
        )

    return ValidationResult(
        template=template_name,
        check="schema_json",
        passed=True,
        message="Valid JSON Schema",
    )


def validate_presets(template_name: str) -> list[ValidationResult]:
    """Validate that all presets conform to the schema."""
    results = []

    try:
        schema = load_schema(template_name)
    except TemplateError as e:
        return [ValidationResult(
            template=template_name,
            check="presets",
            passed=False,
            message=f"Could not load schema: {e}",
        )]

    presets = list_presets(template_name)
    if not presets:
        return [ValidationResult(
            template=template_name,
            check="presets",
            passed=True,
            message="No presets to validate",
        )]

    for preset_name in presets:
        try:
            preset_params = load_preset(template_name, preset_name)
            merged = merge_params(schema, preset_params=preset_params)
            validate_params(schema, merged)
            results.append(ValidationResult(
                template=template_name,
                check=f"preset:{preset_name}",
                passed=True,
                message="Valid",
            ))
        except TemplateError as e:
            results.append(ValidationResult(
                template=template_name,
                check=f"preset:{preset_name}",
                passed=False,
                message=str(e),
            ))

    return results


def validate_template_renders(template_name: str) -> list[ValidationResult]:
    """Validate that template renders with each preset."""
    results = []

    try:
        template_text = load_template(template_name)
        schema = load_schema(template_name)
    except TemplateError as e:
        return [ValidationResult(
            template=template_name,
            check="render",
            passed=False,
            message=f"Could not load template/schema: {e}",
        )]

    presets = list_presets(template_name)
    if not presets:
        # Try with just defaults
        try:
            merged = merge_params(schema)
            validate_params(schema, merged)
            render(template_text, merged)
            results.append(ValidationResult(
                template=template_name,
                check="render:defaults",
                passed=True,
                message="Renders with defaults only",
            ))
        except TemplateError as e:
            results.append(ValidationResult(
                template=template_name,
                check="render:defaults",
                passed=False,
                message=str(e),
            ))
        return results

    for preset_name in presets:
        try:
            preset_params = load_preset(template_name, preset_name)
            merged = merge_params(schema, preset_params=preset_params)
            validate_params(schema, merged)
            render(template_text, merged)
            results.append(ValidationResult(
                template=template_name,
                check=f"render:{preset_name}",
                passed=True,
                message="Renders successfully",
            ))
        except TemplateError as e:
            results.append(ValidationResult(
                template=template_name,
                check=f"render:{preset_name}",
                passed=False,
                message=str(e),
            ))

    return results


def validate_variable_coverage(template_name: str) -> ValidationResult:
    """
    Validate that all template variables are declared in the schema.

    This catches:
    - Typos in variable names
    - Variables used but not documented
    - Template-schema drift
    """
    try:
        template_text = load_template(template_name)
        schema = load_schema(template_name)
    except TemplateError as e:
        return ValidationResult(
            template=template_name,
            check="variable_coverage",
            passed=False,
            message=f"Could not load template/schema: {e}",
        )

    try:
        template_vars = get_template_variables(template_text)
    except TemplateError as e:
        return ValidationResult(
            template=template_name,
            check="variable_coverage",
            passed=False,
            message=f"Template parse error: {e}",
        )

    schema_vars = get_schema_variables(schema)

    # Find undeclared variables (in template but not in schema)
    undeclared = template_vars - schema_vars

    # Filter out Jinja2 built-ins
    jinja_builtins = {"loop", "self", "range", "dict", "lipsum", "cycler", "joiner"}
    undeclared = undeclared - jinja_builtins

    if undeclared:
        return ValidationResult(
            template=template_name,
            check="variable_coverage",
            passed=False,
            message=f"Undeclared variables in template: {', '.join(sorted(undeclared))}",
            details=[f"Add these to schema.json or fix typos: {sorted(undeclared)}"],
        )

    # Also report unused schema variables (warning, not failure)
    unused = schema_vars - template_vars
    details = []
    if unused:
        details.append(f"Schema variables not used in template: {sorted(unused)}")

    return ValidationResult(
        template=template_name,
        check="variable_coverage",
        passed=True,
        message="All template variables declared in schema",
        details=details,
    )


def normalize_text(text: str) -> str:
    """Normalize text for comparison (line endings, trailing whitespace)."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # Strip trailing whitespace from each line, but preserve blank lines
    lines = [line.rstrip() for line in lines]
    # Remove trailing blank lines
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def validate_golden_test(template_name: str) -> ValidationResult:
    """
    Validate that rendering with default preset matches golden file.

    Golden file location: templates/<name>/tests/render_golden.md
    """
    template_dir = get_template_dir(template_name)
    golden_file = template_dir / "tests" / "render_golden.md"

    if not golden_file.exists():
        return ValidationResult(
            template=template_name,
            check="golden_test",
            passed=False,
            message=f"Golden file not found: {golden_file}",
            details=["Create tests/render_golden.md with expected output"],
        )

    try:
        template_text = load_template(template_name)
        schema = load_schema(template_name)

        # Use default preset if available, otherwise just defaults
        presets = list_presets(template_name)
        if "default" in presets:
            preset_params = load_preset(template_name, "default")
            merged = merge_params(schema, preset_params=preset_params)
        else:
            merged = merge_params(schema)

        validate_params(schema, merged)
        rendered = render(template_text, merged)

    except TemplateError as e:
        return ValidationResult(
            template=template_name,
            check="golden_test",
            passed=False,
            message=f"Render failed: {e}",
        )

    expected = golden_file.read_text(encoding="utf-8")

    # Normalize both for comparison
    rendered_norm = normalize_text(rendered)
    expected_norm = normalize_text(expected)

    if rendered_norm == expected_norm:
        return ValidationResult(
            template=template_name,
            check="golden_test",
            passed=True,
            message="Golden test passed",
        )

    # Find first difference for debugging
    rendered_lines = rendered_norm.split("\n")
    expected_lines = expected_norm.split("\n")

    details = []
    for i, (r, e) in enumerate(zip(rendered_lines, expected_lines, strict=False)):
        if r != e:
            details.append(f"First difference at line {i + 1}:")
            details.append(f"  Expected: {e[:80]}{'...' if len(e) > 80 else ''}")
            details.append(f"  Got:      {r[:80]}{'...' if len(r) > 80 else ''}")
            break
    else:
        if len(rendered_lines) != len(expected_lines):
            details.append(
                f"Line count mismatch: expected {len(expected_lines)}, got {len(rendered_lines)}"
            )

    return ValidationResult(
        template=template_name,
        check="golden_test",
        passed=False,
        message="Golden test failed - output doesn't match expected",
        details=details,
    )


def validate_template(template_name: str) -> list[ValidationResult]:
    """Run all validations for a single template."""
    results = []

    # Schema validation
    results.append(validate_schema_json(template_name))

    # Preset validation
    results.extend(validate_presets(template_name))

    # Variable coverage
    results.append(validate_variable_coverage(template_name))

    # Render tests
    results.extend(validate_template_renders(template_name))

    # Golden test
    results.append(validate_golden_test(template_name))

    return results


def validate_all_templates() -> DoctorReport:
    """Run all validations for all templates."""
    report = DoctorReport()

    templates = list_templates()
    if not templates:
        report.add(ValidationResult(
            template="(none)",
            check="templates_exist",
            passed=False,
            message="No templates found",
            details=[f"Expected templates in: {get_templates_dir()}"],
        ))
        return report

    for template_info in templates:
        template_name = template_info["name"]
        results = validate_template(template_name)
        for result in results:
            report.add(result)

    return report
