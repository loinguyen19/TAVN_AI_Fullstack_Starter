# Take-Home Assignment — Torque Specification Validator

## Context

You're joining a team that manages automotive torque specification data. Workshop technicians rely on this data to apply the correct torque to fasteners — wrong values can cause mechanical failure.

You receive a working but incomplete application that parses torque XML files and displays the data. The validation layer is minimal — only one example validator is implemented.

## What You Get

- A working stack: Python/FastAPI backend + React/TypeScript frontend + Docker Compose
- A sample data file in `data/`
- A brief data specification in `data-specification.md`
- One example validator (`MissingTorqueValidator`) showing the pattern

## Your Task

**Add data quality validators** that catch real issues in the sample file.

Specifically:

1. **Study the data.** Open the XML file, read it carefully, understand what the data represents. Look for anything a workshop technician should be warned about.

2. **Implement validators.** Follow the existing pattern (`BaseValidator` subclass, register in `registry.py`). Each validator should check for a specific class of data quality issue.

3. **Surface findings in the UI.** The frontend already displays validation results in a table. Improve how issues are presented — severity coloring, grouping, filtering, or any UX you think helps a data quality reviewer.

4. **Add upload history.** Store past uploads and their validation results (SQLite, JSON file, or any lightweight persistence). Add a way to browse previous uploads in the UI.

5. **Add export.** Let the user download validation results as CSV.

6. **(Optional) Describe deployment.** In a short `ARCHITECTURE.md`, sketch how you'd deploy this on AWS. Consider: What happens when a user uploads a 500 MB ZIP with 200+ files? How do you handle the API Gateway 29-second timeout?

## Constraints

- Keep the existing stack (FastAPI + React + Docker Compose). Don't rewrite it in a different framework.
- Your solution must run with `docker compose up` — we will test it.
- Time limit: **4 hours**. Focus on the validators and data understanding. Don't spend time on styling or features we didn't ask for.

## What We Evaluate

| Priority | What |
|----------|------|
| **High** | Did you find the data quality issues? Do your validators catch them? |
| **High** | Do you understand *why* each issue matters in this domain? |
| **Medium** | Is the validator code well-structured and extensible? |
| **Medium** | Are findings clearly surfaced in the UI? |
| **Medium** | Upload history and export functionality |
| **Low** | Frontend polish, extra features, deployment docs |

## Submission

Return the complete project folder (zip or git repo). We will run `docker compose up` and upload the sample file.
