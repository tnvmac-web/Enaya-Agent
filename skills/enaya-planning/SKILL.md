---
name: enaya-planning
description: "Task decomposition → plan creation → validation → execution monitoring"
version: 1.0.0
author: Enaya Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, task-decomposition, project-management, validation]
    category: planning
    related_skills: [enaya-research, enaya-delegation, enaya-code-review]
---

# Enaya Planning Skill

Structured planning workflow for complex goals.

## When This Skill Activates

Use this skill when the user:
- Asks to create a plan for a complex goal
- Wants task decomposition
- Needs project roadmap or milestone planning
- Requests plan validation and risk assessment
- Wants to track plan execution

## Workflow

### 1. Goal Analysis
- Parse the high-level goal
- Identify constraints and requirements
- Determine complexity level

### 2. Task Decomposition
- Use `task_decompose` to break into subtasks
- Identify dependencies
- Estimate effort and skills needed

### 3. Plan Creation
- Use `plan_create` to build execution phases
- Group parallelizable tasks
- Define milestones

### 4. Plan Validation
- Use `plan_review` for feasibility check
- Identify risks and gaps
- Score and iterate

### 5. Execution Monitoring
- Track progress against plan
- Adjust for changes
- Report status

## Tool Chain

```
goal → task_decompose → plan_create → plan_review → validated_plan → execution
```

## Example Usage

```
User: "Plan the implementation of a new authentication system"
Enaya: [Executes planning workflow]
1. Decomposes into: design, database, API, frontend, testing, deployment
2. Creates phased plan with parallel groups
3. Validates for completeness and risks
4. Delivers structured plan with milestones
```

## Configuration

- `max_depth`: Maximum decomposition depth (default: 3)
- `parallel_groups`: Enable parallel task grouping (default: true)
- `validation_criteria`: List of criteria to check (default: all)
- `include_milestones`: Add milestones to plan (default: true)