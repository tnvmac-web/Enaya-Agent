---
name: enaya-doc-audit
description: "Documentation vs codebase drift detection"
version: 1.0.0
author: Enaya Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [documentation, audit, drift-detection, consistency]
    category: documentation
    related_skills: [enaya-code-review, enaya-planning]
---

# Enaya Doc Audit Skill

Documentation vs codebase drift detection and consistency checking.

## When This Skill Activates

Use this skill when the user:
- Wants to check if documentation matches code
- Needs to find outdated documentation
- Requests API documentation validation
- Asks for README/AGENTS.md accuracy check

## Workflow

### 1. Documentation Discovery
- Find all documentation files (README, AGENTS.md, docs/, docstrings)
- Parse structure and claims

### 2. Codebase Analysis
- Extract actual APIs, configs, conventions
- Identify documented vs actual behavior

### 3. Drift Detection
- Compare docs vs code
- Flag outdated examples
- Find missing documentation

### 4. Consistency Check
- Cross-reference internal links
- Validate code examples
- Check version references

### 5. Report Generation
- Drift report with file/line references
- Suggested updates
- Priority ranking

## Tool Chain

```
doc_discovery → codebase_analysis → drift_detection → consistency_check → audit_report
```

## Example Usage

```
User: "Audit the documentation for drift"
Enaya: [Executes doc audit workflow]
1. Scans all .md files and docstrings
2. Compares against actual code
3. Reports: 5 outdated examples, 3 broken links, 2 missing API docs
4. Provides specific fix recommendations
```

## Configuration

- `doc_paths`: Paths to scan (default: README.md, AGENTS.md, docs/, src/**/*.py)
- `check_examples`: Validate code examples (default: true)
- `check_links`: Validate internal/external links (default: true)
- `check_versions`: Check version references (default: true)
- `severity_threshold`: Minimum severity to report (default: warning)