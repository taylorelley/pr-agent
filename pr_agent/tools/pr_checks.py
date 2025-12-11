# AGPL-3.0 License

"""
PR Checks tool - runs configurable pre-merge checks.

This tool executes custom checks against a PR and reports results
either as GitHub check runs or as PR comments.
"""

from functools import partial
from typing import Optional

from pr_agent.algo.ai_handlers.base_ai_handler import BaseAiHandler
from pr_agent.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler
from pr_agent.algo.pr_processing import get_pr_diff
from pr_agent.checks.base_check import BaseCheck
from pr_agent.checks.check_context import CheckContext
from pr_agent.checks.check_result import CheckResult
from pr_agent.checks.orchestrator import CheckOrchestrator
from pr_agent.checks.built_in_checks import (
    FreeTextRuleCheck,
    PatternCheck,
    FileSizeCheck,
    RequiredFilesCheck,
    ForbiddenPatternsCheck,
)
from pr_agent.config_loader import get_settings
from pr_agent.git_providers.git_provider import get_git_provider_with_context
from pr_agent.log import get_logger


class PRChecks:
    """
    PR Checks tool - executes pre-merge checks and reports results.
    """

    def __init__(
        self,
        pr_url: str,
        args: list = None,
        ai_handler: partial[BaseAiHandler] = LiteLLMAIHandler
    ):
        """
        Initialize PR Checks tool.

        Args:
            pr_url: URL of the PR to check
            args: Command-line arguments
            ai_handler: AI handler for free-text rules
        """
        self.pr_url = pr_url
        self.git_provider = get_git_provider_with_context(pr_url)
        self.ai_handler = ai_handler
        self.args = args or []
        self.logger = get_logger()

    async def run(self):
        """Execute checks and report results."""
        try:
            self.logger.info(f"Running checks on PR: {self.pr_url}")

            # Load checks from configuration
            checks = await self._load_checks_from_config()

            if not checks:
                self.logger.info("No checks configured")
                await self._publish_comment("ℹ️ No checks are currently configured for this repository.")
                return

            # Build check context
            context = await self._build_check_context()

            # Execute checks
            orchestrator = CheckOrchestrator(checks)
            results = await orchestrator.run_all(context)

            # Report results
            await self._report_results(checks, results)

            self.logger.info(f"Checks completed: {len(results)} checks run")

        except Exception as e:
            self.logger.error(f"Failed to run checks: {e}", exc_info=True)
            await self._publish_comment(f"❌ Error running checks: {str(e)}")

    async def _load_checks_from_config(self) -> list[BaseCheck]:
        """
        Load checks from repository configuration.

        Looks for check definitions in .pr_agent.toml under [checks.*] sections.
        """
        checks = []
        settings = get_settings()

        # Check if checks are enabled
        if not settings.get("checks", {}).get("enable_auto_checks", False):
            self.logger.debug("Auto checks are not enabled")
            return checks

        try:
            # Get all check configurations
            # The configuration format is: [checks.<check_name>]
            checks_config = settings.get("checks", {})

            for key in checks_config.keys():
                # Skip meta-configuration keys
                if key in ["enable_auto_checks", "default_mode", "parallel_execution",
                          "enable_auto_checks_feedback", "excluded_checks_list",
                          "persistent_comment", "enable_help_text", "final_update_message"]:
                    continue

                # This is a check configuration
                check_config = checks_config[key]

                # Skip if not a dict (might be a simple value)
                if not isinstance(check_config, dict):
                    continue

                # Get check type
                check_type = check_config.get("type", "pattern")

                # Create appropriate check instance
                check = await self._create_check(key, check_type, check_config)
                if check:
                    checks.append(check)

        except Exception as e:
            self.logger.error(f"Failed to load checks from config: {e}")

        return checks

    async def _create_check(self, name: str, check_type: str, config: dict) -> Optional[BaseCheck]:
        """Create a check instance from configuration."""
        try:
            # Extract common parameters
            description = config.get("description", name)
            mode = config.get("mode", get_settings().get("checks", {}).get("default_mode", "advisory"))
            paths = config.get("paths", None)
            exclude_paths = config.get("exclude_paths", None)

            if check_type == "free_text":
                return FreeTextRuleCheck(
                    name=name,
                    description=description,
                    rule=config.get("rule", ""),
                    mode=mode,
                    paths=paths,
                    exclude_paths=exclude_paths,
                    ai_handler=self.ai_handler
                )

            elif check_type == "pattern":
                return PatternCheck(
                    name=name,
                    description=description,
                    pattern=config.get("pattern", ""),
                    message=config.get("message", "Pattern detected"),
                    mode=mode,
                    invert=config.get("invert", False),
                    paths=paths,
                    exclude_paths=exclude_paths
                )

            elif check_type == "file_size":
                return FileSizeCheck(
                    name=name,
                    description=description,
                    max_file_size_kb=config.get("max_file_size_kb"),
                    max_pr_lines=config.get("max_pr_lines"),
                    mode=mode,
                    paths=paths,
                    exclude_paths=exclude_paths
                )

            elif check_type == "required_files":
                return RequiredFilesCheck(
                    name=name,
                    description=description,
                    trigger_files=config.get("trigger_files", []),
                    required_files=config.get("required_files", []),
                    message=config.get("message", "Required files not modified"),
                    mode=mode,
                    paths=paths,
                    exclude_paths=exclude_paths
                )

            elif check_type == "forbidden_patterns":
                # Convert custom patterns if provided
                custom_patterns = None
                if "custom_patterns" in config:
                    custom_patterns = [
                        (p["pattern"], p["message"])
                        for p in config["custom_patterns"]
                    ]

                return ForbiddenPatternsCheck(
                    name=name,
                    description=description,
                    custom_patterns=custom_patterns,
                    mode=mode,
                    paths=paths,
                    exclude_paths=exclude_paths
                )

            else:
                self.logger.warning(f"Unknown check type: {check_type}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to create check '{name}': {e}")
            return None

    async def _build_check_context(self) -> CheckContext:
        """Build context for check execution."""
        # Get PR data
        pr_info = await self.git_provider.get_pr()

        # Get diff files
        patches = await get_pr_diff(self.git_provider, self.git_provider.incremental)
        files_changed = [p.filename for p in patches]

        # Build context
        context = CheckContext(
            pr_url=self.pr_url,
            pr_title=pr_info.get("title", ""),
            pr_description=self.git_provider.get_pr_description(),
            pr_author=pr_info.get("user", {}).get("login", ""),
            pr_labels=[label.get("name", "") for label in pr_info.get("labels", [])],
            files_changed=files_changed,
            patches=patches,
            git_provider=self.git_provider,
            config=get_settings().to_dict()
        )

        return context

    async def _report_results(self, checks: list[BaseCheck], results: dict[str, CheckResult]):
        """
        Report check results via check runs and/or comments.
        """
        # Try to create check runs if supported
        check_runs_created = await self._create_check_runs(checks, results)

        # Always create a comment with results summary
        await self._create_results_comment(checks, results, check_runs_created)

    async def _create_check_runs(self, checks: list[BaseCheck], results: dict[str, CheckResult]) -> bool:
        """
        Create GitHub check runs for each check.

        Returns True if check runs were created successfully.
        """
        try:
            for check in checks:
                result = results.get(check.name)
                if not result:
                    continue

                # Determine conclusion
                conclusion = "success" if result.passed else "failure"
                if result.severity == "info":
                    conclusion = "neutral"

                # Build output
                output = {
                    "title": f"{check.description}",
                    "summary": result.message,
                }

                # Add details if any
                if result.details:
                    text_lines = []
                    for detail in result.details:
                        location = f"{detail.file_path}"
                        if detail.line_number:
                            location += f":{detail.line_number}"
                        text_lines.append(f"**{location}**: {detail.message}")
                        if detail.suggestion:
                            text_lines.append(f"  _Suggestion: {detail.suggestion}_")

                    output["text"] = "\n\n".join(text_lines)

                # Create check run
                check_id = self.git_provider.create_check_run(
                    name=f"PR-Agent: {check.name}",
                    status="completed",
                    conclusion=conclusion,
                    output=output
                )

                if check_id:
                    self.logger.debug(f"Created check run for '{check.name}' with ID {check_id}")

            return True

        except Exception as e:
            self.logger.warning(f"Could not create check runs (provider may not support them): {e}")
            return False

    async def _create_results_comment(self, checks: list[BaseCheck], results: dict[str, CheckResult], check_runs_created: bool):
        """
        Create or update a comment with check results.
        """
        # Build comment markdown
        lines = ["## 🔍 PR Checks Results\n"]

        # Add check run notice if created
        if check_runs_created:
            lines.append("_Check details are also available in the Checks tab above._\n")

        # Count results
        passed_count = sum(1 for r in results.values() if r.passed)
        failed_count = len(results) - passed_count

        # Add summary
        if failed_count == 0:
            lines.append(f"✅ **All {len(results)} checks passed!**\n")
        else:
            lines.append(f"⚠️ **{failed_count} of {len(results)} checks failed**\n")

        # Add individual check results
        for check in checks:
            result = results.get(check.name)
            if not result:
                continue

            # Status icon
            if result.passed:
                icon = "✅"
            elif result.severity == "error":
                icon = "❌"
            elif result.severity == "warning":
                icon = "⚠️"
            else:
                icon = "ℹ️"

            # Mode badge
            mode_badge = "🔒 **BLOCKING**" if check.mode == "blocking" else "💡 Advisory"

            lines.append(f"\n### {icon} {check.name} ({mode_badge})")
            lines.append(f"\n{result.message}\n")

            # Add details if any
            if result.details:
                lines.append("<details>")
                lines.append(f"<summary>Details ({len(result.details)} finding(s))</summary>\n")

                for detail in result.details:
                    location = f"`{detail.file_path}`"
                    if detail.line_number:
                        location += f" line {detail.line_number}"

                    lines.append(f"- {location}: {detail.message}")
                    if detail.suggestion:
                        lines.append(f"  - _💡 {detail.suggestion}_")

                lines.append("\n</details>\n")

        # Add footer
        lines.append("\n---")
        lines.append("\n_Checks can be configured in `.pr_agent.toml`. See documentation for details._")

        comment_body = "\n".join(lines)

        # Publish comment
        await self._publish_comment(comment_body)

    async def _publish_comment(self, comment: str):
        """Publish a comment on the PR."""
        try:
            if get_settings().get("checks", {}).get("persistent_comment", True):
                # Use persistent comment
                self.git_provider.publish_persistent_comment(
                    comment,
                    initial_header="## 🔍 PR Checks Results",
                    name="checks",
                    final_update_message=get_settings().get("checks", {}).get("final_update_message", False)
                )
            else:
                # Regular comment
                self.git_provider.publish_comment(comment)

        except Exception as e:
            self.logger.error(f"Failed to publish comment: {e}")
