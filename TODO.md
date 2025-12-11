# PR-Agent Upgrade Plan: CodeRabbit Feature Parity

> **Status**: PLANNING PHASE - No implementation changes yet
> **License**: All changes must remain AGPL-3.0 compliant
> **Goal**: Extend PR-Agent to reach feature parity with CodeRabbit while remaining fully open source

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Feature 1: Native Pre-Merge Check Engine](#feature-1-native-pre-merge-check-engine)
3. [Feature 2: Path-Scoped Configuration System](#feature-2-path-scoped-configuration-system)
4. [Feature 3: Expanded Diagram Generation](#feature-3-expanded-diagram-generation)
5. [Feature 4: Improved Incremental Review Engine](#feature-4-improved-incremental-review-engine)
6. [Feature 5: Conversational PR Interaction](#feature-5-conversational-pr-interaction)
7. [Feature 6: Learning From Feedback](#feature-6-learning-from-feedback)
8. [Feature 7: Optional Org-Level Dashboard](#feature-7-optional-org-level-dashboard)
9. [Feature 8: Official VS Code Extension](#feature-8-official-vs-code-extension)
10. [Open Source Requirements](#open-source-requirements)
11. [Dependencies and Recommended Order](#dependencies-and-recommended-order)
12. [Testing Strategy](#testing-strategy)
13. [Documentation Plan](#documentation-plan)
14. [Migration Guide](#migration-guide)

---

## Executive Summary

This document outlines a comprehensive plan to extend PR-Agent with features that achieve parity with CodeRabbit's key capabilities. The implementation is divided into 8 major features, each with detailed tasks, design decisions, and dependencies.

### Current Architecture Overview

PR-Agent uses a modular architecture:
- **Tools**: Plugin-style classes in `pr_agent/tools/` (PRReviewer, PRDescription, etc.)
- **Providers**: Abstract `GitProvider` base with implementations for GitHub, GitLab, Bitbucket, Azure DevOps, etc.
- **AI Handlers**: LiteLLM-based supporting 40+ models including local options (Ollama)
- **Configuration**: TOML-based via Dynaconf with secure custom loader (`custom_merge_loader.py`)
- **Entry Points**: CLI (`cli.py`), Agent (`agent/pr_agent.py`), Webhooks (`servers/`)

---

## Feature 1: Native Pre-Merge Check Engine

### Overview
Create a new module for configurable named checks that can run as advisory or blocking gates before merge. This enables teams to enforce custom rules beyond standard code review.

### Tasks

#### 1.1 Core Check Framework
- [ ] **1.1.1** Create new module `pr_agent/checks/` with base check infrastructure
- [ ] **1.1.2** Define `BaseCheck` abstract class with:
  - `name: str` - Unique identifier for the check
  - `description: str` - Human-readable description
  - `mode: Literal["advisory", "blocking"]` - Check behavior
  - `async def run(context: CheckContext) -> CheckResult`
- [ ] **1.1.3** Create `CheckContext` dataclass containing:
  - PR metadata (title, description, author, labels)
  - Diff information (files changed, patches)
  - Git provider instance
  - Configuration settings
- [ ] **1.1.4** Create `CheckResult` dataclass with:
  - `passed: bool`
  - `message: str`
  - `details: list[CheckDetail]`
  - `severity: Literal["info", "warning", "error"]`

#### 1.2 Built-in Check Types
- [ ] **1.2.1** Implement `FreeTextRuleCheck` - AI-powered check with custom prompt
  ```python
  # Example config:
  # [checks.require_tests]
  # type = "free_text"
  # rule = "All new functions must have corresponding unit tests"
  # mode = "blocking"
  ```
- [ ] **1.2.2** Implement `PatternCheck` - Regex-based content matching
- [ ] **1.2.3** Implement `FileSizeCheck` - Enforce max file/PR size limits
- [ ] **1.2.4** Implement `RequiredFilesCheck` - Ensure certain files are modified together
- [ ] **1.2.5** Implement `ForbiddenPatternsCheck` - Block commits with secrets/sensitive data

#### 1.3 Path-Aware Filters
- [ ] **1.3.1** Add `paths` filter to check configuration:
  ```toml
  [checks.frontend_lint]
  paths = ["src/frontend/**/*.tsx", "src/frontend/**/*.ts"]
  exclude_paths = ["**/*.test.ts"]
  ```
- [ ] **1.3.2** Implement glob-based path matching using `fnmatch` or `pathspec`
- [ ] **1.3.3** Support both include and exclude patterns
- [ ] **1.3.4** Add path-aware context to `CheckContext`

#### 1.4 Provider Integration for Check Status
- [ ] **1.4.1** Extend `GitProvider` base class with check status methods:
  ```python
  @abstractmethod
  async def create_check_run(self, name: str, status: str, conclusion: str, output: dict) -> str

  @abstractmethod
  async def update_check_run(self, check_id: str, status: str, conclusion: str, output: dict)
  ```
- [ ] **1.4.2** Implement for GitHub (using Checks API)
- [ ] **1.4.3** Implement for GitLab (using Pipeline/Commit Status API)
- [ ] **1.4.4** Implement for Bitbucket (using Build Status API)
- [ ] **1.4.5** Implement for Azure DevOps (using Status API)

#### 1.5 Check Orchestration
- [ ] **1.5.1** Create `CheckOrchestrator` class to manage check execution:
  - Load checks from configuration
  - Execute checks in parallel where possible
  - Aggregate results
  - Report status to git provider
- [ ] **1.5.2** Add `/checks` command to `command2class` mapping
- [ ] **1.5.3** Implement `PRChecks` tool class in `pr_agent/tools/pr_checks.py`
- [ ] **1.5.4** Add automatic check trigger on PR events (configurable)

#### 1.6 Blocking Behavior
- [ ] **1.6.1** Implement merge blocking via check status (GitHub: `failure` conclusion)
- [ ] **1.6.2** Add bypass mechanism for authorized users
- [ ] **1.6.3** Create summary comment with all check results
- [ ] **1.6.4** Support re-running checks via `/checks rerun`

### Design Decisions to Make
- **Check registration**: Dynamic discovery vs explicit configuration?
- **Check execution model**: Sequential with dependencies or fully parallel?
- **State storage**: How to track check history across PR updates?
- **Rate limiting**: How to prevent excessive AI calls for free-text rules?

### Configuration Schema
```toml
[checks]
enable_auto_checks = true
default_mode = "advisory"  # or "blocking"
parallel_execution = true

[checks.require_description]
type = "free_text"
rule = "PR description must explain the 'why' not just the 'what'"
mode = "advisory"
paths = ["**/*"]

[checks.no_console_logs]
type = "pattern"
pattern = "console\\.(log|debug|info)"
mode = "blocking"
paths = ["src/**/*.ts", "src/**/*.js"]
exclude_paths = ["**/*.test.*"]
message = "Remove console.log statements before merging"
```

---

## Feature 2: Path-Scoped Configuration System

### Overview
Enable multiple `.pr_agent.toml` files in subdirectories with path-based rule merging, allowing teams to customize behavior for different parts of a monorepo.

### Tasks

#### 2.1 Configuration Discovery
- [ ] **2.1.1** Create `ConfigDiscovery` class to find all `.pr_agent.toml` files:
  ```python
  async def discover_configs(repo_root: Path, changed_files: list[str]) -> list[ConfigFile]
  ```
- [ ] **2.1.2** Walk directory tree from changed file locations upward
- [ ] **2.1.3** Cache discovered configs per PR to avoid repeated filesystem access
- [ ] **2.1.4** Support alternative config names: `.pr_agent.toml`, `pr_agent.toml`, `.pr-agent.toml`

#### 2.2 Path-Based Merge Rules
- [ ] **2.2.1** Define merge semantics for nested configs:
  - **Override**: Child completely replaces parent value
  - **Extend**: Child adds to parent list/dict
  - **Inherit**: Child inherits parent if not specified
- [ ] **2.2.2** Implement `ConfigMerger` class with depth-aware merging
- [ ] **2.2.3** Add `_merge_strategy` directive support in config:
  ```toml
  [pr_reviewer]
  _merge_strategy = "extend"  # or "override", "inherit"
  extra_instructions = "Focus on performance for this module"
  ```
- [ ] **2.2.4** Support explicit path scopes in root config:
  ```toml
  [[path_overrides]]
  paths = ["packages/frontend/**"]
  [path_overrides.pr_reviewer]
  extra_instructions = "Check for React best practices"
  ```

#### 2.3 Security Hardening
- [ ] **2.3.1** Extend `validate_file_security()` to validate all discovered configs
- [ ] **2.3.2** Add maximum depth limit for config search (default: 5 levels)
- [ ] **2.3.3** Restrict which settings can be overridden at subdirectory level:
  ```toml
  [config]
  allow_subdirectory_overrides = ["extra_instructions", "num_max_findings"]
  deny_subdirectory_overrides = ["model", "api_key"]
  ```
- [ ] **2.3.4** Log all config merges for audit trail

#### 2.4 Per-File Configuration Resolution
- [ ] **2.4.1** Create `ConfigResolver` to get effective config for a specific file:
  ```python
  def get_config_for_file(file_path: str) -> Settings
  ```
- [ ] **2.4.2** Integrate with `PRReviewer` to use per-file instructions
- [ ] **2.4.3** Integrate with `PRCodeSuggestions` for path-aware suggestions
- [ ] **2.4.4** Add config info to PR comments showing which config applied

#### 2.5 Configuration Validation
- [ ] **2.5.1** Add `/config validate` subcommand to check all configs
- [ ] **2.5.2** Report conflicts and merge issues
- [ ] **2.5.3** Show effective configuration per path

### Design Decisions to Make
- **Merge precedence**: Most specific wins or explicit override required?
- **Performance**: Eager vs lazy config loading?
- **Caching**: How long to cache resolved configs?
- **Conflict resolution**: Error on conflict or use defined precedence?

### Configuration Schema
```toml
# Root .pr_agent.toml
[config]
path_config_enabled = true
path_config_max_depth = 5
path_config_allowed_overrides = [
    "pr_reviewer.extra_instructions",
    "pr_reviewer.num_max_findings",
    "pr_code_suggestions.extra_instructions"
]

# packages/backend/.pr_agent.toml
[pr_reviewer]
extra_instructions = "Focus on database query performance and security"

[pr_code_suggestions]
extra_instructions = "Suggest async/await patterns where applicable"
```

---

## Feature 3: Expanded Diagram Generation

### Overview
Extend the existing PR diagram feature (currently Mermaid-based in `/describe`) to support component diagrams and data-flow diagrams.

### Tasks

#### 3.1 Diagram Type Framework
- [ ] **3.1.1** Create `pr_agent/diagrams/` module with diagram base classes
- [ ] **3.1.2** Define `DiagramType` enum:
  - `CHANGE_FLOW` (existing)
  - `COMPONENT`
  - `DATA_FLOW`
  - `SEQUENCE`
  - `CLASS`
- [ ] **3.1.3** Create `BaseDiagramGenerator` abstract class
- [ ] **3.1.4** Refactor existing diagram logic from `PRDescription` into `ChangeFlowDiagram`

#### 3.2 Component Diagram Generator
- [ ] **3.2.1** Implement `ComponentDiagramGenerator`:
  - Analyze import/require statements
  - Identify module boundaries
  - Show dependencies between components
- [ ] **3.2.2** Create AI prompt for component extraction
- [ ] **3.2.3** Generate Mermaid `flowchart` or `C4Context` syntax
- [ ] **3.2.4** Support language-specific module detection:
  - Python: `import`, `from...import`
  - JavaScript/TypeScript: `import`, `require`
  - Go: `import`
  - Java: `import`
  - Rust: `use`, `mod`

#### 3.3 Data Flow Diagram Generator
- [ ] **3.3.1** Implement `DataFlowDiagramGenerator`:
  - Track data transformations in changed code
  - Identify inputs, outputs, and stores
- [ ] **3.3.2** Create AI prompt for data flow analysis
- [ ] **3.3.3** Generate Mermaid DFD-style diagrams
- [ ] **3.3.4** Highlight new vs existing data flows

#### 3.4 Integration with Existing Tools
- [ ] **3.4.1** Update `/describe` to support diagram type selection:
  ```
  /describe --diagram=component
  /describe --diagram=data_flow
  /describe --diagram=all
  ```
- [ ] **3.4.2** Add diagram section to `/review` output (optional)
- [ ] **3.4.3** Create dedicated `/diagram` command for standalone generation
- [ ] **3.4.4** Support multiple diagrams in single PR comment

#### 3.5 Diagram Configuration
- [ ] **3.5.1** Add configuration options:
  ```toml
  [pr_description]
  enable_pr_diagram = true
  diagram_types = ["change_flow", "component"]
  diagram_max_nodes = 20
  diagram_collapse_threshold = 10
  ```
- [ ] **3.5.2** Support diagram filtering by file type
- [ ] **3.5.3** Add detail level control (high/medium/low)

#### 3.6 Rendering Options
- [ ] **3.6.1** Ensure Mermaid compatibility with GitHub/GitLab/Bitbucket
- [ ] **3.6.2** Add fallback ASCII diagram option for limited markdown support
- [ ] **3.6.3** Support diagram image generation via external service (optional)

### Design Decisions to Make
- **Diagram complexity**: How to handle large PRs with many components?
- **Accuracy vs completeness**: Prioritize precision or coverage?
- **LLM usage**: Generate diagrams with LLM or use static analysis + LLM refinement?
- **Caching**: Cache diagram data for incremental updates?

---

## Feature 4: Improved Incremental Review Engine

### Overview
Enhance the existing `IncrementalPR` class to support PR-specific state storage, finding tracking, persistent comments, and review pause/resume functionality.

### Tasks

#### 4.1 PR-Specific State Store
- [ ] **4.1.1** Create `pr_agent/state/` module for state management
- [ ] **4.1.2** Define `PRState` dataclass:
  ```python
  @dataclass
  class PRState:
      pr_id: str
      provider: str
      findings: list[Finding]
      reviewed_commits: list[str]
      last_review_at: datetime
      paused: bool
      conversation_history: list[Message]
  ```
- [ ] **4.1.3** Implement `StateStore` abstract class with methods:
  - `async def load(pr_id: str) -> PRState | None`
  - `async def save(state: PRState)`
  - `async def delete(pr_id: str)`
- [ ] **4.1.4** Implement `FileStateStore` using JSON files (default)
- [ ] **4.1.5** Implement `GitNoteStateStore` using git notes (optional)
- [ ] **4.1.6** Implement `RedisStateStore` for distributed deployments (optional)

#### 4.2 Finding Tracking
- [ ] **4.2.1** Define `Finding` dataclass:
  ```python
  @dataclass
  class Finding:
      id: str  # Hash of location + content
      file_path: str
      line_range: tuple[int, int]
      category: str
      severity: str
      message: str
      suggestion: str | None
      status: Literal["open", "resolved", "invalidated", "dismissed"]
      created_at: datetime
      resolved_at: datetime | None
  ```
- [ ] **4.2.2** Implement finding deduplication logic
- [ ] **4.2.3** Implement finding invalidation when code changes
- [ ] **4.2.4** Track resolution via:
  - Code changes that address the finding
  - User dismissal
  - Suggestion application

#### 4.3 Persistent Comment System
- [ ] **4.3.1** Refactor to use single persistent comment per PR
- [ ] **4.3.2** Implement comment sections:
  - Summary
  - Active Findings
  - Resolved Findings (collapsible)
  - Review History
- [ ] **4.3.3** Update comment on each review instead of creating new
- [ ] **4.3.4** Add "Last updated" timestamp
- [ ] **4.3.5** Support expanding/collapsing sections via markdown details

#### 4.4 Review Lifecycle Commands
- [ ] **4.4.1** Implement `/pr_agent pause` command:
  - Stop automatic reviews
  - Store paused state
  - Add visual indicator to PR comment
- [ ] **4.4.2** Implement `/pr_agent resume` command:
  - Resume automatic reviews
  - Optionally trigger immediate review
- [ ] **4.4.3** Add pause/resume status to PR comment header
- [ ] **4.4.4** Support pause duration: `/pr_agent pause 24h`

#### 4.5 Combined Command Support
- [ ] **4.5.1** Parse multiple commands from single comment:
  ```
  /review
  /improve
  /describe
  ```
- [ ] **4.5.2** Execute commands in sequence with shared context
- [ ] **4.5.3** Aggregate results into single response comment
- [ ] **4.5.4** Handle command dependencies (e.g., review before improve)

#### 4.6 Incremental Diff Analysis
- [ ] **4.6.1** Extend `IncrementalPR` class with commit tracking
- [ ] **4.6.2** Only analyze new/modified hunks since last review
- [ ] **4.6.3** Carry forward findings for unchanged code
- [ ] **4.6.4** Re-validate existing findings against new code

### Design Decisions to Make
- **State storage location**: Filesystem, git notes, external database, or provider-specific (PR comments)?
- **Finding identity**: How to uniquely identify findings across code changes?
- **Conflict resolution**: What happens if state is corrupted or missing?
- **Performance**: Lazy loading vs eager state hydration?

### Configuration Schema
```toml
[incremental_review]
enabled = true
state_store = "file"  # "file", "git_notes", "redis"
state_file_path = ".pr_agent_state/"
persist_resolved_findings = true
finding_expiry_days = 30

[incremental_review.redis]
url = "redis://localhost:6379"
prefix = "pr_agent:"
```

---

## Feature 5: Conversational PR Interaction

### Overview
Enhance `/ask` with context history, threaded responses, and new commands for explaining specific comments.

### Tasks

#### 5.1 Context History for /ask
- [ ] **5.1.1** Extend `PRState` to include `conversation_history: list[Message]`
- [ ] **5.1.2** Store each Q&A exchange:
  ```python
  @dataclass
  class Message:
      role: Literal["user", "assistant"]
      content: str
      timestamp: datetime
      metadata: dict  # file context, line numbers, etc.
  ```
- [ ] **5.1.3** Include history in LLM prompt for `/ask`
- [ ] **5.1.4** Limit history to configurable token count
- [ ] **5.1.5** Support history reset: `/ask --clear-history`

#### 5.2 Threaded Conversation Responses
- [ ] **5.2.1** Detect when `/ask` is used in a reply thread
- [ ] **5.2.2** Include thread context in conversation
- [ ] **5.2.3** Reply in same thread instead of new comment
- [ ] **5.2.4** Support provider-specific threading:
  - GitHub: Review comment threads
  - GitLab: Discussion threads
  - Bitbucket: Inline comment threads

#### 5.3 Comment Explanation Commands
- [ ] **5.3.1** Implement `/explain` command for code selection:
  ```
  /explain lines 45-60 in src/utils.ts
  ```
- [ ] **5.3.2** Implement `/explain @comment-id` to explain a PR comment
- [ ] **5.3.3** Auto-detect context from thread when no arguments
- [ ] **5.3.4** Include surrounding code context for better explanations

#### 5.4 Smart Context Gathering
- [ ] **5.4.1** Extract mentioned file paths from user questions
- [ ] **5.4.2** Include relevant code snippets automatically
- [ ] **5.4.3** Reference previous findings when relevant
- [ ] **5.4.4** Link to related PR comments in responses

#### 5.5 Follow-up Suggestions
- [ ] **5.5.1** Generate follow-up question suggestions
- [ ] **5.5.2** Add "Ask more" button/link with pre-filled prompts
- [ ] **5.5.3** Track common question patterns per repo

### Design Decisions to Make
- **History scope**: Per-PR, per-user, or per-thread?
- **History persistence**: Store in state or reconstruct from comments?
- **Thread detection**: How to reliably detect thread context across providers?
- **Token management**: How to balance history length vs response quality?

### Configuration Schema
```toml
[pr_questions]
use_conversation_history = true
max_history_messages = 10
max_history_tokens = 4000
enable_follow_up_suggestions = true
enable_threaded_responses = true
```

---

## Feature 6: Learning From Feedback

### Overview
Log user actions and create a preference model to dynamically tune suggestions.

### Tasks

#### 6.1 Feedback Event Logging
- [ ] **6.1.1** Create `pr_agent/feedback/` module
- [ ] **6.1.2** Define feedback event types:
  ```python
  class FeedbackEvent(Enum):
      SUGGESTION_APPLIED = "suggestion_applied"
      SUGGESTION_DISMISSED = "suggestion_dismissed"
      COMMENT_RESOLVED = "comment_resolved"
      COMMENT_REPLIED = "comment_replied"
      THUMBS_UP = "thumbs_up"
      THUMBS_DOWN = "thumbs_down"
      FINDING_DISPUTED = "finding_disputed"
  ```
- [ ] **6.1.3** Implement `FeedbackLogger` class
- [ ] **6.1.4** Store events with context:
  - Suggestion content
  - Code context
  - User action
  - Timestamp
  - Repository/org metadata

#### 6.2 Feedback Detection
- [ ] **6.2.1** Detect applied suggestions via webhook events:
  - GitHub: `pull_request.synchronize` + diff analysis
  - GitLab: Pipeline events
- [ ] **6.2.2** Detect comment resolution events
- [ ] **6.2.3** Implement thumbs up/down buttons in suggestions (where supported)
- [ ] **6.2.4** Parse explicit feedback commands: `/feedback good|bad|ignore`

#### 6.3 Preference Model
- [ ] **6.3.1** Design preference schema:
  ```python
  @dataclass
  class Preference:
      pattern_type: str  # "suggestion_category", "code_pattern", etc.
      pattern: str
      weight: float  # -1.0 to 1.0
      confidence: float
      sample_count: int
  ```
- [ ] **6.3.2** Implement preference extraction from feedback events
- [ ] **6.3.3** Aggregate preferences at repository level
- [ ] **6.3.4** Support organization-level preference inheritance

#### 6.4 Dynamic Tuning
- [ ] **6.4.1** Inject preferences into LLM prompts:
  ```
  Based on team feedback:
  - Prefer functional patterns over class-based
  - Avoid suggestions about comment formatting
  - Prioritize security-related findings
  ```
- [ ] **6.4.2** Adjust suggestion scoring based on historical acceptance
- [ ] **6.4.3** Filter out suggestion types with low acceptance rate
- [ ] **6.4.4** Highlight suggestions matching high-acceptance patterns

#### 6.5 Privacy and Opt-out
- [ ] **6.5.1** Make feedback logging opt-in by default
- [ ] **6.5.2** Add per-repo and per-user opt-out
- [ ] **6.5.3** Support local-only feedback (no external storage)
- [ ] **6.5.4** Implement feedback data export/delete commands

#### 6.6 Feedback Analytics
- [ ] **6.6.1** Generate acceptance rate metrics
- [ ] **6.6.2** Identify most/least useful suggestion categories
- [ ] **6.6.3** Track improvement over time
- [ ] **6.6.4** Expose metrics via dashboard (see Feature 7)

### Design Decisions to Make
- **Storage**: Local files, git notes, or database?
- **Scope**: Repo-level, org-level, or user-level preferences?
- **Model complexity**: Simple heuristics vs ML-based?
- **Privacy**: How to anonymize feedback data?

### Configuration Schema
```toml
[feedback]
enabled = true
storage = "local"  # "local", "database"
storage_path = ".pr_agent_feedback/"
aggregate_to_org = false
min_samples_for_preference = 5

[feedback.privacy]
anonymize_code = true
retention_days = 90
allow_export = true
```

---

## Feature 7: Optional Org-Level Dashboard

### Overview
Create a minimal open-source dashboard showing trends, checks, and findings across repositories.

### Tasks

#### 7.1 Data Collection Layer
- [ ] **7.1.1** Create `pr_agent/dashboard/` module
- [ ] **7.1.2** Define metrics to collect:
  - PRs reviewed per day/week/month
  - Findings by category/severity
  - Check pass/fail rates
  - Average time to merge
  - Suggestion acceptance rate
- [ ] **7.1.3** Implement `MetricsCollector` class
- [ ] **7.1.4** Store metrics in lightweight database (SQLite default)

#### 7.2 Backend API (FastAPI)
- [ ] **7.2.1** Create `pr_agent/dashboard/api/` with FastAPI app
- [ ] **7.2.2** Implement endpoints:
  - `GET /api/metrics/overview` - Org summary
  - `GET /api/metrics/repos` - Per-repo metrics
  - `GET /api/metrics/trends` - Time-series data
  - `GET /api/checks` - Check results history
  - `GET /api/findings` - Finding trends
- [ ] **7.2.3** Add authentication middleware (optional)
- [ ] **7.2.4** Support filtering by date range, repo, team

#### 7.3 Static Frontend
- [ ] **7.3.1** Create simple static HTML/JS dashboard
- [ ] **7.3.2** Use lightweight charting library (Chart.js or similar)
- [ ] **7.3.3** Build pages:
  - Overview dashboard
  - Repository detail view
  - Check history
  - Feedback analytics
- [ ] **7.3.4** Support light/dark theme
- [ ] **7.3.5** Make responsive for mobile

#### 7.4 Deployment Options
- [ ] **7.4.1** Document standalone deployment (Docker)
- [ ] **7.4.2** Integrate as optional PR-Agent server endpoint
- [ ] **7.4.3** Support serverless deployment (Vercel, Netlify)
- [ ] **7.4.4** Add Kubernetes manifests

#### 7.5 Data Export
- [ ] **7.5.1** CSV export for all metrics
- [ ] **7.5.2** JSON API for integration with external tools
- [ ] **7.5.3** Webhook notifications for threshold breaches

### Design Decisions to Make
- **Database**: SQLite, PostgreSQL, or pluggable?
- **Authentication**: None, basic auth, OAuth, or integrate with git provider?
- **Multi-tenancy**: Single org or multi-org support?
- **Data retention**: How long to keep historical data?

### Configuration Schema
```toml
[dashboard]
enabled = false
database_url = "sqlite:///pr_agent_metrics.db"
api_port = 8080
static_files_path = "./dashboard/static"

[dashboard.auth]
enabled = false
method = "basic"  # "basic", "oauth"
```

---

## Feature 8: Official VS Code Extension

### Overview
Create a new open-source repository `pr-agent-vscode` with VS Code extension for PR-Agent integration.

### Tasks

#### 8.1 Repository Setup
- [ ] **8.1.1** Create new repository: `qodo-ai/pr-agent-vscode`
- [ ] **8.1.2** Initialize with VS Code extension scaffold
- [ ] **8.1.3** Set up CI/CD for extension publishing
- [ ] **8.1.4** Add AGPL-3.0 license
- [ ] **8.1.5** Create contribution guidelines

#### 8.2 Core Extension Features
- [ ] **8.2.1** Command palette integration:
  - `PR-Agent: Describe PR`
  - `PR-Agent: Review PR`
  - `PR-Agent: Run Checks`
  - `PR-Agent: Ask Question`
  - `PR-Agent: Improve Code`
- [ ] **8.2.2** Status bar item showing PR-Agent status
- [ ] **8.2.3** Activity bar panel for PR-Agent
- [ ] **8.2.4** Settings UI for configuration

#### 8.3 PR Integration
- [ ] **8.3.1** Detect current branch's PR automatically
- [ ] **8.3.2** Show PR-Agent findings in Problems panel
- [ ] **8.3.3** Display inline decorations for findings
- [ ] **8.3.4** Quick-fix actions for applicable suggestions

#### 8.4 Local Patch Application
- [ ] **8.4.1** Parse code suggestions from PR-Agent output
- [ ] **8.4.2** Show diff preview before applying
- [ ] **8.4.3** Apply patches with single click
- [ ] **8.4.4** Support undo for applied patches
- [ ] **8.4.5** Handle merge conflicts gracefully

#### 8.5 Backend Communication
- [ ] **8.5.1** Support direct CLI invocation (local PR-Agent)
- [ ] **8.5.2** Support HTTP API communication (remote PR-Agent)
- [ ] **8.5.3** Support GitHub App webhook trigger
- [ ] **8.5.4** Handle authentication securely

#### 8.6 UI Components
- [ ] **8.6.1** TreeView for PR findings/suggestions
- [ ] **8.6.2** WebView for rich markdown rendering
- [ ] **8.6.3** Input box for `/ask` questions
- [ ] **8.6.4** Progress indicators during operations

#### 8.7 Testing and Quality
- [ ] **8.7.1** Unit tests with Jest
- [ ] **8.7.2** Integration tests with VS Code test framework
- [ ] **8.7.3** Manual test checklist
- [ ] **8.7.4** Accessibility compliance (WCAG)

### Design Decisions to Make
- **Architecture**: Extension-only or Language Server Protocol (LSP)?
- **Backend**: Bundled PR-Agent or external server required?
- **Authentication**: Store tokens in VS Code secrets or system keychain?
- **Offline support**: What features work without network?

### Extension Configuration
```json
{
  "pr-agent.serverUrl": "http://localhost:8080",
  "pr-agent.authMethod": "token",
  "pr-agent.autoDetectPR": true,
  "pr-agent.showInlineFindings": true,
  "pr-agent.model": "gpt-4"
}
```

---

## Open Source Requirements

### Licensing Compliance
- [ ] All new code must be AGPL-3.0 licensed
- [ ] Add license headers to all new source files
- [ ] Audit all new dependencies for license compatibility
- [ ] Document any AGPL obligations for derivative works

### No Proprietary Dependencies
- [ ] Use only open-source libraries
- [ ] No API calls to proprietary services (except user-configured LLMs)
- [ ] Provide open-source alternatives for all features
- [ ] Document any optional proprietary integrations clearly

### Local LLM Support
- [ ] Ensure all features work with LiteLLM
- [ ] Test with Ollama for fully local operation
- [ ] Document local deployment configurations
- [ ] Optimize prompts for smaller models where possible

### Dependency Audit
```
Required new dependencies (all must be OSS-compatible):
- pathspec (BSD) - for glob pattern matching
- fastapi (MIT) - for dashboard API
- uvicorn (BSD) - for ASGI server
- aiosqlite (MIT) - for async SQLite access
- chart.js (MIT) - for dashboard charts (frontend)
```

---

## Dependencies and Recommended Order

### Dependency Graph
```
Feature 2 (Path-Scoped Config) ─┐
                                ├──► Feature 1 (Pre-Merge Checks)
Feature 4 (State Store) ────────┘
                                    │
Feature 4 (Incremental Review) ◄────┘
        │
        ├──► Feature 5 (Conversational)
        │
        └──► Feature 6 (Feedback Learning)
                    │
                    ▼
            Feature 7 (Dashboard)

Feature 3 (Diagrams) ──► Standalone

Feature 8 (VS Code) ──► Requires all core features
```

### Recommended Implementation Order

#### Phase 1: Foundation (Weeks 1-2)
1. **Feature 2: Path-Scoped Configuration** - Foundation for other features
2. **Feature 4.1-4.2: State Store & Finding Tracking** - Core infrastructure

#### Phase 2: Core Features (Weeks 3-4)
3. **Feature 1: Pre-Merge Check Engine** - High-value feature
4. **Feature 4.3-4.6: Incremental Review** - Complete review overhaul

#### Phase 3: Enhancements (Weeks 5-6)
5. **Feature 3: Expanded Diagrams** - Standalone enhancement
6. **Feature 5: Conversational PR** - Builds on state store

#### Phase 4: Intelligence (Weeks 7-8)
7. **Feature 6: Learning from Feedback** - Requires solid data foundation

#### Phase 5: Ecosystem (Weeks 9-10)
8. **Feature 7: Dashboard** - Visualization of collected data
9. **Feature 8: VS Code Extension** - Separate repo, can parallelize

---

## Testing Strategy

### Unit Testing
- [ ] Achieve 80%+ code coverage for new modules
- [ ] Mock external services (git providers, LLMs)
- [ ] Test configuration merging edge cases
- [ ] Test state store operations

### Integration Testing
- [ ] End-to-end tests with GitHub/GitLab APIs (test accounts)
- [ ] Test check status reporting
- [ ] Test incremental review state persistence
- [ ] Test feedback collection and preference application

### Performance Testing
- [ ] Benchmark state store operations
- [ ] Test with large PRs (1000+ file changes)
- [ ] Measure config resolution performance
- [ ] Load test dashboard API

### Manual Testing Checklist
- [ ] Test all new commands via CLI
- [ ] Test via GitHub Actions
- [ ] Test via GitLab webhooks
- [ ] Test with different LLM providers
- [ ] Test VS Code extension flows

---

## Documentation Plan

### User Documentation
- [ ] Update existing tool docs with new features
- [ ] Create check engine configuration guide
- [ ] Write path-scoped config tutorial
- [ ] Document state management and data persistence
- [ ] Create dashboard deployment guide
- [ ] Write VS Code extension user guide

### Developer Documentation
- [ ] Architecture decision records (ADRs) for major decisions
- [ ] API reference for new modules
- [ ] Plugin development guide (custom checks)
- [ ] State store implementation guide
- [ ] Contributing guide updates

### Migration Documentation
- [ ] Breaking changes log
- [ ] Configuration migration scripts
- [ ] State migration for existing users
- [ ] Deprecation notices and timelines

---

## Migration Guide

### Configuration Migration
1. Existing `.pr_agent.toml` files remain fully compatible
2. New path-scoped configs are opt-in
3. New sections use sensible defaults
4. Provide `pr_agent migrate` command for automated updates

### State Migration
1. First run with new version initializes state store
2. Historical data not required for basic operation
3. Provide import tool for existing feedback data

### Breaking Changes to Avoid
- Do not change existing command syntax
- Do not remove existing configuration options
- Maintain backward compatibility for webhook payloads
- Keep existing comment formats recognizable

---

## Notes

### Risks and Mitigations
| Risk | Mitigation |
|------|------------|
| State store corruption | Implement recovery mode, regular backups |
| Config merge conflicts | Clear precedence rules, validation command |
| Performance degradation | Lazy loading, caching, benchmarks |
| Provider API changes | Abstract provider layer, version pinning |
| LLM prompt size limits | Token counting, content prioritization |

### Out of Scope
- Real-time collaborative review features
- IDE plugins beyond VS Code (future consideration)
- Mobile applications
- Paid/premium tier features

### Future Considerations
- GitHub Copilot integration
- Custom LLM fine-tuning support
- Team/org management features
- Slack/Teams integrations

---

**Document Version**: 1.0
**Created**: 2024
**Last Updated**: 2024
**Status**: Planning Phase - Awaiting Approval
