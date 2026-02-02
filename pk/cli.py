"""
CLI interface for promptkit.

Commands:
- list: List available templates
- show: Show template details
- presets: List presets for a template
- render: Render a template with parameters
- doctor: Validate all templates
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from pk import __version__
from pk.doctor import validate_all_templates
from pk.render import (
    PresetNotFoundError,
    SchemaValidationError,
    TemplateError,
    TemplateNotFoundError,
    emit_run_packet,
    get_template_dir,
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


@click.group()
@click.version_option(version=__version__, prog_name="pk")
def main():
    """
    pk - Production-grade prompt template library for LLM-assisted software engineering.

    Render, validate, and manage reusable prompt templates with strict schemas
    and deterministic rendering.
    """
    pass


@main.command("list")
def list_cmd():
    """List all available templates."""
    templates = list_templates()

    if not templates:
        click.echo("No templates found.", err=True)
        sys.exit(1)

    # Calculate column width
    max_name_len = max(len(t["name"]) for t in templates)

    click.echo(f"{'Template':<{max_name_len}}  Description")
    click.echo("-" * (max_name_len + 2 + 50))

    for template in templates:
        name = template["name"]
        desc = template["description"]
        # Truncate description if too long
        if len(desc) > 60:
            desc = desc[:57] + "..."
        click.echo(f"{name:<{max_name_len}}  {desc}")


@main.command("show")
@click.argument("template")
def show_cmd(template: str):
    """Show details for a template."""
    try:
        template_dir = get_template_dir(template)
        schema = load_schema(template)
    except TemplateNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Template: {template}")
    click.echo(f"Path: {template_dir}")
    click.echo()

    # Show schema summary
    click.echo("Schema:")
    click.echo(f"  Title: {schema.get('title', 'N/A')}")
    click.echo(f"  Description: {schema.get('description', 'N/A')}")
    click.echo()

    # Show parameters
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    if properties:
        click.echo("Parameters:")
        for name, prop in sorted(properties.items()):
            req_marker = "*" if name in required else " "
            prop_type = prop.get("type", "any")
            default = prop.get("default", "")
            default_str = f" (default: {default})" if default != "" else ""
            description = prop.get("description", "")

            click.echo(f"  {req_marker} {name}: {prop_type}{default_str}")
            if description:
                click.echo(f"      {description}")

    # Show presets
    presets = list_presets(template)
    if presets:
        click.echo()
        click.echo(f"Presets: {', '.join(presets)}")

    # Show files
    click.echo()
    click.echo("Files:")
    click.echo(f"  template.md: {template_dir / 'template.md'}")
    click.echo(f"  schema.json: {template_dir / 'schema.json'}")


@main.command("presets")
@click.argument("template")
def presets_cmd(template: str):
    """List available presets for a template."""
    try:
        get_template_dir(template)  # Validate template exists
    except TemplateNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    presets = list_presets(template)

    if not presets:
        click.echo(f"No presets found for template '{template}'.")
        return

    click.echo(f"Presets for '{template}':")
    for preset in presets:
        click.echo(f"  - {preset}")


@main.command("render")
@click.argument("template")
@click.option("--preset", "-p", help="Preset name to use (e.g., 'fast', 'deep')")
@click.option("--params", "-P", "params_file", type=click.Path(exists=True),
              help="YAML or JSON file with parameters")
@click.option("--set", "-s", "overrides", multiple=True,
              help="Override parameter: key=value (repeatable)")
@click.option("--out", "-o", "output_file", type=click.Path(),
              help="Write output to file instead of stdout")
@click.option("--format", "-f", "output_format", type=click.Choice(["markdown", "json"]),
              help="Override output_format parameter")
@click.option("--run-dir", "run_dir", type=click.Path(),
              help="Emit a run packet directory with metadata")
def render_cmd(
    template: str,
    preset: str | None,
    params_file: str | None,
    overrides: tuple[str, ...],
    output_file: str | None,
    output_format: str | None,
    run_dir: str | None,
):
    """
    Render a template with parameters.

    Parameters are merged in order (later overrides earlier):

    \b
    1. Schema defaults
    2. Preset file (--preset)
    3. Params file (--params)
    4. CLI overrides (--set)

    Examples:

    \b
      pk render audit --preset fast
      pk render security --params my_params.yaml --set repo_path=/path/to/repo
      pk render readme --preset default --out prompt.md --run-dir ./runs
    """
    # Load template and schema
    try:
        template_text = load_template(template)
        schema = load_schema(template)
    except TemplateNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except TemplateError as e:
        click.echo(f"Error loading template: {e}", err=True)
        sys.exit(1)

    # Load preset if specified
    preset_params = None
    if preset:
        try:
            preset_params = load_preset(template, preset)
        except PresetNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except TemplateError as e:
            click.echo(f"Error loading preset: {e}", err=True)
            sys.exit(1)

    # Load params file if specified
    file_params = None
    if params_file:
        try:
            file_params = load_params_file(params_file)
        except TemplateError as e:
            click.echo(f"Error loading params file: {e}", err=True)
            sys.exit(1)

    # Parse CLI overrides
    cli_overrides = {}
    for override in overrides:
        try:
            key, value = parse_cli_override(override)
            cli_overrides[key] = value
        except TemplateError as e:
            click.echo(f"Error parsing override: {e}", err=True)
            sys.exit(1)

    # Apply --format flag as an override if specified
    if output_format:
        cli_overrides["output_format"] = output_format

    # Merge parameters
    merged_params = merge_params(
        schema,
        preset_params=preset_params,
        file_params=file_params,
        cli_overrides=cli_overrides,
    )

    # Validate parameters
    try:
        validate_params(schema, merged_params)
    except SchemaValidationError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Render template
    try:
        rendered = render(template_text, merged_params)
    except TemplateError as e:
        click.echo(f"Error rendering template: {e}", err=True)
        sys.exit(1)

    # Emit run packet if requested
    if run_dir:
        try:
            packet_dir = emit_run_packet(
                run_dir=run_dir,
                template_name=template,
                rendered_prompt=rendered,
                resolved_params=merged_params,
            )
            click.echo(f"Run packet created: {packet_dir}", err=True)
        except Exception as e:
            click.echo(f"Warning: Failed to create run packet: {e}", err=True)

    # Output result
    if output_file:
        Path(output_file).write_text(rendered, encoding="utf-8")
        click.echo(f"Output written to: {output_file}", err=True)
    else:
        click.echo(rendered)


@main.command("doctor")
@click.option("--template", "-t", help="Validate only a specific template")
def doctor_cmd(template: str | None):
    """
    Validate templates and run health checks.

    Checks:

    \b
    - Schema JSON validity
    - Preset validation against schemas
    - Template rendering with presets
    - Variable coverage (no undeclared variables)
    - Golden tests (output matches expected)

    Exits with non-zero status if any check fails.
    """
    if template:
        # Validate single template
        try:
            from pk.doctor import validate_template
            results = validate_template(template)
            from pk.doctor import DoctorReport
            report = DoctorReport()
            for r in results:
                report.add(r)
        except TemplateNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    else:
        # Validate all templates
        report = validate_all_templates()

    click.echo(report.format_report())

    if not report.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
