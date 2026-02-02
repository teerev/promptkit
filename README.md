# promptkit

Production-grade prompt template library and CLI for LLM-assisted software engineering.

[![CI](https://github.com/promptkit/promptkit/actions/workflows/ci.yml/badge.svg)](https://github.com/promptkit/promptkit/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

## Overview

promptkit provides reusable "archetype" prompt templates for common software engineering tasks. Each template is:

- **Self-contained**: Template + schema + presets + tests in one unit
- **Strictly validated**: Typed parameters with JSON Schema validation
- **Deterministic**: Fails hard on missing parameters (no silent nulls)
- **Reproducible**: Version tracking, parameter hashing, run packets
- **Testable**: Golden tests to catch template drift

Think of prompts as code: versioned, testable, lintable, reproducible.

## Installation

### Using pip (editable install for development)

```bash
git clone https://github.com/promptkit/promptkit.git
cd promptkit
pip install -e ".[dev]"
```

### Using pipx (isolated install)

```bash
pipx install git+https://github.com/promptkit/promptkit.git
```

### Using uv

```bash
uv tool install git+https://github.com/promptkit/promptkit.git
```

## Quick Start

### List available templates

```bash
pk list
```

Output:
```
Template          Description
---------------------------------------------------------
audit             Comprehensive code quality audit with prioritized findings
security          Security-focused code review identifying vulnerabilities
readme            Generate or improve README documentation
...
```

### Show template details

```bash
pk show audit
```

### List presets for a template

```bash
pk presets audit
```

### Render a prompt

```bash
# Render with default preset
pk render audit --preset default

# Render with custom parameters
pk render audit --preset fast --set repo_path=/path/to/repo --set time_budget_minutes=30

# Render to a file
pk render audit --preset default --out prompt.md

# Render with run packet (for reproducibility)
pk render audit --preset default --run-dir ./runs
```

### Validate templates

```bash
# Validate all templates
pk doctor

# Validate a specific template
pk doctor --template audit
```

## Available Templates

| Template | Description |
|----------|-------------|
| `audit` | Comprehensive code quality audit with prioritized findings |
| `security` | Security-focused code review identifying vulnerabilities |
| `readme` | Generate or improve README documentation |
| `repo_map` | Repository structure and architecture mapping |
| `core_spine` | Identify critical path and essential modules |
| `failure_modes` | Analyze potential failure modes and edge cases |
| `test_plan` | Generate comprehensive test plans |
| `coverage_critique` | Analyze test coverage quality and gaps |
| `refactor_plan` | Create systematic refactoring plans |
| `perf_cost` | Performance bottleneck and cost analysis |
| `ci_cd` | CI/CD pipeline analysis and improvements |
| `pr_review` | Pull request code review |

## Usage in Other Repositories

promptkit is designed to be used from any repository. Simply install it globally and run:

```bash
# From any repo, render a prompt for that repo
cd /path/to/your/project
pk render audit --preset default --set repo_path=. --out audit_prompt.md

# Create a run packet for reproducibility
pk render security --preset deep --run-dir ./prompt_runs
```

### Run Packets

When using `--run-dir`, promptkit creates a timestamped directory containing:

```
runs/20240115_143022_audit/
├── prompt.md           # Rendered prompt
├── params.resolved.json # Final resolved parameters
└── meta.json           # Metadata (template, version, hash, timestamp)
```

This enables:
- Reproducing exact prompts later
- Tracking which prompts were used for which tasks
- Auditing prompt usage over time

## Parameter Merging

Parameters are merged in order (later overrides earlier):

1. **Schema defaults** - Defined in `schema.json`
2. **Preset** - From `--preset` flag
3. **Params file** - From `--params` flag (YAML or JSON)
4. **CLI overrides** - From `--set` flags

Example:
```bash
pk render audit \
  --preset fast \
  --params custom_params.yaml \
  --set time_budget_minutes=15 \
  --set depth=deep
```

## Adding a New Template

1. Create the template directory structure:

```bash
mkdir -p templates/my_template/{examples,tests}
```

2. Create `schema.json` with parameter definitions:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "My Template",
  "description": "Description of what this template does",
  "type": "object",
  "properties": {
    "repo_path": {
      "type": "string",
      "default": ".",
      "description": "Path to the repository"
    },
    "custom_param": {
      "type": "string",
      "description": "A custom parameter"
    }
  },
  "required": ["custom_param"]
}
```

3. Create `template.md` following the standard structure:

```markdown
# Role & Mission
[What the model should be/do]

# Inputs
- **Repo Path**: `{{ repo_path }}`
- **Custom Param**: {{ custom_param }}

# Procedure
[Step-by-step instructions]

# Output Contract
[Exact required output format]

# Stop Conditions
[When to stop]

# Refusal Conditions
[When to refuse]

# Evidence Requirements
[Citation requirements]
```

4. Create preset examples in `examples/`:

```yaml
# examples/default.yaml
repo_path: "."
custom_param: "default_value"
```

5. Create golden test in `tests/render_golden.md`:
   - Render your template with the default preset
   - Save the output as the golden file

6. Validate your template:

```bash
pk doctor --template my_template
```

## Base Parameters

These parameters are available across most templates:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repo_path` | string | "." | Path to repository root |
| `scope` | array[string] | ["."] | Directories/globs to include |
| `time_budget_minutes` | integer | 60 | Time budget for the task |
| `depth` | enum | "normal" | fast/normal/deep |
| `output_format` | enum | "markdown" | markdown/json |
| `risk_tolerance` | enum | "balanced" | conservative/balanced/aggressive |
| `audience` | enum | "senior_eng" | senior_eng/junior_eng/non_tech |
| `definition_of_done` | array[string] | [] | Completion criteria |
| `constraints` | array[string] | [] | Constraints to observe |
| `assumptions` | array[string] | [] | Assumptions about the task |
| `notes` | string | "" | Additional context |

## Development

### Setup

```bash
git clone https://github.com/promptkit/promptkit.git
cd promptkit
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest -v
```

### Running Doctor

```bash
pk doctor
```

### Code Style

The project uses [ruff](https://github.com/astral-sh/ruff) for linting:

```bash
ruff check pk/ tests/
```

## License

Apache 2.0 - see [LICENSE](LICENSE) for details.
