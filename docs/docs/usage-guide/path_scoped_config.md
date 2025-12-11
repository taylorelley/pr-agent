# Path-Scoped Configuration System

The path-scoped configuration system allows you to customize PR-Agent behavior for different parts of your repository using multiple `.pr_agent.toml` files in subdirectories. This is particularly useful for monorepos where different teams or modules have different review requirements.

## Overview

With path-scoped configuration:
- Place `.pr_agent.toml` files in any subdirectory
- Configurations are automatically discovered and merged based on file paths
- Deeper configurations override shallower ones
- Security restrictions prevent dangerous overrides in subdirectories

## Enabling Path-Scoped Configuration

Add to your root `.pr_agent.toml`:

```toml
[config]
path_config_enabled = true
path_config_max_depth = 5  # Maximum directory depth to search
```

## Configuration File Names

PR-Agent searches for configuration files in this order of precedence:
1. `.pr_agent.toml`
2. `pr_agent.toml`
3. `.pr-agent.toml`

## How Configuration Merging Works

### Merge Order

Configurations are merged from root to leaf:
1. Repository root `.pr_agent.toml`
2. Intermediate directory configs
3. Deepest directory config (highest precedence)

### Example Directory Structure

```text
my-repo/
├── .pr_agent.toml              # Root config
├── src/
│   ├── .pr_agent.toml          # Applies to all of src/
│   ├── backend/
│   │   ├── .pr_agent.toml      # Applies to backend only
│   │   └── api.py
│   └── frontend/
│       ├── .pr_agent.toml      # Applies to frontend only
│       └── app.tsx
└── tests/
    └── test_api.py
```

### Merge Example

**Root config** (`.pr_agent.toml`):
```toml
[pr_reviewer]
num_max_findings = 3
extra_instructions = "General review guidelines"
require_security_review = true
```

**Backend config** (`src/backend/.pr_agent.toml`):
```toml
[pr_reviewer]
extra_instructions = "Focus on API security and database queries"
```

**Effective config for `src/backend/api.py`**:
```toml
[pr_reviewer]
num_max_findings = 3                    # From root
extra_instructions = "Focus on API security and database queries"  # From backend (overrides root)
require_security_review = true          # From root
```

## Allowed Overrides

For security, subdirectory configs can **only** override these settings:

### PR Reviewer
- `pr_reviewer.extra_instructions`
- `pr_reviewer.num_max_findings`
- `pr_reviewer.require_score_review`
- `pr_reviewer.require_tests_review`
- `pr_reviewer.require_security_review`

### Code Suggestions
- `pr_code_suggestions.extra_instructions`
- `pr_code_suggestions.num_code_suggestions`

### Other Tools
- `pr_description.extra_instructions`
- `pr_questions.extra_instructions`

## Forbidden Overrides

Subdirectory configs **cannot** override:
- `config.model` - Model selection
- `config.fallback_models` - Fallback models
- API keys (`openai.key`, `anthropic.key`, etc.)
- Git provider settings
- Access tokens

Attempting to override forbidden settings will cause validation errors.

## Merge Strategies

Control how configurations merge using the `_merge_strategy` directive:

### Override (Default)
Child completely replaces parent value:
```toml
[pr_reviewer]
_merge_strategy = "override"
extra_instructions = "Backend specific instructions"
```

### Extend
Child adds to parent (for compatible types):
```toml
[pr_reviewer]
_merge_strategy = "extend"
extra_instructions = "Additional backend instructions"
```

### Inherit
Child inherits parent if not specified:
```toml
[pr_reviewer]
_merge_strategy = "inherit"
extra_instructions = "Only set if not in parent"
```

## Validation Command

Validate your path-scoped configurations:

```bash
/config validate
```

Or via CLI:
```bash
pr-agent --pr_url=<URL> config validate
```

### Validation Output

The validation report includes:
- ✅ Overall validation status
- 📋 Configuration summary
- 📁 Discovered configuration files
- ⚠️ Validation issues (if any)
- 💡 Best practices recommendations

Example output:
```markdown
## 🔍 Path-Scoped Configuration Validation

✅ **All configurations are valid!**

### Configuration Summary
- Path Config Enabled: true
- Repository Root: /path/to/repo
- Max Depth: 5
- Changed Files: 3
- Discovered Configs: 2

### Discovered Configuration Files
| File | Depth |
|------|-------|
| `.pr_agent.toml` | 0 |
| `src/backend/.pr_agent.toml` | 2 |
```

## Use Cases

### 1. Different Review Strictness by Module

**Root config** - Lenient defaults:
```toml
[pr_reviewer]
num_max_findings = 5
```

**Critical module** (`src/security/.pr_agent.toml`):
```toml
[pr_reviewer]
num_max_findings = 10
require_security_review = true
extra_instructions = "Extremely thorough security review required"
```

### 2. Language-Specific Instructions

**Python backend** (`src/backend/.pr_agent.toml`):
```toml
[pr_reviewer]
extra_instructions = "Check for async/await patterns, type hints, and proper exception handling"

[pr_code_suggestions]
extra_instructions = "Suggest Pythonic idioms and PEP 8 compliance"
```

**TypeScript frontend** (`src/frontend/.pr_agent.toml`):
```toml
[pr_reviewer]
extra_instructions = "Check for React best practices, hooks usage, and TypeScript strict mode compliance"

[pr_code_suggestions]
extra_instructions = "Suggest modern React patterns and accessibility improvements"
```

### 3. Test Directory Configuration

**Test directory** (`tests/.pr_agent.toml`):
```toml
[pr_reviewer]
extra_instructions = "Verify test coverage, check for proper mocking, and ensure test isolation"
num_max_findings = 2  # More lenient for tests
```

### 4. Legacy Code vs New Code

**Legacy module** (`src/legacy/.pr_agent.toml`):
```toml
[pr_reviewer]
num_max_findings = 2  # Be gentle with legacy code
extra_instructions = "Focus on critical bugs and security issues only"
```

**New module** (`src/new/.pr_agent.toml`):
```toml
[pr_reviewer]
num_max_findings = 10  # Strict for new code
extra_instructions = "Enforce all best practices and design patterns"
```

## Best Practices

### 1. Document Your Configs
Add comments explaining why each subdirectory config exists:
```toml
# Backend API requires extra security review due to sensitive data handling
[pr_reviewer]
require_security_review = true
```

### 2. Keep It Simple
- Use subdirectory configs sparingly
- Only override what's necessary
- Prefer root config for global settings

### 3. Security First
- Never commit API keys or secrets in config files
- Use environment variables or secret managers for sensitive data
- Regularly validate your configurations

### 4. Test Your Configurations
- Use `/config validate` before merging config changes
- Test with actual PRs to verify behavior
- Review validation reports carefully

### 5. Team Communication
- Document your configuration strategy in README
- Notify team when adding new subdirectory configs
- Establish conventions for config usage

## Troubleshooting

### Config Not Being Applied

1. **Check if path config is enabled:**
   ```toml
   [config]
   path_config_enabled = true
   ```

2. **Verify file naming:**
   - Must be exactly `.pr_agent.toml`, `pr_agent.toml`, or `.pr-agent.toml`
   - Check for typos

3. **Check depth limit:**
   ```toml
   [config]
   path_config_max_depth = 5  # Increase if needed
   ```

4. **Run validation:**
   ```bash
   /config validate
   ```

### Security Violations

If you see errors like "Setting cannot be overridden in subdirectory configs":
- Move the setting to root config
- Check the [Allowed Overrides](#allowed-overrides) list
- Remove forbidden settings from subdirectory configs

### Merge Conflicts

If settings aren't merging as expected:
- Review merge order (root → leaf)
- Check for `_merge_strategy` directives
- Use `/config validate` to see effective configuration

## Performance Considerations

- **Caching:** Discovered configurations are cached per PR
- **Max Depth:** Lower `path_config_max_depth` for faster discovery
- **File Count:** More config files = slower discovery (but cached)

## Migration from Single Config

To migrate from a single root config to path-scoped configs:

1. **Enable the feature:**
   ```toml
   [config]
   path_config_enabled = true
   ```

2. **Identify sections that vary by path:**
   - Review your root config
   - Note settings that should differ by module

3. **Create subdirectory configs incrementally:**
   - Start with one subdirectory
   - Test with `/config validate`
   - Verify with actual PRs
   - Expand to other directories

4. **Remove overridden settings from root:**
   - Keep only true defaults in root config
   - Move specific settings to subdirectories

## API Usage

For programmatic access:

```python
from pathlib import Path
from pr_agent.path_config import ConfigResolver

# Initialize resolver
resolver = ConfigResolver(
    repo_root=Path("/path/to/repo"),
    max_depth=5,
    enable_path_config=True
)

# Get config for a specific file
resolved = resolver.get_config_for_file("src/backend/api.py")
print(resolved.config)
print(resolved.get_applied_config_info())

# Get configs for multiple files
results = resolver.get_config_for_files([
    "src/backend/api.py",
    "src/frontend/app.tsx"
])

# Validate all configs
issues = resolver.validate_all_configs(changed_files)
if issues:
    for issue in issues:
        print(f"Issue in {issue['file']}: {issue['message']}")
```

## FAQ

**Q: Can I use path-scoped configs with GitHub Actions?**
A: Yes, path-scoped configs work with all PR-Agent deployment methods.

**Q: Do path-scoped configs work with all git providers?**
A: Yes, this feature is provider-agnostic and works with GitHub, GitLab, Bitbucket, Azure DevOps, etc.

**Q: How many levels of nesting are supported?**
A: By default 5 levels, configurable via `path_config_max_depth`.

**Q: Can I disable path-scoped config for specific PRs?**
A: Set `path_config_enabled = false` in your root config, or don't create subdirectory configs.

**Q: What happens if a config file has syntax errors?**
A: The file will be skipped and logged as an error. Use `/config validate` to check for issues.

## Related Documentation

- [Configuration Guide](../core/configuration_options.md)
- [Security Best Practices](../security/best_practices.md)
- [PR Review Tool](../tools/review.md)
- [Code Suggestions Tool](../tools/improve.md)

## Support

For issues or questions:
- [GitHub Issues](https://github.com/qodo-ai/pr-agent/issues)
- [Discord Community](https://discord.com/channels/1057273017547378788/1126104260430528613)
