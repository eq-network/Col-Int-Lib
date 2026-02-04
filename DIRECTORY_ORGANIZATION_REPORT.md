# Directory Organization Report

## Current Structure Analysis

### Issues Found

**1. Unclear Hierarchy** (8 directories with vague/inconsistent names)
- `random_shit/` - Unclear purpose, unprofessional naming
- `UI Col-Int-Lib/` - Spaces in name, unclear abbreviation
- `Related Papers/` - Spaces in name
- `experiment_outputs/` - Single experiment output, possibly orphaned
- `plans/` vs `docs/` - Overlapping purposes

**2. Misplaced Files** (11 files at wrong level)
- `demo_tracker.py` - Should be in `examples/`
- `test_tracker.py` - Should be in `tests/`
- `predict.py` - CLI tool, should be in dedicated location
- `tracker.db` - Runtime data, should be in `.gitignore` or `data/`
- `NUL` - Windows artifact, should be deleted
- `Building the Collective Intelligence Visualizer.pdf` - Should be in `docs/`
- Top-level documentation sprawl (8 MD files)

**3. Naming Inconsistency** (3 different patterns)
- Spaces: `Related Papers/`, `UI Col-Int-Lib/`
- Underscores: `experiment_outputs/`, `mcp_server/`, `prediction_service/`
- Hyphens: None currently used
- Mixed case in directories

**4. Clutter** (5+ items)
- `NUL` - Windows artifact
- `tracker.db` - Runtime database file
- Empty `__init__.py` at root
- Multiple overlapping documentation files
- Old experiment outputs

**5. Documentation Sprawl** (35 markdown files, 8 at root)
Root-level docs create confusion about what's the entry point:
- `README.md` - Main entry
- `CLAUDE.md` - Repository guidance
- `Start_Here.md` - Tutorial
- `Manifesto.md` - Philosophy
- `STATUS.md` - Project status
- `USER_STORY.md` - ???
- `COMPLETION_REPORT.md` - Project report
- `CODE_CLEANUP_REPORT.md` - Recent cleanup
- `DONE_SERVICE_REFACTOR.md` - Refactor summary
- `PREDICTION_TRACKER.md` - Feature documentation

### Current Structure (Key Directories)

```
mycorrhiza/
├── core/                        # Core primitives ✓
├── engine/                      # Protocol library ✓
│   ├── agents/
│   ├── environments/
│   └── transformations/
├── studio/                      # Visualizer ✓
│   ├── configs/
│   └── screens/
├── prediction_service/          # HTTP API ✓
├── tracker/                     # Legacy tracker ✓
├── mcp_server/                  # MCP integration ✓
├── execution/                   # Execution strategies ✓
├── examples/                    # Examples ✓
├── tests/                       # Tests ✓
├── docs/                        # Documentation ✓
├── plans/                       # Planning docs (overlaps docs/)
├── experiments/                 # Experiment code ✓
├── experiment_outputs/          # Single old output (clutter)
├── random_shit/                 # Unclear experiments ❌
├── UI Col-Int-Lib/             # Design assets ❌
├── Related Papers/             # Research papers ❌
├── .claude/                    # Claude Code config ✓
└── [17 files at root]          # Too many ❌
```

### First Principles Identified

**Primary Access Pattern:**
1. New users: `README.md` → `Start_Here.md` → examples
2. Developers: Core language primitives → protocols → execution
3. Feature users: Prediction tracker, Studio visualizer
4. Researchers: Papers, experiments, thesis context

**Natural Groupings:**
1. **Core Language** - Primitives, transforms, composition (keep as-is)
2. **Applications** - Prediction tracker, Studio (group better)
3. **Experiments & Research** - Papers, experimental code, results
4. **Documentation** - Guides, architecture, planning
5. **Infrastructure** - Tests, execution, tooling

**Hierarchy of Importance:**
1. Top level: Entry points (README, core, main apps)
2. Second level: Features (prediction tracker, studio)
3. Third level: Supporting (docs, experiments, tools)

**Growth Pattern:**
- More protocol implementations in `engine/`
- More applications (like prediction tracker)
- More experiments and research
- More integrations (MCP, APIs)

---

## Proposed Structure

### Organizational Strategy

**Hybrid approach:**
- Feature-based for applications (prediction tracker, studio)
- Layer-based for core language (core, engine, execution)
- Purpose-based for supporting files (docs, research, tools)

### New Structure

```
mycorrhiza/
├── README.md                   # Main entry point
├── pyproject.toml             # Python project config (future)
├── requirements.txt
│
├── core/                       # Language primitives (unchanged)
│   ├── graph.py
│   ├── category.py
│   ├── property.py
│   ├── agents.py
│   ├── environment.py
│   ├── simulation.py
│   └── ...
│
├── engine/                     # Protocol library (unchanged)
│   ├── transformations/
│   ├── agents/
│   └── environments/
│
├── execution/                  # Execution strategies (unchanged)
│   ├── config.py
│   └── worker.py
│
├── apps/                       # Applications built with Mycorrhiza
│   ├── studio/                # Visual graph editor
│   │   ├── main.py
│   │   ├── screens/
│   │   └── ...
│   │
│   └── prediction-tracker/    # Prediction tracking system
│       ├── README.md          # Consolidated guide
│       ├── service/           # HTTP API (was prediction_service/)
│       │   ├── api.py
│       │   ├── storage.py
│       │   └── models.py
│       ├── client/            # Client implementations
│       │   ├── cli.py         # Unified CLI (was predict.py)
│       │   └── mcp/           # MCP server (was mcp_server/)
│       │       └── server.py
│       ├── legacy/            # Backward compatibility
│       │   ├── database.py    # Old TrackerDB
│       │   ├── bridge.py      # World sync
│       │   └── metrics.py     # Pure functions
│       ├── tests/             # Feature-specific tests
│       │   └── test_tracker.py
│       └── examples/
│           └── integrated_prediction_demo.py
│
├── tests/                      # Integration & core tests
│   ├── test_category.py
│   ├── test_graph.py
│   ├── test_property.py
│   └── integration/
│       ├── test_e2e_multi_agent_learning.py
│       └── test_e2e_prediction_cycle.py
│
├── examples/                   # Language examples
│   ├── capacity_demo.py
│   ├── clean_architecture_demo.py
│   └── visual_graph_editor.py
│
├── experiments/                # Research experiments
│   ├── README.md
│   ├── synthetic_agents.py
│   ├── lake-model/            # Consolidated from random_shit
│   │   ├── democratic_fishing_test.py
│   │   ├── simple_lake_test.py
│   │   ├── quick_test_fishing.py
│   │   └── quick_test_fishing_v2.py
│   └── outputs/               # Experiment results
│       └── .gitkeep
│
├── docs/                       # All documentation
│   ├── README.md              # Documentation index
│   ├── getting-started/
│   │   ├── README.md          # Entry point (was Start_Here.md)
│   │   └── tutorial.md
│   ├── architecture/
│   │   ├── overview.md        # From docs/ARCHITECTURE.md
│   │   ├── computational-foundation.md
│   │   ├── core-abstractions.md
│   │   └── design-patterns.md
│   ├── guides/
│   │   ├── building-protocols.md
│   │   ├── composition.md
│   │   └── jax-integration.md
│   ├── planning/              # From plans/
│   │   ├── context.md
│   │   ├── architecture.md
│   │   └── next-steps.md
│   ├── reports/               # Project reports
│   │   ├── completion-report.md
│   │   ├── service-refactor.md
│   │   └── code-cleanup.md
│   ├── design/                # UI/design assets (was UI Col-Int-Lib)
│   │   ├── ci-lab-spec.pdf
│   │   └── screenshots/
│   │       ├── graph-initialization.png
│   │       └── ...
│   └── manifesto.md           # Philosophy
│
├── research/                   # Research materials
│   ├── README.md
│   ├── papers/                # (was Related Papers/)
│   │   ├── predictive-governance.pdf
│   │   └── spectral-collective-inference.pdf
│   ├── thesis/
│   │   ├── context.md
│   │   └── visualizer-spec.pdf
│   └── notes/
│       ├── jax-parallelization-results.md
│       ├── lake-model-summary.md
│       └── quick-reference.md
│
├── scripts/                    # Utility scripts
│   └── demo_tracker.py        # (was root-level)
│
├── data/                       # Runtime data (gitignored)
│   └── .gitkeep
│
└── .claude/                    # Claude Code config
    ├── CURRENT_PLAN.md
    ├── SESSION_LOG.md
    └── ...
```

### Key Changes

**1. Create `apps/` directory**
- **Move** `studio/` → `apps/studio/`
- **Consolidate** prediction tracker:
  - `prediction_service/` → `apps/prediction-tracker/service/`
  - `predict.py` → `apps/prediction-tracker/client/cli.py`
  - `mcp_server/` → `apps/prediction-tracker/client/mcp/`
  - `tracker/` → `apps/prediction-tracker/legacy/`
  - `test_tracker.py` → `apps/prediction-tracker/tests/`
  - `examples/integrated_prediction_demo.py` → `apps/prediction-tracker/examples/`
  - Consolidate docs into single `apps/prediction-tracker/README.md`

**Rationale:** Applications are distinct products built with Mycorrhiza. Grouping makes it clear what's framework vs application. Prediction tracker is scattered across 6 locations - consolidating creates clear ownership.

**2. Reorganize `experiments/`**
- **Move** `random_shit/` contents → `experiments/lake-model/`
- **Rename** `experiment_outputs/` → `experiments/outputs/`
- **Move** experimental notes to `research/notes/`

**Rationale:** "random_shit" is unprofessional and unclear. Lake model experiments are legitimate research. Consolidating makes experimental work discoverable.

**3. Consolidate `docs/`**
- **Move** root-level docs → `docs/` subdirectories by purpose
- **Merge** `plans/` → `docs/planning/`
- **Move** `UI Col-Int-Lib/` → `docs/design/`
- **Create** `docs/reports/` for project reports
- **Keep** only `README.md` and `CLAUDE.md` at root

**Rationale:** 8 root-level docs create confusion. Organized hierarchy makes documentation discoverable. Single README.md as clear entry point.

**4. Create `research/`**
- **Move** `Related Papers/` → `research/papers/`
- **Move** `Building the Collective Intelligence Visualizer.pdf` → `research/thesis/`
- **Move** research notes from `random_shit/` → `research/notes/`

**Rationale:** Thesis context is important. Separating research from operational docs creates clarity.

**5. Cleanup root level**
- **Move** `demo_tracker.py` → `scripts/`
- **Delete** `NUL` (Windows artifact)
- **Delete** `__init__.py` (not a package)
- **Move** `tracker.db` → `data/` and add to `.gitignore`
- Result: 2 docs (README, CLAUDE) + config files + core directories

**Rationale:** Clean root level aids navigation. Only entry points and essential config visible.

**6. Reorganize `tests/`**
- **Keep** core tests at top level
- **Create** `tests/integration/` for E2E tests
- **Move** feature tests to feature directories

**Rationale:** Core language tests separate from integration. Feature tests near feature code.

### Naming Conventions

**Directories:**
- Use kebab-case: `prediction-tracker`, `lake-model`
- Plural for collections: `apps`, `experiments`, `tests`
- Singular for single-purpose: `core`, `engine`, `execution`
- No spaces, no underscores (except Python modules)

**Files:**
- Python: snake_case (PEP 8)
- Markdown: kebab-case
- Config: Standard names (requirements.txt, pyproject.toml)

**Special Cases:**
- Legacy Python modules: Keep snake_case (mcp_server → mcp in client/mcp/)
- README.md: Always capitalized
- .dotfiles: Standard conventions

---

## Migration Plan

### Phase 1: Cleanup (Low Risk)

**Delete unnecessary files:**
- [ ] `NUL` - Windows artifact
- [ ] `__init__.py` - Empty root-level file
- [ ] `experiment_outputs/TimelinePortfolioDemocracySuite_20250603_091409/` - Old output

**Gitignore runtime data:**
- [ ] Move `tracker.db` → `data/tracker.db`
- [ ] Add `data/` to `.gitignore`

**Archive old experiment outputs:**
- [ ] Create `experiments/outputs/` with `.gitkeep`
- [ ] Document that outputs are gitignored

### Phase 2: Restructure (Medium Risk)

**2.1: Create new directories**
```bash
mkdir -p apps/studio
mkdir -p apps/prediction-tracker/{service,client/{cli,mcp},legacy,tests,examples}
mkdir -p experiments/{lake-model,outputs}
mkdir -p research/{papers,thesis,notes}
mkdir -p docs/{getting-started,architecture,guides,planning,reports,design/screenshots}
mkdir -p scripts
mkdir -p data
```

**2.2: Move applications**
```bash
# Studio (simple move)
git mv studio/* apps/studio/
rmdir studio

# Prediction tracker (complex consolidation)
git mv prediction_service apps/prediction-tracker/service
git mv predict.py apps/prediction-tracker/client/cli.py
git mv mcp_server apps/prediction-tracker/client/mcp
git mv tracker apps/prediction-tracker/legacy
git mv test_tracker.py apps/prediction-tracker/tests/
git mv examples/integrated_prediction_demo.py apps/prediction-tracker/examples/

# Consolidate docs
# (Create single README in apps/prediction-tracker/)
```

**2.3: Move experiments**
```bash
# Lake model experiments
git mv random_shit/democratic_fishing_test.py experiments/lake-model/
git mv random_shit/simple_lake_test.py experiments/lake-model/
git mv random_shit/quick_test_fishing*.py experiments/lake-model/
git mv random_shit/*.md research/notes/

# Clean up random_shit
# (After verifying nothing important left)
```

**2.4: Move research materials**
```bash
git mv "Related Papers"/*.pdf research/papers/
git mv "Building the Collective Intelligence Visualizer.pdf" research/thesis/visualizer-spec.pdf
git mv "UI Col-Int-Lib"/*.pdf docs/design/
git mv "UI Col-Int-Lib"/*.png docs/design/screenshots/
```

**2.5: Organize documentation**
```bash
# Getting started
git mv Start_Here.md docs/getting-started/README.md

# Architecture (from docs/)
git mv docs/ARCHITECTURE.md docs/architecture/overview.md
git mv docs/COMPUTATIONAL_FOUNDATION.md docs/architecture/computational-foundation.md
git mv docs/CORE_ABSTRACTIONS.md docs/architecture/core-abstractions.md
git mv docs/DESIGN_PATTERNS.md docs/architecture/design-patterns.md

# Planning (from plans/)
git mv plans/CONTEXT.md docs/planning/context.md
git mv plans/ARCHITECTURE.md docs/planning/architecture.md
git mv plans/NEXT_STEPS.md docs/planning/next-steps.md

# Reports
git mv COMPLETION_REPORT.md docs/reports/completion-report.md
git mv DONE_SERVICE_REFACTOR.md docs/reports/service-refactor.md
git mv CODE_CLEANUP_REPORT.md docs/reports/code-cleanup.md

# Philosophy
git mv Manifesto.md docs/manifesto.md

# Status and user story
git mv STATUS.md docs/status.md
git mv USER_STORY.md docs/user-story.md
```

**2.6: Move tests**
```bash
git mv tests/test_e2e_*.py tests/integration/
```

**2.7: Move scripts**
```bash
git mv demo_tracker.py scripts/
```

### Phase 3: Update References (High Risk)

**3.1: Update imports in prediction tracker**
```python
# In apps/prediction-tracker/client/cli.py
# OLD: from prediction_service import ...
# NEW: from ..service import ...

# In apps/prediction-tracker/client/mcp/server.py
# OLD: from prediction_service import ...
# NEW: from ...service import ...

# In apps/prediction-tracker/legacy/database.py
# OLD: from tracker.metrics import ...
# NEW: from .metrics import ...
```

**3.2: Update studio imports**
```python
# In apps/studio/main.py
# OLD: from studio.screens import ...
# NEW: from .screens import ...

# In apps/studio/screens/prediction_dashboard.py
# OLD: from tracker.database import TrackerDB
# NEW: from ...prediction-tracker.legacy.database import TrackerDB
```

**3.3: Update service startup**
```python
# apps/prediction-tracker/service/__main__.py
# Verify import paths work
```

**3.4: Update documentation links**
- [ ] Fix all relative links in moved markdown files
- [ ] Update README.md with new structure
- [ ] Update CLAUDE.md with new paths

**3.5: Update config files**
```bash
# pytest.ini - Update test paths
# mcp_config.json - Update server path
# requirements.txt - No changes needed
```

### Phase 4: Documentation & Validation

**4.1: Create navigation READMEs**

**`docs/README.md`:**
```markdown
# Mycorrhiza Documentation

## Getting Started
- [Quick Start](getting-started/README.md) - 30-minute tutorial
- [README](../README.md) - Project overview

## Architecture
- [Overview](architecture/overview.md)
- [Computational Foundation](architecture/computational-foundation.md)
- [Core Abstractions](architecture/core-abstractions.md)

## Applications
- [Prediction Tracker](../apps/prediction-tracker/README.md)
- [Studio Visualizer](../apps/studio/README.md)

## Research
- [Papers](../research/papers/)
- [Thesis Context](../research/thesis/)
```

**`apps/README.md`:**
```markdown
# Mycorrhiza Applications

Applications built with the Mycorrhiza collective intelligence framework.

## Prediction Tracker

Service-first prediction tracking system for measuring calibration.

**Location:** `apps/prediction-tracker/`
**Documentation:** [README](prediction-tracker/README.md)

**Quick start:**
```bash
cd apps/prediction-tracker
python -m service          # Start API
python client/cli.py --help  # Use CLI
```

## Studio Visualizer

Interactive graph editor and simulation visualizer.

**Location:** `apps/studio/`

**Quick start:**
```bash
cd apps/studio
python main.py
```
```

**`apps/prediction-tracker/README.md`:**
(Consolidate PREDICTION_TRACKER.md + service README + tracker README)

**`experiments/README.md`:**
```markdown
# Experiments

Research experiments and exploratory code.

## Lake Model

Tragedy of the commons simulations with democratic mechanisms.

**Location:** `experiments/lake-model/`

Includes:
- Democratic fishing tests
- Simple lake model
- Variants and iterations

## Running Experiments

```bash
cd experiments/lake-model
python democratic_fishing_test.py
python simple_lake_test.py
```

## Outputs

Experiment outputs are saved to `experiments/outputs/` (gitignored).
```

**`research/README.md`:**
```markdown
# Research Materials

## Papers

Foundational papers on collective intelligence and predictive governance.

- [Predictive Governance Model](papers/predictive-governance.pdf)
- [Spectral Collective Inference](papers/spectral-collective-inference.pdf)

## Thesis

**Title:** "Red Teaming Democracy: LLM Simulation of Institutional Resilience"
**Author:** Jonas Hallgren
**Institution:** Uppsala University
**Year:** 2026

**Documents:**
- [Visualizer Specification](thesis/visualizer-spec.pdf)
- [Context](../docs/planning/context.md)

## Notes

Research notes and findings:
- [JAX Parallelization Results](notes/jax-parallelization-results.md)
- [Lake Model Summary](notes/lake-model-summary.md)
```

**4.2: Update root README.md**

Add directory structure section:
```markdown
## Repository Structure

```
mycorrhiza/
├── core/              # Language primitives (GraphState, transforms)
├── engine/            # Protocol library (transformations, agents, environments)
├── execution/         # Execution strategies (parallel, distributed)
├── apps/              # Applications built with Mycorrhiza
│   ├── studio/        # Visual graph editor
│   └── prediction-tracker/  # Prediction tracking system
├── experiments/       # Research experiments
├── tests/             # Core tests
├── examples/          # Language examples
├── docs/              # Documentation
├── research/          # Papers, thesis, notes
└── scripts/           # Utility scripts
```

See [CLAUDE.md](CLAUDE.md) for development guidance.
```

**4.3: Verify everything works**

```bash
# Test imports
python -c "from core.graph import GraphState; print('Core OK')"
python -c "from apps.prediction-tracker.service.api import app; print('Service OK')"

# Run tests
cd tests
python test_graph.py
python test_category.py
python integration/test_e2e_prediction_cycle.py

# Run prediction tracker tests
cd ../apps/prediction-tracker/tests
python test_tracker.py

# Start services
cd ../service
python -m __main__  # Should start on localhost:8000

# Test CLI
cd ../client
python cli.py --help

# Start studio
cd ../../studio
python main.py
```

**4.4: Verify documentation**

```bash
# Check for broken links
grep -r "](/" docs/ | grep -v ".git"

# Verify all READMEs exist
find . -type d -name "apps" -o -name "docs" -o -name "research" -o -name "experiments" | while read dir; do
  if [ ! -f "$dir/README.md" ]; then
    echo "Missing README: $dir"
  fi
done
```

**4.5: Update .gitignore**

```
# Add to .gitignore
data/
experiments/outputs/
*.db
__pycache__/
*.pyc
.DS_Store
Thumbs.db
```

---

## Risks & Mitigations

### Risk 1: Import breaks in prediction tracker

**Impact:** Service won't start, CLI won't work
**Mitigation:**
- Update imports systematically
- Test after each change
- Keep old structure until all references updated
- Document import patterns in README

### Risk 2: Studio can't find prediction tracker

**Impact:** Dashboard screen fails
**Mitigation:**
- Update relative imports
- Add apps/ to Python path if needed
- Test dashboard screen specifically
- Provide migration guide for imports

### Risk 3: MCP server path changes

**Impact:** MCP integration breaks
**Mitigation:**
- Update mcp_config.json with new path
- Test MCP server startup
- Document new path in prediction tracker README

### Risk 4: Experiment scripts can't find modules

**Impact:** Research experiments fail
**Mitigation:**
- Keep experiments/ at root (already is)
- Add parent directory to sys.path if needed
- Document import patterns

### Risk 5: Documentation links break

**Impact:** Navigation between docs fails
**Mitigation:**
- Use relative links consistently
- Test links after move
- Create comprehensive index pages
- Add link checker to CI (future)

### Risk 6: Git history fragmentation

**Impact:** Harder to track file history
**Mitigation:**
- Use `git mv` for all moves (preserves history)
- Document major moves in commit message
- Tag commit before restructure
- Keep this report for reference

---

## Validation Checklist

### Builds & Tests
- [ ] All core tests pass (`tests/test_*.py`)
- [ ] Integration tests pass (`tests/integration/`)
- [ ] Prediction tracker tests pass
- [ ] Service starts successfully
- [ ] CLI commands work
- [ ] MCP server connects
- [ ] Studio launches
- [ ] Studio dashboard works

### Documentation
- [ ] All relative links work
- [ ] No broken markdown references
- [ ] README.md updated with structure
- [ ] CLAUDE.md updated with paths
- [ ] All new directories have READMEs
- [ ] Migration guide complete

### Structure
- [ ] No orphaned files
- [ ] No empty directories (except .gitkeep)
- [ ] Naming is consistent
- [ ] Max depth reasonable (≤4 levels)
- [ ] Root level clean (≤10 items)
- [ ] No duplicate files

### Functionality
- [ ] Prediction service API accessible
- [ ] CLI can make/resolve predictions
- [ ] Studio can visualize graphs
- [ ] Experiments can run
- [ ] Examples work
- [ ] Demo scripts work

---

## Before/After Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Max directory depth | 4 | 4 | No change |
| Root-level items | 31 | 12 | -19 |
| Documentation files | 35 | 35 | 0 (reorganized) |
| Directories with unclear names | 3 | 0 | -3 |
| Files in wrong locations | 11 | 0 | -11 |
| Naming patterns | 3+ | 1 | Standardized |
| Application directories | 2 scattered | 1 consolidated | Simplified |
| Documentation hierarchy levels | 2 | 4 | More organized |

---

## Implementation Timeline

**Estimated time:** 3-4 hours

**Phase 1 (30 min):**
- Delete artifacts
- Update .gitignore
- Create directory structure

**Phase 2 (90 min):**
- Move files systematically
- Test after each major move
- Commit frequently

**Phase 3 (60 min):**
- Update all imports
- Fix config files
- Update documentation links

**Phase 4 (30 min):**
- Create READMEs
- Run full test suite
- Verify all functionality

---

## Documentation Created

After reorganization, create:

- [x] `DIRECTORY_ORGANIZATION_REPORT.md` - This document
- [ ] `docs/README.md` - Documentation index
- [ ] `apps/README.md` - Applications overview
- [ ] `apps/prediction-tracker/README.md` - Consolidated tracker docs
- [ ] `experiments/README.md` - Experiments guide
- [ ] `research/README.md` - Research materials index
- [ ] Updated `README.md` - With new structure section
- [ ] Updated `CLAUDE.md` - With new file paths

---

## Success Criteria

✅ **Discoverability:** New contributor can find files in < 3 clicks
✅ **Consistency:** All naming follows single pattern
✅ **Clarity:** Purpose of each directory is obvious
✅ **Functionality:** All tests pass, all features work
✅ **Documentation:** Clear entry points and navigation
✅ **Maintainability:** Structure scales with growth

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Create backup** / tag current state
3. **Execute Phase 1** (low risk cleanup)
4. **Execute Phase 2** (restructure, test frequently)
5. **Execute Phase 3** (update references)
6. **Execute Phase 4** (documentation & validation)
7. **Commit with detailed message** explaining restructure
8. **Update any CI/CD** with new paths

---

## Notes

### Why This Structure?

**Apps-based organization:**
- Clear separation: framework (core/engine) vs applications (studio, prediction tracker)
- Feature ownership: All prediction tracker code in one place
- Independent development: Apps can evolve separately
- Scalability: Easy to add new applications

**Research separation:**
- Academic context clear and accessible
- Papers grouped with thesis materials
- Experiment code separate from production

**Documentation hierarchy:**
- Multiple audiences: beginners, developers, researchers
- Progressive disclosure: README → guides → deep docs
- Clear navigation: Index pages at each level

### What This Achieves

1. **Professional appearance** - No "random_shit", spaces in names
2. **Clear hierarchy** - Purpose obvious from path
3. **Feature consolidation** - Prediction tracker unified
4. **Discoverability** - Related files grouped together
5. **Scalability** - Structure supports growth
6. **Maintainability** - Consistent patterns throughout

### Potential Future Improvements

- **Package structure:** Convert to proper Python package with `pyproject.toml`
- **CLI installation:** Make `predict` a globally installable command
- **Plugin system:** Apps register as plugins to core
- **Monorepo tools:** Consider tools like `nx` for multi-app management
- **Documentation site:** Deploy docs/ as static site

---

**Last Updated:** 2026-02-04
**Status:** Proposed - Awaiting Implementation
**Estimated Implementation Time:** 3-4 hours
