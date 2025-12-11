from pathlib import Path
from dynaconf import Dynaconf

from pr_agent.config_loader import get_settings, _find_repository_root
from pr_agent.git_providers import get_git_provider
from pr_agent.log import get_logger


class PRConfig:
    """
    The PRConfig class is responsible for listing and validating configuration options.

    Supports commands:
    - /config (or /settings): List all configurations
    - /config validate: Validate path-scoped configurations
    """
    def __init__(self, pr_url: str, args=None, ai_handler=None):
        """
        Initialize the PRConfig object with the necessary attributes and objects to comment on a pull request.

        Args:
            pr_url (str): The URL of the pull request to be reviewed.
            args (list, optional): List of arguments passed to the PRConfig class. Defaults to None.
        """
        self.git_provider = get_git_provider()(pr_url)
        self.args = args or []

    async def run(self):
        # Check if this is a validate command
        if self.args and 'validate' in [arg.lower() for arg in self.args]:
            return await self._run_validate()

        # Default behavior: list configurations
        get_logger().info('Getting configuration settings...')
        get_logger().info('Preparing configs...')
        pr_comment = self._prepare_pr_configs()
        if get_settings().config.publish_output:
            get_logger().info('Pushing configs...')
            self.git_provider.publish_comment(pr_comment)
            self.git_provider.remove_initial_comment()
        return ""

    async def _run_validate(self):
        """
        Validate path-scoped configuration files for the PR.

        This command:
        1. Discovers all .pr_agent.toml files in the repository
        2. Validates security constraints
        3. Checks for configuration conflicts
        4. Reports effective configuration per path
        """
        get_logger().info('Validating path-scoped configurations...')

        # Check if path-based config is enabled
        if not get_settings().config.get('path_config_enabled', False):
            message = "⚠️ **Path-Scoped Configuration Validation**\n\n"
            message += "Path-based configuration is currently disabled.\n"
            message += "Enable it by setting `config.path_config_enabled = true` in your configuration."

            if get_settings().config.publish_output:
                self.git_provider.publish_comment(message)
            return message

        try:
            from pr_agent.path_config import ConfigResolver

            # Find repository root
            repo_root = _find_repository_root()
            if not repo_root:
                message = "❌ **Configuration Validation Failed**\n\n"
                message += "Could not find repository root (no .git directory found)."
                if get_settings().config.publish_output:
                    self.git_provider.publish_comment(message)
                return message

            # Get changed files from PR
            pr_files = await self.git_provider.get_pr_files()
            changed_files = [file.filename for file in pr_files]

            # Initialize resolver
            max_depth = get_settings().config.get('path_config_max_depth', 5)
            resolver = ConfigResolver(
                repo_root=repo_root,
                max_depth=max_depth,
                enable_path_config=True
            )

            # Validate configurations
            issues = resolver.validate_all_configs(changed_files)

            # Get configuration summary
            summary = resolver.get_config_summary(changed_files)

            # Prepare response
            pr_comment = self._prepare_validation_report(issues, summary, changed_files)

            if get_settings().config.publish_output:
                get_logger().info('Publishing validation report...')
                self.git_provider.publish_comment(pr_comment)
                self.git_provider.remove_initial_comment()

            return pr_comment

        except Exception as e:
            get_logger().error(f"Configuration validation failed: {e}", exc_info=True)
            message = f"❌ **Configuration Validation Error**\n\n```\n{str(e)}\n```"
            if get_settings().config.publish_output:
                self.git_provider.publish_comment(message)
            return message

    def _prepare_validation_report(self, issues, summary, changed_files):
        """
        Prepare a markdown report for configuration validation.

        Args:
            issues: List of validation issues
            summary: Configuration summary dictionary
            changed_files: List of changed file paths

        Returns:
            Markdown formatted validation report
        """
        report = "## 🔍 Path-Scoped Configuration Validation\n\n"

        # Overall status
        if not issues:
            report += "✅ **All configurations are valid!**\n\n"
        else:
            report += f"⚠️ **Found {len(issues)} validation issue(s)**\n\n"

        # Summary section
        report += "<details>\n<summary><strong>Configuration Summary</strong></summary>\n\n"
        report += "```yaml\n"
        report += f"Path Config Enabled: {summary['path_config_enabled']}\n"
        report += f"Repository Root: {summary['repo_root']}\n"
        report += f"Max Depth: {summary['max_depth']}\n"
        report += f"Changed Files: {summary['changed_files_count']}\n"
        report += f"Discovered Configs: {len(summary['discovered_configs'])}\n"
        report += "```\n"
        report += "</details>\n\n"

        # Discovered configs
        if summary['discovered_configs']:
            report += "<details>\n<summary><strong>Discovered Configuration Files</strong></summary>\n\n"
            report += "| File | Depth |\n"
            report += "|------|-------|\n"
            for config in summary['discovered_configs']:
                report += f"| `{config['path']}` | {config['depth']} |\n"
            report += "\n</details>\n\n"

        # Issues section
        if issues:
            report += "### ❌ Validation Issues\n\n"
            for i, issue in enumerate(issues, 1):
                report += f"**Issue {i}:** `{issue['file']}`\n"
                report += f"- **Type:** {issue['type']}\n"
                report += f"- **Details:** {issue['message']}\n\n"

        # Recommendations
        report += "<details>\n<summary><strong>Configuration Best Practices</strong></summary>\n\n"
        report += "1. ✅ Only override allowed settings in subdirectory configs\n"
        report += "2. ✅ Never commit API keys or secrets in config files\n"
        report += "3. ✅ Use `_merge_strategy` directive to control merge behavior\n"
        report += "4. ✅ Keep subdirectory configs focused on path-specific overrides\n"
        report += "5. ✅ Document why each subdirectory config is needed\n"
        report += "\n</details>\n"

        return report

    def _prepare_pr_configs(self) -> str:
        try:
            conf_file = get_settings().find_file("configuration.toml")
            dynconf_kwargs = {'core_loaders': [],  # DISABLE default loaders, otherwise will load toml files more than once.
                 'loaders': ['pr_agent.custom_merge_loader'],
                 # Use a custom loader to merge sections, but overwrite their overlapping values. Do not use ENV variables.
                 'merge_enabled': True
                 # Merge multiple TOML files; prevent full section overwrite—only overlapping keys in sections overwrite prior ones.
             }
            conf_settings = Dynaconf(settings_files=[conf_file],
                                     # Security: Disable all dynamic loading features
                                     load_dotenv=False,  # Don't load .env files
                                     envvar_prefix=False,
                                     **dynconf_kwargs
                                     )
        except Exception as e:
            get_logger().error("Caught exception during Dynaconf loading. Returning empty dict",
                               artifact={"exception": e})
            conf_settings = {}
        configuration_headers = [header.lower() for header in conf_settings.keys()]
        relevant_configs = {
            header: configs for header, configs in get_settings().to_dict().items()
            if (header.lower().startswith("pr_") or header.lower().startswith("config")) and header.lower() in configuration_headers
        }

        skip_keys = ['ai_disclaimer', 'ai_disclaimer_title', 'ANALYTICS_FOLDER', 'secret_provider', "skip_keys", "app_id", "redirect",
                     'trial_prefix_message', 'no_eligible_message', 'identity_provider', 'ALLOWED_REPOS',
                     'APP_NAME', 'PERSONAL_ACCESS_TOKEN', 'shared_secret', 'key', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'user_token',
                     'private_key', 'private_key_id', 'client_id', 'client_secret', 'token', 'bearer_token', 'jira_api_token','webhook_secret']
        partial_skip_keys = ['key', 'secret', 'token', 'private']
        extra_skip_keys = get_settings().config.get('config.skip_keys', [])
        if extra_skip_keys:
            skip_keys.extend(extra_skip_keys)
        skip_keys_lower = [key.lower() for key in skip_keys]


        markdown_text = "<details> <summary><strong>🛠️ PR-Agent Configurations:</strong></summary> \n\n"
        markdown_text += f"\n\n```yaml\n\n"
        for header, configs in relevant_configs.items():
            if configs:
                markdown_text += "\n\n"
                markdown_text += f"==================== {header} ===================="
            for key, value in configs.items():
                if key.lower() in skip_keys_lower:
                    continue
                if any(skip_key in key.lower() for skip_key in partial_skip_keys):
                    continue
                markdown_text += f"\n{header.lower()}.{key.lower()} = {repr(value) if isinstance(value, str) else value}"
                markdown_text += "  "
        markdown_text += "\n```"
        markdown_text += "\n</details>\n"
        get_logger().info(f"Possible Configurations outputted to PR comment", artifact=markdown_text)
        return markdown_text
