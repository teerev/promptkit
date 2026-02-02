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

## CLI Reference

### `pk render` - Full Options

```bash
pk render <template> [OPTIONS]
```

| Flag | Description | Example |
|------|-------------|---------|
| `--preset`, `-p` | Load a preset file (e.g., `default`, `fast`, `deep`) | `--preset fast` |
| `--params`, `-P` | Load parameters from YAML/JSON file | `--params my_config.yaml` |
| `--set`, `-s` | Override a single parameter (repeatable) | `--set depth=deep` |
| `--out`, `-o` | Write output to file instead of stdout | `--out prompt.md` |
| `--format`, `-f` | Override output format | `--format json` |
| `--run-dir` | Create a reproducibility packet | `--run-dir ./runs` |

### Parameter Merging

Parameters are merged in order (later overrides earlier):

1. **Schema defaults** - Defined in `schema.json`
2. **Preset** - From `--preset` flag
3. **Params file** - From `--params` flag (YAML or JSON)
4. **CLI overrides** - From `--set` flags

### `--set` Flag Syntax

The `--set` flag supports multiple value types:

```bash
# Strings
--set repo_path=/path/to/repo
--set notes="Review the auth module carefully"

# Integers
--set time_budget_minutes=120
--set code_examples_count=5

# Booleans
--set include_badges=true
--set include_toc=false

# Arrays (JSON syntax)
--set 'scope=["src/", "lib/"]'
--set 'focus_areas=["security", "performance"]'
--set 'constraints=["Do not modify public APIs", "Preserve backwards compatibility"]'
```

### Complete Examples

```bash
# Quick audit with minimal output
pk render audit \
  --preset fast \
  --set severity_threshold=warning \
  --out quick_audit.md

# Deep security review for a web app
pk render security \
  --preset deep \
  --set threat_model=web_app \
  --set 'compliance_frameworks=["OWASP", "CWE"]' \
  --set 'sensitive_paths=["src/auth/", "src/crypto/"]' \
  --run-dir ./security_runs

# Generate README for junior developers
pk render readme \
  --set audience=junior_eng \
  --set code_examples_count=5 \
  --set include_toc=true \
  --set 'sections=["overview", "installation", "usage", "api"]'

# Audit with custom scope and constraints
pk render audit \
  --set 'scope=["src/api/", "src/models/"]' \
  --set 'exclude_patterns=["**/*.test.ts", "**/mocks/**"]' \
  --set 'focus_areas=["error_handling", "code_quality"]' \
  --set 'definition_of_done=["All critical issues addressed", "No security vulnerabilities"]'

# PR review with custom params file
pk render pr_review \
  --params ./review_config.yaml \
  --set pr_title="Add user authentication" \
  --set 'review_focus=["security", "correctness"]'
```

## Base Parameters (All Templates)

These parameters are available across all templates:

| Parameter | Type | Values | Default | Description |
|-----------|------|--------|---------|-------------|
| `repo_path` | string | any path | `"."` | Path to repository root |
| `scope` | array | glob patterns | `["."]` | Directories/files to include |
| `time_budget_minutes` | integer | 5+ | varies | Time budget for the task |
| `depth` | enum | `fast`, `normal`, `deep` | `"normal"` | Analysis thoroughness |
| `output_format` | enum | `markdown`, `json` | `"markdown"` | Output format |
| `risk_tolerance` | enum | `conservative`, `balanced`, `aggressive` | `"balanced"` | Risk level for recommendations |
| `audience` | enum | `senior_eng`, `junior_eng`, `non_tech` | `"senior_eng"` | Target audience |
| `definition_of_done` | array | any strings | `[]` | Completion criteria |
| `constraints` | array | any strings | `[]` | Constraints to observe |
| `assumptions` | array | any strings | `[]` | Assumptions about the task |
| `notes` | string | any text | `""` | Additional context |

## Template-Specific Parameters

### `audit` - Code Quality Audit

| Parameter | Type | Values | Default |
|-----------|------|--------|---------|
| `focus_areas` | array | `code_quality`, `maintainability`, `error_handling`, `documentation` | all four |
| `exclude_patterns` | array | glob patterns | common excludes |
| `severity_threshold` | enum | `info`, `warning`, `error`, `critical` | `"info"` |

### `security` - Security Review

| Parameter | Type | Values | Default |
|-----------|------|--------|---------|
| `threat_model` | enum | `web_app`, `api`, `cli`, `library`, `infrastructure`, `general` | `"general"` |
| `compliance_frameworks` | array | e.g., `OWASP`, `CWE`, `PCI-DSS` | `[]` |
| `exclude_patterns` | array | glob patterns | common excludes |
| `sensitive_paths` | array | paths requiring extra scrutiny | `[]` |

### `readme` - README Generator

| Parameter | Type | Values | Default |
|-----------|------|--------|---------|
| `readme_mode` | enum | `create`, `improve`, `audit` | `"create"` |
| `project_name` | string | any (auto-detected if empty) | `""` |
| `existing_readme_path` | string | path to existing README | `""` |
| `sections` | array | `overview`, `installation`, `usage`, `api`, `contributing`, `license` | all six |
| `include_badges` | boolean | `true`, `false` | `true` |
| `include_toc` | boolean | `true`, `false` | `true` |
| `code_examples_count` | integer | 0-10 | `3` |

### `pr_review` - Pull Request Review

| Parameter | Type | Values | Default |
|-----------|------|--------|---------|
| `pr_title` | string | any | `""` |
| `pr_description` | string | any | `""` |
| `review_focus` | array | `correctness`, `security`, `performance`, `maintainability` | all four |

### Other Templates

Use `pk show <template>` to see all parameters for any template:

```bash
pk show test_plan      # Test planning parameters
pk show refactor_plan  # Refactoring parameters  
pk show perf_cost      # Performance analysis parameters
pk show ci_cd          # CI/CD analysis parameters
```

## Available Presets

Each template includes presets for common scenarios:

| Template | Presets | Description |
|----------|---------|-------------|
| `audit` | `default`, `fast`, `deep` | Varies time budget and severity threshold |
| `security` | `default`, `fast`, `deep` | Varies depth and compliance frameworks |
| `readme` | `default`, `fast`, `deep` | Varies sections and example count |
| Others | `default` | Standard configuration |

View presets with:
```bash
pk presets audit
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
