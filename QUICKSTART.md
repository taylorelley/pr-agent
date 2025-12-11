# Quickstart Guide

Get PR-Agent running with local Ollama in 2 minutes.

## Prerequisites

- Docker or Podman
- Ollama instance with a model (e.g., `codestral:22b`)
- Git provider access token (Gitea, GitHub, or GitLab)

## 1. Pull the Image

```bash
docker pull ghcr.io/tobend/pr-agent:latest
```

## 2. Run a Review

Replace the placeholder values:

```bash
docker run --rm \
  -e CONFIG.GIT_PROVIDER=gitea \
  -e GITEA.URL=https://your-gitea.com \
  -e GITEA.PERSONAL_ACCESS_TOKEN=your-token \
  -e OPENAI.API_BASE=https://your-ollama.com/v1 \
  -e OPENAI.KEY=dummy \
  -e CONFIG.MODEL=openai/codestral:22b \
  ghcr.io/tobend/pr-agent:latest \
  --pr_url="https://your-gitea.com/owner/repo/pulls/1" review
```

## Available Commands

| Command | Description |
|---------|-------------|
| `review` | Full code review with issues and score |
| `describe` | Generate PR description |
| `improve` | Suggest code improvements |

## Provider Configuration

**Gitea:**
```
-e CONFIG.GIT_PROVIDER=gitea
-e GITEA.URL=https://...
-e GITEA.PERSONAL_ACCESS_TOKEN=...
```

**GitHub:**
```
-e CONFIG.GIT_PROVIDER=github
-e GITHUB.USER_TOKEN=...
```

**GitLab:**
```
-e CONFIG.GIT_PROVIDER=gitlab
-e GITLAB.URL=https://...
-e GITLAB.PERSONAL_ACCESS_TOKEN=...
```

## Recommended Models

- `codestral:22b` - Best for code review
- `qwen2.5-coder:14b` - Good alternative
- `mistral:latest` - Lightweight

## Troubleshooting

**"Failed to parse review data"**
- Ensure Ollama is v0.5+ (supports json_schema)
- Check model is loaded: `curl your-ollama:11434/api/tags`

**Connection refused**
- Verify Ollama is accessible from Docker
- Check firewall/network settings

## Next Steps

See [README.md](README.md) for full documentation.
