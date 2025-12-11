# Prerequisite Changes for CodeRabbit Feature Parity

This document outlines all prerequisite changes that must be made before implementing the features outlined in TODO.md.

## Analysis Summary

After analyzing the codebase, I've identified the following components that exist and will be leveraged:

### Existing Infrastructure ✅
- **Module System**: Well-organized with tools/, git_providers/, settings/, algo/
- **Tool Pattern**: All tools inherit async run() pattern and use command2class mapping
- **Configuration**: Dynaconf-based TOML configuration with hierarchical merging
- **Dependencies**: FastAPI (0.118.0) and uvicorn (0.22.0) already present for dashboard feature
- **Git Provider Abstraction**: Abstract GitProvider base class with 13 implementations
- **Types System**: Basic dataclasses in pr_agent/algo/types.py
- **Testing**: pytest-based with coverage support

## Prerequisite Changes Required

### 1. New Module Directories

Create the following module directories with proper Python package structure:

```
pr_agent/
├── checks/          # Feature 1: Pre-Merge Check Engine
│   ├── __init__.py
│   ├── base_check.py
│   ├── check_context.py
│   ├── check_result.py
│   └── orchestrator.py
├── state/           # Feature 4: State Store & Finding Tracking
│   ├── __init__.py
│   ├── state_store.py
│   ├── pr_state.py
│   └── finding.py
├── diagrams/        # Feature 3: Expanded Diagram Generation
│   ├── __init__.py
│   ├── base_diagram.py
│   └── diagram_types.py
├── feedback/        # Feature 6: Learning from Feedback
│   ├── __init__.py
│   ├── feedback_logger.py
│   ├── feedback_event.py
│   └── preference.py
└── dashboard/       # Feature 7: Org-Level Dashboard
    ├── __init__.py
    ├── api/
    │   ├── __init__.py
    │   └── routes.py
    └── metrics/
        ├── __init__.py
        └── collector.py
```

### 2. Dependency Additions

Add to `requirements.txt`:
- **pathspec** (BSD License) - For glob pattern matching in path-scoped configs and checks
- **aiosqlite** (MIT License) - For async SQLite operations in state store and dashboard

Both dependencies are AGPL-3.0 compatible with permissive licenses.

### 3. Base Classes and Infrastructure

#### 3.1 Checks Module (`pr_agent/checks/`)

**base_check.py** - Abstract base class for all checks:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal
from pr_agent.checks.check_context import CheckContext
from pr_agent.checks.check_result import CheckResult

class BaseCheck(ABC):
    """Base class for all pre-merge checks"""

    def __init__(self, name: str, description: str, mode: Literal["advisory", "blocking"]):
        self.name = name
        self.description = description
        self.mode = mode

    @abstractmethod
    async def run(self, context: CheckContext) -> CheckResult:
        """Execute the check and return results"""
        pass
```

**check_context.py** - Context data for check execution
**check_result.py** - Result dataclass for check outputs
**orchestrator.py** - Manages check execution and aggregation

#### 3.2 State Module (`pr_agent/state/`)

**state_store.py** - Abstract state storage interface:
```python
from abc import ABC, abstractmethod
from pr_agent.state.pr_state import PRState

class StateStore(ABC):
    """Abstract base class for state persistence"""

    @abstractmethod
    async def load(self, pr_id: str) -> PRState | None:
        """Load PR state from storage"""
        pass

    @abstractmethod
    async def save(self, state: PRState) -> None:
        """Save PR state to storage"""
        pass

    @abstractmethod
    async def delete(self, pr_id: str) -> None:
        """Delete PR state from storage"""
        pass
```

**pr_state.py** - PRState dataclass
**finding.py** - Finding dataclass for tracking review findings

#### 3.3 Diagrams Module (`pr_agent/diagrams/`)

**base_diagram.py** - Abstract diagram generator
**diagram_types.py** - Enum for diagram types (CHANGE_FLOW, COMPONENT, DATA_FLOW, etc.)

#### 3.4 Feedback Module (`pr_agent/feedback/`)

**feedback_logger.py** - Feedback event logging
**feedback_event.py** - Feedback event types enum
**preference.py** - Preference model dataclass

#### 3.5 Dashboard Module (`pr_agent/dashboard/`)

**metrics/collector.py** - Metrics collection class
**api/routes.py** - FastAPI route definitions

### 4. Configuration Schema Extensions

Add new sections to `pr_agent/settings/configuration.toml`:

```toml
# Feature 1: Pre-Merge Checks
[checks]
enable_auto_checks = false  # Disabled by default (opt-in)
default_mode = "advisory"
parallel_execution = true

# Feature 2: Path-Scoped Configuration
[config]
path_config_enabled = false  # Disabled by default (opt-in)
path_config_max_depth = 5
path_config_allowed_overrides = [
    "pr_reviewer.extra_instructions",
    "pr_reviewer.num_max_findings",
    "pr_code_suggestions.extra_instructions"
]

# Feature 3: Diagram Generation (extends pr_description)
[pr_description]
enable_pr_diagram = true  # Already exists
diagram_types = ["change_flow"]  # Start with existing type
diagram_max_nodes = 20
diagram_collapse_threshold = 10

# Feature 4: Incremental Review
[incremental_review]
enabled = false  # Disabled by default (opt-in)
state_store = "file"
state_file_path = ".pr_agent_state/"
persist_resolved_findings = true
finding_expiry_days = 30

# Feature 5: Conversational PR
[pr_questions]
use_conversation_history = false  # Disabled by default (opt-in)
max_history_messages = 10
max_history_tokens = 4000
enable_follow_up_suggestions = false
enable_threaded_responses = true

# Feature 6: Feedback Learning
[feedback]
enabled = false  # Disabled by default (opt-in)
storage = "local"
storage_path = ".pr_agent_feedback/"
aggregate_to_org = false
min_samples_for_preference = 5

[feedback.privacy]
anonymize_code = true
retention_days = 90
allow_export = true

# Feature 7: Dashboard
[dashboard]
enabled = false  # Disabled by default (opt-in)
database_url = "sqlite:///.pr_agent_metrics.db"
api_port = 8080

[dashboard.auth]
enabled = false
method = "basic"
```

### 5. Prompt Files

Create initial prompt files in `pr_agent/settings/`:

- **pr_checks_prompts.toml** - Prompts for free-text rule evaluation
- **pr_diagram_prompts.toml** - Prompts for component/data-flow diagram generation (extend existing)
- **pr_explain_prompts.toml** - Prompts for the new /explain command

### 6. Git Provider Extensions (Future)

Note: GitProvider base class will need extension methods for check status reporting (Feature 1), but this will be done when implementing Feature 1, not as a prerequisite.

## Implementation Principles

All prerequisite changes follow these principles:

1. **Opt-in by Default**: All new features disabled in default config (backward compatible)
2. **AGPL-3.0 Compliant**: All dependencies have compatible licenses
3. **Async-First**: All new code uses async/await patterns
4. **Minimal**: Only create infrastructure needed for features
5. **Documented**: Each module has clear docstrings
6. **Tested**: Each base class comes with unit tests

## Recommended Prerequisite Order

1. Add dependencies to requirements.txt
2. Create module directory structures with __init__.py files
3. Implement base classes and dataclasses
4. Add configuration schema sections
5. Create prompt files
6. Write unit tests for base infrastructure
7. Commit all prerequisite changes

## Verification Checklist

Before starting feature implementation:

- [ ] All new modules can be imported successfully
- [ ] All new dependencies install without conflicts
- [ ] Configuration loads without errors
- [ ] Unit tests pass for all base classes
- [ ] No breaking changes to existing functionality
- [ ] Ruff linting passes
- [ ] All files have AGPL-3.0 license headers

## Next Steps

After completing these prerequisite changes, implement features in this order (per TODO.md Phase 1-5):

1. **Feature 2**: Path-Scoped Configuration (Foundation)
2. **Feature 4.1-4.2**: State Store & Finding Tracking (Core Infrastructure)
3. **Feature 1**: Pre-Merge Check Engine
4. **Feature 4.3-4.6**: Complete Incremental Review
5. **Feature 3**: Expanded Diagrams
6. **Feature 5**: Conversational PR
7. **Feature 6**: Learning from Feedback
8. **Feature 7**: Dashboard
9. **Feature 8**: VS Code Extension (separate repo)
