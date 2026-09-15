---
name: enaya-code-review
description: "Automated code review with security/quality gates"
version: 1.0.0
author: Enaya Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, security, quality, static-analysis]
    category: code-review
    related_skills: [enaya-planning, enaya-delegation, enaya-doc-audit]
---

# Enaya Code Review Skill

Automated code review with security scanning and quality gates.

## When This Skill Activates

Use this skill when the user:
- Asks for code review of a PR or changes
- Wants security vulnerability scanning
- Needs code quality assessment
- Requests best practices validation

## Workflow

### 1. Code Fetch
- Get changed files (from git diff or provided paths)
- Parse language and framework

### 2. Static Analysis
- Run linters (ruff, mypy, eslint, etc.)
- Run security scanners (bandit, semgrep, etc.)
- Check for common vulnerabilities

### 3. Quality Assessment
- Code complexity (cyclomatic, cognitive)
- Test coverage gaps
- Documentation coverage
- Best practice violations

### 4. Review Synthesis
- Aggregate findings
- Prioritize by severity
- Provide actionable feedback

### 5. Report Generation
- Summary with severity counts
- Detailed findings with line numbers
- Suggested fixes

## Tool Chain

```
git_diff → file_tools → linters → security_scanners → quality_metrics → synthesize_results → review_report
```

## Example Usage

```
User: "Review the latest changes in src/auth/"
Enaya: [Executes code review workflow]
1. Gets diff of recent changes
2. Runs ruff, mypy, bandit
3. Analyzes complexity and coverage
4. Produces prioritized review report
```

## Configuration

- `linters`: List of linters to run (default: ruff, mypy)
- `security_scanners`: List of scanners (default: bandit)
- `min_coverage`: Minimum test coverage % (default: 60)
- `max_complexity`: Maximum cyclomatic complexity (default: 10)
- `severity_threshold`: Minimum severity to report (default: medium)