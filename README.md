# PR-Agent Fork for Local Ollama Integration

A fork of [PR-Agent](https://github.com/Codium-ai/pr-agent) with modifications to support local Ollama models with reliable structured output.

## Quick Links

- [QUICKSTART.md](QUICKSTART.md) - Get running in 2 minutes
- [Changes from Upstream](#changes-from-upstream)
- [Environment Variables](#environment-variables)

## Why This Fork?

The official PR-Agent blocks certain LiteLLM parameters required for proper Ollama integration. This fork enables:

1. **JSON Schema Enforcement** - Uses Ollama's GBNF grammar to force exact schema compliance
2. **Response Format Support** - Passes `response_format` through LiteLLM
3. **Gitea Compatibility** - Fixes `urllib3` version conflict

## Installation

```bash
docker pull ghcr.io/tobend/pr-agent:latest
```

## Usage by Git Provider

### Gitea / Codeberg

Gitea and Gitea-based platforms (like Codeberg) use the same configuration:

```bash
docker run --rm \
  -e CONFIG.GIT_PROVIDER=gitea \
  -e GITEA.URL=https://your-gitea.example.com \
  -e GITEA.PERSONAL_ACCESS_TOKEN=your-token-here \
  -e OPENAI.API_BASE=https://your-ollama.example.com/v1 \
  -e OPENAI.KEY=dummy \
  -e CONFIG.MODEL=openai/codestral:22b \
  -e CONFIG.CUSTOM_MODEL_MAX_TOKENS=8192 \
  -e CONFIG.TEMPERATURE=0 \
  ghcr.io/tobend/pr-agent:latest \
  --pr_url="https://your-gitea.example.com/owner/repo/pulls/1" review
```

**Examples:**
- Gitea: `GITEA.URL=https://gitea.example.com`
- Codeberg: `GITEA.URL=https://codeberg.org`

**Gitea-Specific Variables:**
- `GITEA.URL` - Your Gitea/Codeberg instance URL
- `GITEA.PERSONAL_ACCESS_TOKEN` - Access token with repo permissions

### GitHub

```bash
docker run --rm \
  -e CONFIG.GIT_PROVIDER=github \
  -e GITHUB.USER_TOKEN=your-github-token \
  -e GITHUB.BASE_URL=https://api.github.com \
  -e OPENAI.API_BASE=https://your-ollama.example.com/v1 \
  -e OPENAI.KEY=dummy \
  -e CONFIG.MODEL=openai/codestral:22b \
  -e CONFIG.CUSTOM_MODEL_MAX_TOKENS=8192 \
  -e CONFIG.TEMPERATURE=0 \
  ghcr.io/tobend/pr-agent:latest \
  --pr_url="https://github.com/owner/repo/pull/1" review
```

**GitHub-Specific Variables:**
- `GITHUB.USER_TOKEN` - Personal access token with repo scope
- `GITHUB.BASE_URL` - API endpoint (default: `https://api.github.com`)
- `GITHUB.DEPLOYMENT_TYPE` - `user` or `app` (default: `user`)

### GitLab

```bash
docker run --rm \
  -e CONFIG.GIT_PROVIDER=gitlab \
  -e GITLAB.URL=https://gitlab.com \
  -e GITLAB.PERSONAL_ACCESS_TOKEN=your-gitlab-token \
  -e OPENAI.API_BASE=https://your-ollama.example.com/v1 \
  -e OPENAI.KEY=dummy \
  -e CONFIG.MODEL=openai/codestral:22b \
  -e CONFIG.CUSTOM_MODEL_MAX_TOKENS=8192 \
  -e CONFIG.TEMPERATURE=0 \
  ghcr.io/tobend/pr-agent:latest \
  --pr_url="https://gitlab.com/owner/repo/-/merge_requests/1" review
```

**GitLab-Specific Variables:**
- `GITLAB.URL` - GitLab instance URL (default: `https://gitlab.com`)
- `GITLAB.PERSONAL_ACCESS_TOKEN` - Access token with api scope

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `CONFIG.GIT_PROVIDER` | Git provider type | `gitea`, `github`, `gitlab` |
| `OPENAI.API_BASE` | Ollama API endpoint (must end in `/v1`) | `https://localhost:11434/v1` |
| `OPENAI.KEY` | API key (any value, Ollama ignores it) | `dummy` |
| `CONFIG.MODEL` | Model name with `openai/` prefix | `openai/codestral:22b` |

### Provider Tokens

| Variable | Provider | Description |
|----------|----------|-------------|
| `GITEA.PERSONAL_ACCESS_TOKEN` | Gitea | Access token |
| `GITHUB.USER_TOKEN` | GitHub | Personal access token (repo scope) |
| `GITLAB.PERSONAL_ACCESS_TOKEN` | GitLab | Access token (api scope) |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG.CUSTOM_MODEL_MAX_TOKENS` | `-1` | Token limit for custom models |
| `CONFIG.TEMPERATURE` | `0.2` | Model temperature (0 = deterministic) |
| `CONFIG.VERBOSITY_LEVEL` | `0` | Logging verbosity (0-2) |
| `CONFIG.PUBLISH_OUTPUT` | `true` | Publish results to PR |
| `CONFIG.PUBLISH_OUTPUT_PROGRESS` | `true` | Show progress comments |
| `LITELLM.ENABLE_JSON_SCHEMA_VALIDATION` | `true` | Validate JSON schema |

### Provider URLs

| Variable | Provider | Default |
|----------|----------|---------|
| `GITEA.URL` | Gitea | Required |
| `GITHUB.BASE_URL` | GitHub | `https://api.github.com` |
| `GITLAB.URL` | GitLab | `https://gitlab.com` |

### Review Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PR_REVIEWER.REQUIRE_TESTS_REVIEW` | `true` | Check for tests |
| `PR_REVIEWER.REQUIRE_SECURITY_REVIEW` | `true` | Security analysis |
| `PR_REVIEWER.REQUIRE_ESTIMATE_EFFORT_TO_REVIEW` | `true` | Effort estimation |
| `PR_REVIEWER.REQUIRE_SCORE` | `false` | PR quality score |
| `PR_REVIEWER.NUM_MAX_FINDINGS` | `3` | Max issues to report |
| `PR_REVIEWER.EXTRA_INSTRUCTIONS` | `""` | Custom review instructions |

## Available Commands

| Command | Description |
|---------|-------------|
| `review` | Full code review with issues, score, and security analysis |
| `describe` | Generate or update PR title and description |
| `improve` | Suggest code improvements as inline comments |
| `ask "question"` | Ask questions about the PR |
| `update_changelog` | Update CHANGELOG.md based on PR |

## Tested Models

| Model | Result | Notes |
|-------|--------|-------|
| codestral:22b | Works | Best results with json_schema enforcement |
| qwen2.5-coder:14b | Works | Good alternative, faster |
| mistral:latest | Works | Lightweight, may simplify complex PRs |

Requires Ollama 0.5+ for json_schema support.

## Changes from Upstream

### 1. LiteLLM Helper (`pr_agent/algo/ai_handlers/litellm_helpers.py`)

Expanded `allowed_extra_body_keys` to include:
```python
{
    "response_format",  # Structured output (JSON schema)
    "drop_params",      # Graceful parameter handling
    "max_retries",      # Retry failed requests
    "timeout",          # Request timeout
}
```

### 2. Configuration (`pr_agent/settings/configuration.toml`)

Added default `extra_body` with full PRReview JSON schema:
```toml
[litellm]
extra_body = '{"response_format":{"type":"json_schema","json_schema":{...}}}'
```

This uses Ollama's GBNF grammar enforcement (v0.5+) to ensure the model returns the exact expected structure.

### 3. Prompts (`pr_agent/settings/pr_reviewer_prompts.toml`)

- Changed output format from YAML to JSON
- Removed markdown fence that caused output wrapping

### 4. Dependencies (`requirements.txt`)

- Pinned `urllib3==2.5.0` to fix Gitea provider compatibility

## How JSON Schema Enforcement Works

Ollama 0.5+ supports structured outputs via GBNF grammars. When you specify:

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "PRReview",
      "schema": { ... }
    }
  }
}
```

The model is constrained to produce output that exactly matches the schema, eliminating parsing errors.

## Building Locally

```bash
git clone https://github.com/TobEnd/pr-agent.git
cd pr-agent
docker build -t pr-agent:local -f docker/Dockerfile --target cli .
```

## Docker Compose

See [docker-compose.yml](docker-compose.yml) for a complete example.

## Troubleshooting

**"Failed to parse review data"**
- Ensure Ollama is v0.5+ (supports json_schema)
- Verify model is loaded: `curl http://localhost:11434/api/tags`

**Connection refused**
- Check Ollama is accessible from Docker network
- Use host IP, not `localhost` when running in Docker

**Model returns simplified output**
- Ensure json_schema enforcement is enabled (built into this fork)
- Try a larger model (e.g., codestral:22b vs mistral:latest)

## Contributing

This fork is maintained for personal use. For upstream issues, contribute to [Codium-ai/pr-agent](https://github.com/Codium-ai/pr-agent).

## License

Apache 2.0 (same as upstream)

## Acknowledgments

- [Codium-ai/pr-agent](https://github.com/Codium-ai/pr-agent) - Original project
- [Ollama](https://ollama.ai) - Local LLM runtime with GBNF support
