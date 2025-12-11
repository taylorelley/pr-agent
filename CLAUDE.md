# Claude AI Assistant Guide for PR-Agent

## Quick Start

**For comprehensive development guidelines, please refer to [AGENTS.md](./AGENTS.md)** which contains detailed information about:

- Project overview and architecture
- Repository structure and key components
- Build, test, and development workflows
- Code style and conventions
- Testing guidelines
- Common development tasks

This document provides Claude-specific guidance and quick references.

## Project Context

**PR-Agent** is an AI-powered code review and PR management tool supporting 40+ AI models across GitHub, GitLab, Bitbucket, Azure DevOps, Gitea, and Gerrit. It's a Python 3.12+ application using FastAPI, LiteLLM, and Dynaconf with an AGPL-3.0 license.

**Important:** This is a **community-maintained fork** of the original open-source PR-Agent. The original project by Qodo (formerly CodiumAI) is no longer actively maintained as they have shifted focus to their commercial product, Qodo Merge. This fork continues development of the open-source version with new features, improvements, and community-driven enhancements.

## Quick Reference

### Essential Commands

```bash
# Setup
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Testing
pytest tests/unittest                  # Run unit tests
pytest --cov=pr_agent tests/unittest  # With coverage
pytest -v tests/unittest              # Verbose

# Linting
ruff check .                          # Check code
ruff check --fix .                    # Auto-fix

# Local execution
pr-agent --pr_url=<URL> review        # Run review tool
pr-agent --pr_url=<URL> describe      # Generate description
pr-agent --pr_url=<URL> improve       # Suggest improvements

# Documentation
cd docs && mkdocs serve               # Serve docs locally
```

### Key File Locations

- **Main orchestrator:** `pr_agent/agent/pr_agent.py`
- **Tools:** `pr_agent/tools/*.py` (14 tools)
- **Git providers:** `pr_agent/git_providers/*.py` (13 providers)
- **Configuration:** `pr_agent/settings/configuration.toml`
- **Prompts:** `pr_agent/settings/*_prompts.toml`
- **Tests:** `tests/unittest/`, `tests/e2e_tests/`

### Code Patterns to Follow

**Async Pattern:**
```python
class NewTool:
    async def run(self):
        # All tools must be async
        pass
```

**Configuration Access:**
```python
from pr_agent.config_loader import get_settings
setting = get_settings().config.model
```

**Logging:**
```python
from pr_agent.log import get_logger
logger = get_logger()
logger.info("Message", extra={"key": "value"})
```

**Git Provider:**
```python
self.git_provider = get_git_provider_with_context(pr_url)
pr_info = await self.git_provider.get_pr()
```

## Important Conventions

### Architecture
- **Async/await everywhere** - All tools use `async def run()`
- **Abstract base classes** - `GitProvider`, `BaseAiHandler` define interfaces
- **Command pattern** - Commands map to tool classes in `command2class`
- **Hierarchical config** - Settings cascade from defaults → global → repo → env → CLI

### Code Style
- **Naming:** snake_case files, PascalCase classes, snake_case functions
- **Line length:** 120 characters (Ruff enforced)
- **Imports:** isort-organized
- **Type hints:** Preferred but not strictly enforced

### Testing Requirements
- Unit tests required for all new functionality
- Use pytest with async support (`@pytest.mark.asyncio`)
- Mock external APIs (git providers, AI models)
- Maintain >80% code coverage
- Test error handling and edge cases

## Critical Development Notes

### Token Management
Every tool must respect token limits via `TokenHandler`. Use:
```python
self.token_handler = TokenHandler(...)
truncated = clip_tokens(text, max_tokens)
```

### Security
- **Never commit secrets** - use `.secrets_template.toml` or secret providers
- **Validate webhooks** - all servers must validate signatures
- **Sanitize inputs** - especially in custom prompts
- **Review AI output** - generated code should always be reviewed

### Configuration Hierarchy
Settings load in this order (later overrides earlier):
1. `pr_agent/settings/configuration.toml` (defaults)
2. Global settings file
3. Wiki settings file
4. Repository `.pr_agent.toml`
5. Environment variables
6. Command-line arguments

### Self-Reference Note
⚠️ **Important:** PR-Agent can read this file! The configuration at `pr_agent/settings/configuration.toml:53-54` shows:
```toml
add_repo_metadata=false
add_repo_metadata_file_list =["AGENTS.MD", "CLAUDE.MD", "QODO.MD"]
```

When this setting is enabled, PR-Agent will include AGENTS.MD and CLAUDE.MD content in its AI context when reviewing PRs in this repository.

## Common AI Assistant Tasks

### Adding a New Tool
1. Create `pr_agent/tools/new_tool.py` with async run method
2. Add prompt template in `pr_agent/settings/new_tool_prompts.toml`
3. Register in `command2class` mapping in `pr_agent/agent/pr_agent.py`
4. Add config section to `configuration.toml`
5. Write tests in `tests/unittest/test_new_tool.py`
6. Document in `docs/docs/tools/new_tool.md`

### Adding a New Git Provider
1. Inherit from `GitProvider` in `pr_agent/git_providers/git_provider.py`
2. Implement all abstract methods
3. Add to `get_git_provider()` factory
4. Add e2e tests
5. Update installation docs

### Debugging
1. Set `log_level="DEBUG"` in configuration
2. Check logs in console output
3. Review `pr_agent/algo/utils.py` for core utilities
4. Examine token usage with `verbosity_level=2`
5. Use pytest `-v` flag for detailed test output

### Reviewing PRs in This Repository
When reviewing code changes:
- ✅ Check async/await patterns are used correctly
- ✅ Verify token limits are respected
- ✅ Ensure configuration accessed via `get_settings()`
- ✅ Validate error handling with proper logging
- ✅ Check Jinja2 template syntax in prompts
- ✅ Confirm tests are included and passing
- ✅ Verify documentation is updated
- ✅ Follow conventional commit message format

## Commit Message Format

```
<type>: <description>

[optional body]
```

**Types:** feat, fix, docs, test, refactor, perf, chore

**Example:**
```
feat: add support for Gerrit code review platform

- Implement GerritProvider class
- Add authentication handling
- Include unit and e2e tests
```

## Resources

- **Detailed Guide:** [AGENTS.md](./AGENTS.md)
- **Documentation:** https://qodo-merge-docs.qodo.ai/
- **Repository:** https://github.com/qodo-ai/pr-agent
- **Issues:** https://github.com/qodo-ai/pr-agent/issues
- **License:** AGPL-3.0
- **Discord:** [Community Server](https://discord.com/channels/1057273017547378788/1126104260430528613)

## Philosophy

- **Code quality over speed** - This tool reviews code for thousands of teams
- **Thorough testing** - Bugs in code review tools are particularly impactful
- **Clear documentation** - AI assistance should be transparent and well-documented
- **Respect the license** - AGPL-3.0 requires derivative works to be open source
- **Async-first** - All I/O operations should be asynchronous
- **Configuration-driven** - Behavior should be customizable via TOML settings

---

**Remember:** Always check [AGENTS.md](./AGENTS.md) for comprehensive development guidelines and architectural details.
