---
name: enaya-delegation
description: "Subagent spawning, monitoring, steering, and result aggregation"
version: 1.0.0
author: Enaya Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, multi-agent, orchestration, subagent]
    category: delegation
    related_skills: [enaya-research, enaya-planning, enaya-synthesis]
---

# Enaya Delegation Skill

Multi-agent orchestration workflow for complex task delegation.

## When This Skill Activates

Use this skill when the user:
- Asks to delegate a complex task
- Wants parallel execution of independent subtasks
- Needs subagent monitoring and steering
- Requests result aggregation from multiple subagents

## Workflow

### 1. Task Assessment
- Analyze task for delegation suitability
- Check complexity threshold
- Identify parallelizable components
- Select appropriate subagent configuration

### 2. Subagent Spawning
- Use `delegate_task` to spawn subagents
- Configure model, toolsets, iteration limits
- Provide context and constraints

### 3. Monitoring & Steering
- Use `subagent_status` to track progress
- Use `subagent_steer` for mid-course corrections
- Use `subagent_stop` if needed

### 4. Result Collection
- Wait for completion
- Use `synthesize_results` to merge outputs
- Handle conflicts and gaps

## Tool Chain

```
task → delegate_task (×N) → subagent_status → subagent_steer → collect → synthesize_results
```

## Example Usage

```
User: "Research and compare three different approaches to distributed caching"
Enaya: [Executes delegation workflow]
1. Decomposes into 3 parallel research subagents
2. Each subagent investigates one approach
3. Monitors progress, steers if needed
4. Collects and synthesizes all results
5. Delivers comparative analysis
```

## Configuration

- `max_parallel_subagents`: Maximum concurrent subagents (default: 3)
- `default_max_iterations`: Default iteration limit per subagent (default: 50)
- `auto_synthesize`: Automatically synthesize results (default: true)
- `conflict_resolution`: latest | consensus | manual (default: consensus)
- `delegation_depth`: Maximum recursive delegation depth (default: 2)