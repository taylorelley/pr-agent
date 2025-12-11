# PR-Agent: AI Assistant Developer Guide

## Project Overview

**PR-Agent** is an open-source AI-powered tool for efficiently reviewing and handling pull requests.

**Important Notice:** This is a **community-maintained fork** of the original PR-Agent project. The original project was created by Qodo (formerly CodiumAI), but is no longer actively maintained as an open-source project. Qodo has shifted focus to their commercial product, Qodo Merge. This fork continues development of the open-source version with new features, improvements, and community support.

This fork provides automated code review, PR descriptions, code suggestions, and various other tools to streamline the PR workflow across multiple git platforms.

**Key Capabilities:**
- `/review` - AI-powered PR review with security analysis, effort estimates, and suggestions
- `/describe` - Auto-generate PR titles and descriptions with file walkthroughs
- `/improve` - Provide actionable code improvement suggestions
- `/ask` - Answer questions about PRs
- `/update_changelog` - Generate changelog entries
- 15+ additional specialized tools

**Supported Platforms:** GitHub, GitLab, Bitbucket, Azure DevOps, Gitea, Gerrit

**License:** AGPL-3.0

## Technology Stack

- **Language:** Python 3.12+
- **Web Framework:** FastAPI with Uvicorn/Gunicorn (for webhooks)
- **Configuration:** Dynaconf for hierarchical TOML-based configuration
- **AI Integration:** LiteLLM (supports 40+ AI models including OpenAI, Anthropic Claude, Google Gemini, AWS Bedrock)
- **Templates:** Jinja2 with StrictUndefined
- **Testing:** pytest with pytest-cov
- **Code Quality:** Ruff (linter), Bandit (security), pre-commit hooks

## Repository Structure

```
pr-agent/
├── pr_agent/                    # Main Python package
│   ├── tools/                   # PR analysis tools (14 tools)
│   │   ├── pr_reviewer.py       # Main review tool
│   │   ├── pr_code_suggestions.py
│   │   ├── pr_description.py
│   │   └── ...                  # 11+ other tools
│   ├── git_providers/           # Platform integrations (13 providers)
│   │   ├── git_provider.py      # Abstract base class
│   │   ├── github_provider.py
│   │   ├── gitlab_provider.py
│   │   └── ...                  # Other platform providers
│   ├── algo/                    # Core algorithms & utilities
│   │   ├── utils.py             # Core utility functions
│   │   ├── pr_processing.py     # PR diff processing
│   │   ├── token_handler.py     # Token management
│   │   └── ai_handlers/         # AI model integrations
│   ├── agent/                   # Main orchestrator
│   │   └── pr_agent.py          # Request handler & command routing
│   ├── servers/                 # Webhook servers & apps
│   ├── settings/                # TOML configuration files
│   │   ├── configuration.toml   # Main configuration (150+ settings)
│   │   └── *_prompts.toml       # Tool-specific prompts (20 files)
│   ├── identity_providers/      # Authentication providers
│   └── secret_providers/        # Secret management (AWS, GCP)
├── tests/                       # Test suite
│   ├── unittest/                # Unit tests (29+ test files)
│   ├── e2e_tests/               # End-to-end tests
│   └── health_test/             # Health checks
├── docs/                        # MkDocs documentation site
│   ├── docs/                    # Markdown documentation
│   └── mkdocs.yml               # Documentation configuration
├── docker/                      # Docker configurations
├── .github/workflows/           # CI/CD workflows
└── Configuration files          # pyproject.toml, requirements.txt, etc.
```

## Build, Test, and Development Workflows

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/qodo-ai/pr-agent.git
cd pr-agent

# Install Python 3.12+ (required)
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Configuration

Create a `.secrets_template.toml` file with your API keys:

```toml
[openai]
key = "your-api-key-here"

[github]
user_token = "your-github-token"
```

Repository-specific settings can be added to `.pr_agent.toml` in the project root.

### Running Tests

```bash
# Run all unit tests
pytest tests/unittest

# Run with verbose output
pytest -v tests/unittest

# Run with coverage report
pytest --cov=pr_agent tests/unittest

# Run specific test file
pytest tests/unittest/test_utils.py

# Run end-to-end tests
pytest tests/e2e_tests
```

### Running Locally

```bash
# CLI mode
pr-agent --pr_url=<PR_URL> review
pr-agent --pr_url=<PR_URL> describe
pr-agent --pr_url=<PR_URL> improve

# Docker mode
docker build -t pr-agent --target cli .
docker run -it pr-agent --pr_url=<PR_URL> review
```

### Linting and Formatting

```bash
# Run ruff linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Run bandit security scanner
bandit -r pr_agent/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Documentation

```bash
# Serve documentation locally
cd docs
mkdocs serve

# Build documentation
mkdocs build

# Documentation will be available at http://127.0.0.1:8000
```

## Code Style and Conventions

### Naming Conventions

- **Files:** `snake_case.py`
- **Classes:** `PascalCase` (e.g., `PRReviewer`, `GitProvider`)
- **Functions/Methods:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private methods:** `_leading_underscore`

### Architectural Patterns

**1. Async/Await Throughout:**
- All tools implement `async def run(self)` methods
- Use `asyncio.create_task()` for concurrent operations
- PR processing is fully asynchronous

**2. Abstract Base Classes:**
- `GitProvider` - base for all git platform integrations
- `BaseAiHandler` - base for AI model handlers
- Tools follow common patterns but are independent

**3. Command Pattern:**
- Commands map to tool classes via `command2class` in `pr_agent/agent/pr_agent.py`
- Uniform request handling interface
- Example: `/review` → `PRReviewer`, `/describe` → `PRDescription`

### Tool Implementation Pattern

```python
class ToolName:
    def __init__(self, pr_url: str, args: list = None,
                 ai_handler: partial[BaseAiHandler,] = LiteLLMAIHandler):
        self.git_provider = get_git_provider_with_context(pr_url)
        self.ai_handler = ai_handler()
        self.vars = {}  # Variables for prompt templates
        self.token_handler = TokenHandler(...)

    async def run(self):
        # Main execution logic
        pass
```

### Configuration Access

```python
from pr_agent.config_loader import get_settings

# Hierarchical access to settings
model = get_settings().config.model
max_findings = get_settings().pr_reviewer.num_max_findings
```

### Prompt Engineering

- Jinja2 templates with `StrictUndefined` mode
- Variables passed via `self.vars` dictionary
- Prompts stored in `pr_agent/settings/*_prompts.toml`
- System + user prompt separation
- Example duplication controlled by `duplicate_prompt_examples` config

### Error Handling

- Extensive try/except with structured logging
- Fallback models configured in `configuration.toml`
- `retry_with_fallback_models()` decorator for resilience
- Graceful degradation when features are unsupported

### Logging

```python
from pr_agent.log import get_logger
logger = get_logger()

# Use structured logging
logger.info("Processing PR", extra={"pr_url": pr_url})
logger.error("Failed to process", exc_info=True)
```

## Important Development Notes

### Token Management

- All tools must respect token limits via `TokenHandler`
- Use `clip_tokens()` for truncation
- Model-specific token counting via tiktoken
- Adaptive patch compression strategies available

### Git Provider Integration

When adding a new git provider:

1. Inherit from `GitProvider` base class
2. Implement all abstract methods
3. Add to `get_git_provider()` factory in `git_provider.py`
4. Test with e2e tests
5. Update documentation

### Adding New Tools

1. Create tool file in `pr_agent/tools/`
2. Implement `async def run(self)` method
3. Add prompt template in `pr_agent/settings/`
4. Register in `command2class` mapping
5. Add configuration section to `configuration.toml`
6. Write unit tests
7. Update documentation

### Configuration Hierarchy

Settings are loaded in this order (later overrides earlier):

1. Default `configuration.toml`
2. Global settings file (if enabled)
3. Wiki settings file (if enabled)
4. Repository `.pr_agent.toml` file (if enabled)
5. Environment variables
6. Command-line arguments

### Security Considerations

- **Never commit secrets** - use `.secrets_template.toml` or secret providers
- **Validate webhook signatures** - all webhook servers validate signatures
- **Use secret providers** for production - AWS Secrets Manager or Google Cloud Storage
- **Sanitize user inputs** - especially in custom prompts
- **Review generated code** - AI-generated code suggestions should be reviewed

### File Filtering

- Excluded file patterns: `pr_agent/settings/ignore.toml`
- Generated code patterns: `pr_agent/settings/generated_code_ignore.toml`
- Language detection: `pr_agent/settings/language_extensions.toml`
- Binary files are automatically excluded
- Large files (>100KB) may be skipped based on `large_patch_policy` setting

### Deployment Options

- **Local CLI** - Run from Docker or source
- **GitHub App** - Hosted or self-hosted webhook
- **GitHub Action** - Runs in CI/CD pipeline
- **GitLab Webhook** - Self-hosted server
- **Bitbucket App** - Hosted or self-hosted
- **AWS Lambda** - Serverless deployment (see `docker/Dockerfile.lambda`)
- **Polling** - For restricted network environments

## Testing Guidelines

- Write unit tests for all new functionality
- Use pytest fixtures for common setup
- Mock external API calls (git providers, AI models)
- Test error handling and edge cases
- Maintain >80% code coverage
- Add e2e tests for new tools
- Use `@pytest.mark.asyncio` for async tests

## Common Tasks for AI Assistants

### Reviewing Code Changes

When reviewing code in this repository:

1. Check adherence to async/await patterns
2. Verify token limits are respected
3. Ensure configuration is properly accessed via `get_settings()`
4. Validate error handling with logging
5. Check that prompts use Jinja2 syntax correctly
6. Verify tests are included for new functionality

### Adding Features

When adding new features:

1. Check if it should be a new tool or extension of existing tool
2. Review existing similar tools for patterns
3. Update configuration.toml with new settings
4. Create prompt templates if needed
5. Add comprehensive tests
6. Update documentation in `docs/docs/`
7. Follow conventional commit message format

### Debugging Issues

Key files for debugging:

- `pr_agent/log/` - Logging configuration
- `pr_agent/algo/utils.py` - Core utilities
- `pr_agent/agent/pr_agent.py` - Main orchestrator
- Configuration files in `pr_agent/settings/`
- Set `log_level="DEBUG"` in configuration for verbose output

### Working with AI Models

- Default model: configurable via `config.model`
- Fallback models: `config.fallback_models`
- Temperature: `config.temperature` (default 0.2)
- Token limits: `config.max_model_tokens`
- Timeout: `config.ai_timeout` (default 120s)
- Support for reasoning models (OpenAI o1, Claude with extended thinking)

## Commit Message Guidelines

Use conventional commit format:

```
<type>: <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

## Pull Request Guidelines

1. Create a focused PR with a single feature or fix
2. Include clear description of changes
3. Link related issues
4. Ensure all tests pass
5. Update documentation as needed
6. Wait for CI/CD checks to complete
7. Respond to review comments promptly

## Additional Resources

- **Documentation:** https://qodo-merge-docs.qodo.ai/
- **Issues:** https://github.com/qodo-ai/pr-agent/issues
- **Discord:** https://discord.com/channels/1057273017547378788/1126104260430528613
- **License:** AGPL-3.0

## Notes for AI Assistants

- This repository uses PR-Agent itself! The configuration at line 53-54 in `pr_agent/settings/configuration.toml` shows that PR-Agent can read AGENTS.MD and CLAUDE.MD files
- Always respect the AGPL-3.0 license when suggesting code
- This is a community-maintained fork - the original Qodo project is no longer actively maintained as open source
- Focus on code quality over speed - this is a production tool used by many teams
- When in doubt, check the extensive documentation in `docs/docs/`
- Test thoroughly - bugs in code review tools can be particularly impactful
