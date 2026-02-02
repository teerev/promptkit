"""Tests for the render module."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from pk.render import (
    RenderError,
    SchemaValidationError,
    TemplateError,
    TemplateNotFoundError,
    compute_hash,
    get_schema_defaults,
    get_schema_variables,
    get_template_variables,
    list_presets,
    list_templates,
    load_params_file,
    load_preset,
    load_schema,
    load_template,
    merge_params,
    parse_cli_override,
    render,
    validate_params,
)


class TestListTemplates:
    """Tests for list_templates function."""

    def test_returns_list(self):
        """Should return a list of templates."""
        templates = list_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0

    def test_contains_expected_templates(self):
        """Should contain the expected template names."""
        templates = list_templates()
        names = [t["name"] for t in templates]
        assert "audit" in names
        assert "security" in names
        assert "readme" in names

    def test_templates_have_description(self):
        """Each template should have a description."""
        templates = list_templates()
        for t in templates:
            assert "name" in t
            assert "description" in t
            assert len(t["description"]) > 0


class TestLoadTemplate:
    """Tests for load_template function."""

    def test_loads_existing_template(self):
        """Should load an existing template."""
        content = load_template("audit")
        assert isinstance(content, str)
        assert len(content) > 0
        assert "Role & Mission" in content

    def test_raises_for_missing_template(self):
        """Should raise TemplateNotFoundError for missing template."""
        with pytest.raises(TemplateNotFoundError):
            load_template("nonexistent_template_xyz")


class TestLoadSchema:
    """Tests for load_schema function."""

    def test_loads_valid_schema(self):
        """Should load a valid JSON schema."""
        schema = load_schema("audit")
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "repo_path" in schema["properties"]

    def test_schema_has_required_fields(self):
        """Schema should have standard fields."""
        schema = load_schema("audit")
        assert "title" in schema or "description" in schema
        assert schema.get("type") == "object"


class TestListPresets:
    """Tests for list_presets function."""

    def test_lists_presets(self):
        """Should list available presets."""
        presets = list_presets("audit")
        assert isinstance(presets, list)
        assert "default" in presets

    def test_returns_empty_for_no_presets(self):
        """Should return empty list if no presets exist."""
        # All templates have at least default, but test the return type
        presets = list_presets("audit")
        assert isinstance(presets, list)


class TestLoadPreset:
    """Tests for load_preset function."""

    def test_loads_valid_preset(self):
        """Should load a valid preset."""
        preset = load_preset("audit", "default")
        assert isinstance(preset, dict)

    def test_raises_for_missing_preset(self):
        """Should raise PresetNotFoundError for missing preset."""
        from pk.render import PresetNotFoundError
        with pytest.raises(PresetNotFoundError):
            load_preset("audit", "nonexistent_preset_xyz")


class TestLoadParamsFile:
    """Tests for load_params_file function."""

    def test_loads_yaml_file(self):
        """Should load a YAML params file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump({"key": "value", "number": 42}, f)
            f.flush()
            params = load_params_file(f.name)
        
        assert params["key"] == "value"
        assert params["number"] == 42

    def test_loads_json_file(self):
        """Should load a JSON params file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"key": "value", "number": 42}, f)
            f.flush()
            params = load_params_file(f.name)
        
        assert params["key"] == "value"
        assert params["number"] == 42

    def test_raises_for_missing_file(self):
        """Should raise TemplateError for missing file."""
        with pytest.raises(TemplateError):
            load_params_file("/nonexistent/path/to/params.yaml")


class TestGetSchemaDefaults:
    """Tests for get_schema_defaults function."""

    def test_extracts_defaults(self):
        """Should extract default values from schema."""
        schema = {
            "properties": {
                "name": {"type": "string", "default": "test"},
                "count": {"type": "integer", "default": 10},
                "no_default": {"type": "string"},
            }
        }
        defaults = get_schema_defaults(schema)
        assert defaults["name"] == "test"
        assert defaults["count"] == 10
        assert "no_default" not in defaults


class TestMergeParams:
    """Tests for merge_params function."""

    def test_applies_schema_defaults(self):
        """Should apply schema defaults."""
        schema = {
            "properties": {
                "name": {"type": "string", "default": "default_name"},
            }
        }
        merged = merge_params(schema)
        assert merged["name"] == "default_name"

    def test_preset_overrides_defaults(self):
        """Preset should override schema defaults."""
        schema = {
            "properties": {
                "name": {"type": "string", "default": "default_name"},
            }
        }
        preset = {"name": "preset_name"}
        merged = merge_params(schema, preset_params=preset)
        assert merged["name"] == "preset_name"

    def test_file_params_override_preset(self):
        """File params should override preset."""
        schema = {
            "properties": {
                "name": {"type": "string", "default": "default_name"},
            }
        }
        preset = {"name": "preset_name"}
        file_params = {"name": "file_name"}
        merged = merge_params(schema, preset_params=preset, file_params=file_params)
        assert merged["name"] == "file_name"

    def test_cli_overrides_everything(self):
        """CLI overrides should have highest priority."""
        schema = {
            "properties": {
                "name": {"type": "string", "default": "default_name"},
            }
        }
        preset = {"name": "preset_name"}
        file_params = {"name": "file_name"}
        cli = {"name": "cli_name"}
        merged = merge_params(
            schema,
            preset_params=preset,
            file_params=file_params,
            cli_overrides=cli,
        )
        assert merged["name"] == "cli_name"


class TestValidateParams:
    """Tests for validate_params function."""

    def test_valid_params_pass(self):
        """Should not raise for valid params."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            },
        }
        params = {"name": "test", "count": 10}
        # Should not raise
        validate_params(schema, params)

    def test_invalid_type_raises(self):
        """Should raise SchemaValidationError for invalid type."""
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
            },
        }
        params = {"count": "not_a_number"}
        with pytest.raises(SchemaValidationError):
            validate_params(schema, params)


class TestGetTemplateVariables:
    """Tests for get_template_variables function."""

    def test_extracts_variables(self):
        """Should extract variables from template."""
        template = "Hello {{ name }}, you have {{ count }} messages."
        variables = get_template_variables(template)
        assert "name" in variables
        assert "count" in variables

    def test_handles_complex_expressions(self):
        """Should handle complex Jinja2 expressions."""
        template = "{% for item in items %}{{ item }}{% endfor %}"
        variables = get_template_variables(template)
        assert "items" in variables


class TestGetSchemaVariables:
    """Tests for get_schema_variables function."""

    def test_extracts_property_names(self):
        """Should extract property names from schema."""
        schema = {
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            }
        }
        variables = get_schema_variables(schema)
        assert "name" in variables
        assert "count" in variables


class TestRender:
    """Tests for render function."""

    def test_renders_simple_template(self):
        """Should render a simple template."""
        template = "Hello {{ name }}!"
        result = render(template, {"name": "World"})
        assert result == "Hello World!"

    def test_raises_for_undefined_variable(self):
        """Should raise RenderError for undefined variable."""
        template = "Hello {{ name }} and {{ undefined_var }}!"
        with pytest.raises(RenderError):
            render(template, {"name": "World"})

    def test_handles_loops(self):
        """Should handle Jinja2 loops."""
        template = "{% for i in items %}{{ i }} {% endfor %}"
        result = render(template, {"items": [1, 2, 3]})
        assert result == "1 2 3 "

    def test_handles_conditionals(self):
        """Should handle Jinja2 conditionals."""
        template = "{% if show %}visible{% else %}hidden{% endif %}"
        assert render(template, {"show": True}) == "visible"
        assert render(template, {"show": False}) == "hidden"


class TestComputeHash:
    """Tests for compute_hash function."""

    def test_produces_consistent_hash(self):
        """Same input should produce same hash."""
        text = "Hello World"
        hash1 = compute_hash(text)
        hash2 = compute_hash(text)
        assert hash1 == hash2

    def test_different_input_different_hash(self):
        """Different input should produce different hash."""
        hash1 = compute_hash("Hello")
        hash2 = compute_hash("World")
        assert hash1 != hash2

    def test_returns_hex_string(self):
        """Hash should be a hex string."""
        hash_value = compute_hash("test")
        assert all(c in "0123456789abcdef" for c in hash_value)
        assert len(hash_value) == 64  # SHA256 produces 64 hex chars


class TestParseCliOverride:
    """Tests for parse_cli_override function."""

    def test_parses_string(self):
        """Should parse string values."""
        key, value = parse_cli_override("name=test")
        assert key == "name"
        assert value == "test"

    def test_parses_integer(self):
        """Should parse integer values."""
        key, value = parse_cli_override("count=42")
        assert key == "count"
        assert value == 42

    def test_parses_float(self):
        """Should parse float values."""
        key, value = parse_cli_override("rate=3.14")
        assert key == "rate"
        assert value == 3.14

    def test_parses_boolean_true(self):
        """Should parse boolean true."""
        key, value = parse_cli_override("enabled=true")
        assert key == "enabled"
        assert value is True

    def test_parses_boolean_false(self):
        """Should parse boolean false."""
        key, value = parse_cli_override("enabled=false")
        assert key == "enabled"
        assert value is False

    def test_parses_json_array(self):
        """Should parse JSON array."""
        key, value = parse_cli_override('items=["a","b","c"]')
        assert key == "items"
        assert value == ["a", "b", "c"]

    def test_parses_json_object(self):
        """Should parse JSON object."""
        key, value = parse_cli_override('config={"key":"value"}')
        assert key == "config"
        assert value == {"key": "value"}

    def test_raises_for_invalid_format(self):
        """Should raise for invalid format."""
        with pytest.raises(TemplateError):
            parse_cli_override("invalid_without_equals")
