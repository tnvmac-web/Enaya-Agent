---
name: enaya-research
description: "Deep research workflow: query → search → extract → synthesize → validate"
version: 1.0.0
author: Enaya Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, web-search, academic, synthesis, validation]
    category: research
    related_skills: [enaya-planning, enaya-delegation, enaya-synthesis]
---

# Enaya Research Skill

Deep research workflow for comprehensive information gathering and synthesis.

## When This Skill Activates

Use this skill when the user:
- Asks to research a topic deeply
- Wants academic paper analysis
- Needs source validation and credibility assessment
- Requests synthesis of multiple sources
- Asks for literature reviews or market research

## Workflow

### 1. Query Analysis
- Parse the research question
- Identify key concepts and search terms
- Determine research depth (quick/deep/comprehensive)
- Select source types (web, academic, all)

### 2. Source Discovery
- **Web Search**: Use `web_search` for current information
- **Academic Search**: Use `arxiv_search` for papers
- **Iterative Deepening**: Follow citations and related work

### 3. Content Extraction
- **Web Pages**: Use `web_extract` for full content
- **Papers**: Use `paper_analyze` for PDF/arXiv papers
- **Validation**: Use `source_validator` for credibility

### 4. Synthesis
- Use `synthesize_results` to merge findings
- Use `compare_sources` for conflicting info
- Use `extract_claims` for verifiable claims

### 5. Validation & Output
- Cross-reference claims
- Flag uncertainties
- Provide structured report with citations

## Tool Chain

```
query → web_search/arxiv_search → web_extract/paper_analyze → source_validator → synthesize_results → final_report
```

## Example Usage

```
User: "Research the current state of LLM agent architectures"
Enaya: [Executes research workflow]
1. Searches web for recent articles
2. Searches arXiv for relevant papers
3. Extracts and analyzes top 10 sources
4. Validates credibility
5. Synthesizes into structured report
6. Delivers with citations and confidence scores
```

## Configuration

- `max_sources`: Maximum sources to analyze (default: 10)
- `depth`: quick | deep | comprehensive (default: deep)
- `source_types`: web | academic | all (default: all)
- `conflict_resolution`: latest | consensus | manual (default: consensus)