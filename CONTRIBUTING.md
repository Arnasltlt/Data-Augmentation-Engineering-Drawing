# Contributing to Symbol-Heavy Drawing Generator

## 🛡️ RepoGuardian Enforcement Rules

This project is actively monitored by **RepoGuardian** to ensure quality and consistency across all agent contributions.

## Repository Structure

```
/symbols/          ← canonical SVG blocks
/src/              ← Python packages (one sub-folder per agent)
/tests/            ← unit + integration tests
/examples/         ← demo PDFs, PNGs, JSON
/tools/            ← RepoGuardian monitoring scripts
/.github/          ← CI/CD workflows
```

## Development Guidelines

### Branching Strategy
- **Protected `main` branch** - direct commits forbidden
- **Feature branches**: `agent-<name>/<feature>`
- Example: `agent-vectorforge/gdt-symbols`, `agent-layoutlab/placement-engine`

### Code Quality Standards
- **Language**: Python 3.11
- **Formatting**: `black` (enforced via pre-commit)
- **Linting**: `ruff` (enforced via pre-commit)
- **Testing**: pytest with ≥80% coverage target

### File Naming Conventions
- **Generated files**: Prefixed with first 8 chars of Git commit SHA
- **Format**: `page_<sha>_*.{pdf,png,json}`
- **Example**: `page_abc12def_drawing.pdf`, `page_abc12def_drawing.json`

## Pull Request Process

### 1. Pre-submission Checklist
- [ ] Branch follows naming convention: `agent-<name>/<feature>`
- [ ] All CI checks pass (linting, tests, formatting)
- [ ] **Completion score ≥ 90/100** (automatically checked)
- [ ] No individual metric at 0
- [ ] Changes documented in PR description

### 2. RepoGuardian Automatic Checks
Every PR triggers:
- Completion score calculation
- License compliance verification
- Convention adherence check
- Cross-agent API compatibility check

### 3. Merge Requirements
- ✅ All CI checks green
- ✅ Completion score ≥ 90/100
- ✅ RepoGuardian approval
- ✅ No merge conflicts

## Agent-Specific Guidelines

### VectorForge (SVG Symbol Library)
- **Output**: `/symbols/*.svg`, `symbols_manifest.yaml`
- **License**: Only OSI-approved or CC-0
- **Breaking changes**: Tag `@layoutlab` before modifying symbol schema

### LayoutLab (Placement Engine)
- **Output**: `/src/layoutlab/`
- **API contracts**: Document any JSON key changes
- **Performance**: Maintain placement throughput benchmarks

### GrungeWorks (Noise Pipeline)
- **Output**: `/src/grungeworks/`
- **Filters**: Maintain backward compatibility
- **CLI**: Follow click conventions

### QualityGate (Testing & Validation)
- **Output**: `/tests/`
- **Coverage**: Maintain ≥80% test coverage
- **Integration**: End-to-end test scenarios

### CLI-Ops (Command Interface)
- **Output**: `generate.py`, CLI enhancements
- **Commands**: Backward compatible flags
- **Help**: Keep documentation current

## Escalation Procedures

### License Issues
If license provenance is unclear:
1. Create GitHub Issue with label `legal-hold`
2. Tag `@QualityGate` and `@VectorForge`
3. **All merges blocked** until resolved

### API Conflicts
If agent APIs diverge:
1. Create Issue with label `contract-break`
2. Assign both conflicting agents
3. Block dependent PRs until resolution

### Emergency Procedures
For critical bugs in `main`:
1. Create hotfix branch: `hotfix/<description>`
2. Tag `@RepoGuardian` for expedited review
3. Emergency merge with ≥2 agent approvals

## RepoGuardian Monitoring

### Completion Score Metrics
- **Symbol coverage**: 30 pts (60+ symbols, manifest parity)
- **Layout engine**: 15 pts (throughput benchmarks)
- **Noise pipeline**: 10 pts (filter variety)
- **End-to-end generator**: 20 pts (successful run)
- **Test coverage**: 10 pts (≥80% coverage)
- **CI status**: 10 pts (green streak)

### Weekly Status Reports
Every Sunday 00:00 UTC, RepoGuardian posts progress digest in Discussion `#progress`:
- Completed vs planned milestones
- Current blockers
- Next-week focus per agent

## Success Metrics

### Release Readiness (`v1.0`)
Project is release-ready when:
- ✅ `main` branch passes `generate.py -n 3 --noise-level 2`
- ✅ All CI checks green for 2 consecutive weeks
- ✅ Completion score ≥ 90/100 sustained
- ✅ Weekly digests posted on schedule

When achieved, RepoGuardian tags release `v1.0` and closes milestone **"Dataset MVP"**.

---

*Enforced by RepoGuardian 🛡️ - The integration & oversight AI*