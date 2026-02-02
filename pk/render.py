"""
Core rendering engine for prompt templates.

Provides:
- Template and schema loading
- Parameter validation and merging
- Strict Jinja2 rendering (fail on undefined)
- Run packet emission for reproducibility
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError, meta
from jsonschema import Draft7Validator, ValidationError


class TemplateError(Exception):
    """Base exception for template-related errors."""


class TemplateNotFoundError(TemplateError):
    """Raised when a template cannot be found."""


class PresetNotFoundError(TemplateError):
    """Raised when a preset cannot be found."""


class SchemaValidationError(TemplateError):
    """Raised when parameters fail schema validation."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


class RenderError(TemplateError):
    """Raised when template rendering fails."""


def get_templates_dir() -> Path:
    """Get the path to the templates directory."""
    # Templates are bundled with the package
    pkg_dir = Path(__file__).parent.parent
    return pkg_dir / "templates"


def list_templates() -> list[dict[str, str]]:
    """
    List all available templates with their names and descriptions.
    
    Returns:
        List of dicts with 'name' and 'description' keys.
    """
    templates_dir = get_templates_dir()
    if not templates_dir.exists():
        return []
    
    templates = []
    for item in sorted(templates_dir.iterdir()):
        if item.is_dir() and (item / "template.md").exists():
            schema = load_schema(item.name)
            description = schema.get("description", schema.get("title", "No description"))
            templates.append({
                "name": item.name,
                "description": description,
            })
    return templates


def get_template_dir(template_name: str) -> Path:
    """
    Get the directory for a specific template.
    
    Args:
        template_name: Name of the template.
        
    Returns:
        Path to the template directory.
        
    Raises:
        TemplateNotFoundError: If template doesn't exist.
    """
    template_dir = get_templates_dir() / template_name
    if not template_dir.exists() or not template_dir.is_dir():
        available = [t["name"] for t in list_templates()]
        raise TemplateNotFoundError(
            f"Template '{template_name}' not found. "
            f"Available templates: {', '.join(available) if available else 'none'}"
        )
    return template_dir


def load_template(template_name: str) -> str:
    """
    Load the template.md content for a template.
    
    Args:
        template_name: Name of the template.
        
    Returns:
        Template content as string.
        
    Raises:
        TemplateNotFoundError: If template file doesn't exist.
    """
    template_dir = get_template_dir(template_name)
    template_file = template_dir / "template.md"
    
    if not template_file.exists():
        raise TemplateNotFoundError(
            f"Template file not found: {template_file}"
        )
    
    return template_file.read_text(encoding="utf-8")


def load_schema(template_name: str) -> dict[str, Any]:
    """
    Load the schema.json for a template.
    
    Args:
        template_name: Name of the template.
        
    Returns:
        Schema as dict.
        
    Raises:
        TemplateNotFoundError: If schema file doesn't exist.
        TemplateError: If schema is invalid JSON.
    """
    template_dir = get_template_dir(template_name)
    schema_file = template_dir / "schema.json"
    
    if not schema_file.exists():
        raise TemplateNotFoundError(
            f"Schema file not found: {schema_file}"
        )
    
    try:
        return json.loads(schema_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise TemplateError(f"Invalid JSON in schema {schema_file}: {e}") from e


def list_presets(template_name: str) -> list[str]:
    """
    List available preset names for a template.
    
    Args:
        template_name: Name of the template.
        
    Returns:
        List of preset names (without extension).
    """
    template_dir = get_template_dir(template_name)
    examples_dir = template_dir / "examples"
    
    if not examples_dir.exists():
        return []
    
    presets = []
    for item in sorted(examples_dir.iterdir()):
        if item.is_file() and item.suffix in (".yaml", ".yml"):
            presets.append(item.stem)
    return presets


def load_preset(template_name: str, preset_name: str) -> dict[str, Any]:
    """
    Load a preset YAML file for a template.
    
    Args:
        template_name: Name of the template.
        preset_name: Name of the preset (without extension).
        
    Returns:
        Preset parameters as dict.
        
    Raises:
        PresetNotFoundError: If preset file doesn't exist.
        TemplateError: If preset is invalid YAML.
    """
    template_dir = get_template_dir(template_name)
    examples_dir = template_dir / "examples"
    
    # Try .yaml first, then .yml
    for ext in (".yaml", ".yml"):
        preset_file = examples_dir / f"{preset_name}{ext}"
        if preset_file.exists():
            try:
                content = yaml.safe_load(preset_file.read_text(encoding="utf-8"))
                return content if content else {}
            except yaml.YAMLError as e:
                raise TemplateError(f"Invalid YAML in preset {preset_file}: {e}") from e
    
    available = list_presets(template_name)
    raise PresetNotFoundError(
        f"Preset '{preset_name}' not found for template '{template_name}'. "
        f"Available presets: {', '.join(available) if available else 'none'}"
    )


def load_params_file(path: str | Path) -> dict[str, Any]:
    """
    Load parameters from a YAML or JSON file.
    
    Args:
        path: Path to the params file.
        
    Returns:
        Parameters as dict.
        
    Raises:
        TemplateError: If file doesn't exist or is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise TemplateError(f"Params file not found: {path}")
    
    content = path.read_text(encoding="utf-8")
    
    if path.suffix == ".json":
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise TemplateError(f"Invalid JSON in params file {path}: {e}") from e
    else:
        # Assume YAML for .yaml, .yml, or anything else
        try:
            result = yaml.safe_load(content)
            return result if result else {}
        except yaml.YAMLError as e:
            raise TemplateError(f"Invalid YAML in params file {path}: {e}") from e


def get_schema_defaults(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Extract default values from a JSON schema.
    
    Args:
        schema: JSON schema dict.
        
    Returns:
        Dict of parameter names to their default values.
    """
    defaults = {}
    properties = schema.get("properties", {})
    
    for prop_name, prop_schema in properties.items():
        if "default" in prop_schema:
            defaults[prop_name] = prop_schema["default"]
    
    return defaults


def merge_params(
    schema: dict[str, Any],
    preset_params: dict[str, Any] | None = None,
    file_params: dict[str, Any] | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Merge parameters with proper precedence.
    
    Precedence (highest to lowest):
    1. CLI overrides
    2. File params (--params)
    3. Preset params
    4. Schema defaults
    
    Args:
        schema: JSON schema for the template.
        preset_params: Parameters from a preset file.
        file_params: Parameters from a user-provided file.
        cli_overrides: Parameters from CLI --set flags.
        
    Returns:
        Merged parameters dict.
    """
    # Start with schema defaults
    merged = get_schema_defaults(schema)
    
    # Layer on preset params
    if preset_params:
        merged.update(preset_params)
    
    # Layer on file params
    if file_params:
        merged.update(file_params)
    
    # Layer on CLI overrides (highest priority)
    if cli_overrides:
        merged.update(cli_overrides)
    
    return merged


def validate_params(schema: dict[str, Any], params: dict[str, Any]) -> None:
    """
    Validate parameters against a JSON schema.
    
    Args:
        schema: JSON schema dict.
        params: Parameters to validate.
        
    Raises:
        SchemaValidationError: If validation fails, with detailed error messages.
    """
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(params))
    
    if errors:
        error_messages = []
        for error in errors:
            path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
            error_messages.append(f"  - {path}: {error.message}")
        
        raise SchemaValidationError(
            f"Parameter validation failed:\n" + "\n".join(error_messages),
            errors=error_messages,
        )


def get_template_variables(template_text: str) -> set[str]:
    """
    Extract all variable names used in a Jinja2 template.
    
    Args:
        template_text: Jinja2 template content.
        
    Returns:
        Set of variable names referenced in the template.
    """
    env = Environment()
    try:
        ast = env.parse(template_text)
        return meta.find_undeclared_variables(ast)
    except TemplateSyntaxError as e:
        raise TemplateError(f"Template syntax error: {e}") from e


def get_schema_variables(schema: dict[str, Any]) -> set[str]:
    """
    Get all variable names defined in a schema.
    
    Args:
        schema: JSON schema dict.
        
    Returns:
        Set of property names defined in the schema.
    """
    return set(schema.get("properties", {}).keys())


def render(template_text: str, params: dict[str, Any]) -> str:
    """
    Render a Jinja2 template with strict undefined checking.
    
    Args:
        template_text: Jinja2 template content.
        params: Parameters to pass to the template.
        
    Returns:
        Rendered template as string.
        
    Raises:
        RenderError: If rendering fails (undefined variable, syntax error, etc).
    """
    env = Environment(undefined=StrictUndefined)
    
    try:
        template = env.from_string(template_text)
        return template.render(**params)
    except UndefinedError as e:
        raise RenderError(f"Undefined variable in template: {e}") from e
    except TemplateSyntaxError as e:
        raise RenderError(f"Template syntax error: {e}") from e
    except Exception as e:
        raise RenderError(f"Rendering failed: {e}") from e


def compute_hash(text: str) -> str:
    """
    Compute SHA256 hash of text.
    
    Args:
        text: Text to hash.
        
    Returns:
        Hex-encoded SHA256 hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def emit_run_packet(
    run_dir: str | Path,
    template_name: str,
    rendered_prompt: str,
    resolved_params: dict[str, Any],
    template_version: str = "0.1.0",
) -> Path:
    """
    Emit a run packet directory with metadata and rendered prompt.
    
    Creates:
        <run_dir>/<timestamp>_<template>/
            prompt.md
            params.resolved.json
            meta.json
    
    Args:
        run_dir: Base directory for run packets.
        template_name: Name of the template.
        rendered_prompt: The rendered prompt text.
        resolved_params: The final resolved parameters.
        template_version: Version of the template/library.
        
    Returns:
        Path to the created run packet directory.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped subdirectory
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    packet_dir = run_dir / f"{timestamp}_{template_name}"
    packet_dir.mkdir(parents=True, exist_ok=True)
    
    # Write rendered prompt
    prompt_file = packet_dir / "prompt.md"
    prompt_file.write_text(rendered_prompt, encoding="utf-8")
    
    # Write resolved params
    params_file = packet_dir / "params.resolved.json"
    params_file.write_text(
        json.dumps(resolved_params, indent=2, sort_keys=True),
        encoding="utf-8"
    )
    
    # Write metadata
    meta = {
        "template": template_name,
        "version": template_version,
        "prompt_hash": compute_hash(rendered_prompt),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "params_hash": compute_hash(json.dumps(resolved_params, sort_keys=True)),
    }
    meta_file = packet_dir / "meta.json"
    meta_file.write_text(
        json.dumps(meta, indent=2, sort_keys=True),
        encoding="utf-8"
    )
    
    return packet_dir


def parse_cli_override(override: str) -> tuple[str, Any]:
    """
    Parse a CLI override in key=value format.
    
    Handles:
    - key=value (string)
    - key=123 (int)
    - key=1.5 (float)
    - key=true/false (bool)
    - key=["a","b"] (JSON array)
    - key={"a":1} (JSON object)
    
    Args:
        override: String in key=value format.
        
    Returns:
        Tuple of (key, parsed_value).
        
    Raises:
        TemplateError: If format is invalid.
    """
    if "=" not in override:
        raise TemplateError(
            f"Invalid override format: '{override}'. Expected 'key=value'."
        )
    
    key, value = override.split("=", 1)
    key = key.strip()
    value = value.strip()
    
    if not key:
        raise TemplateError(f"Empty key in override: '{override}'")
    
    # Try to parse as JSON for complex types
    if value.startswith("[") or value.startswith("{"):
        try:
            return key, json.loads(value)
        except json.JSONDecodeError:
            pass  # Fall through to string
    
    # Try boolean
    if value.lower() == "true":
        return key, True
    if value.lower() == "false":
        return key, False
    
    # Try int
    try:
        return key, int(value)
    except ValueError:
        pass
    
    # Try float
    try:
        return key, float(value)
    except ValueError:
        pass
    
    # Default to string
    return key, value
