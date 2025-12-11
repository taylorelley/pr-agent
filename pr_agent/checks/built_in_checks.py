# AGPL-3.0 License

"""
Built-in check implementations.

Provides commonly-needed check types that can be configured
via TOML without writing custom code.
"""

import re
import json
from typing import Optional, Literal
from functools import partial

from pr_agent.checks.base_check import BaseCheck
from pr_agent.checks.check_context import CheckContext
from pr_agent.checks.check_result import CheckResult, CheckDetail
from pr_agent.algo.ai_handlers.base_ai_handler import BaseAiHandler
from pr_agent.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler
from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class FreeTextRuleCheck(BaseCheck):
    """
    AI-powered check that evaluates code against a custom rule.

    Uses LLM to interpret and apply custom rules written in natural language.
    Example: "All new functions must have corresponding unit tests"
    """

    def __init__(
        self,
        name: str,
        description: str,
        rule: str,
        mode: Literal["advisory", "blocking"] = "advisory",
        paths: Optional[list[str]] = None,
        exclude_paths: Optional[list[str]] = None,
        ai_handler: partial[BaseAiHandler] = LiteLLMAIHandler
    ):
        """
        Initialize free-text rule check.

        Args:
            name: Check identifier
            description: Human-readable description
            rule: Natural language rule to evaluate
            mode: Check behavior
            paths: File patterns to include
            exclude_paths: File patterns to exclude
            ai_handler: AI handler for rule evaluation
        """
        super().__init__(name, description, mode, paths, exclude_paths)
        self.rule = rule
        self.ai_handler = ai_handler()
        self.logger = get_logger()

    async def run(self, context: CheckContext) -> CheckResult:
        """Evaluate the rule using AI."""
        if not context.filtered_files:
            return CheckResult(
                passed=True,
                message="No files to check",
                severity="info"
            )

        try:
            # Build prompt from template
            from jinja2 import Template

            # Get relevant patches for filtered files
            relevant_patches = [
                p for p in context.patches
                if p.filename in context.filtered_files
            ]

            # Load prompt template
            settings = get_settings()
            prompt_template = settings.pr_checks_prompts.user

            template = Template(prompt_template)
            prompt = template.render(
                rule_description=self.rule,
                pr_title=context.pr_title,
                pr_description=context.pr_description,
                files=[{
                    "filename": p.filename,
                    "patch": p.patch
                } for p in relevant_patches]
            )

            # Call AI model
            system_prompt = settings.pr_checks_prompts.system
            response, _, _ = await self.ai_handler.chat_completion(
                model=get_settings().config.model,
                temperature=0.2,
                system=system_prompt,
                user=prompt
            )

            # Parse JSON response
            result_data = json.loads(response)

            # Convert to CheckResult
            details = [
                CheckDetail(
                    file_path=d.get("file_path", ""),
                    line_number=d.get("line_number"),
                    message=d.get("message", ""),
                    suggestion=d.get("suggestion")
                )
                for d in result_data.get("details", [])
            ]

            return CheckResult(
                passed=result_data.get("passed", False),
                message=result_data.get("message", "Check evaluation completed"),
                details=details,
                severity=result_data.get("severity", "info")
            )

        except Exception as e:
            self.logger.error(f"FreeTextRuleCheck failed: {e}")
            return CheckResult(
                passed=False,
                message=f"Check execution error: {str(e)}",
                severity="error"
            )


class PatternCheck(BaseCheck):
    """
    Regex-based pattern matching check.

    Searches for forbidden patterns or ensures required patterns are present.
    """

    def __init__(
        self,
        name: str,
        description: str,
        pattern: str,
        message: str = "Pattern match found",
        mode: Literal["advisory", "blocking"] = "advisory",
        invert: bool = False,
        paths: Optional[list[str]] = None,
        exclude_paths: Optional[list[str]] = None
    ):
        """
        Initialize pattern check.

        Args:
            name: Check identifier
            description: Human-readable description
            pattern: Regular expression pattern
            message: Message to show on match
            mode: Check behavior
            invert: If True, fail when pattern is NOT found (require pattern)
            paths: File patterns to include
            exclude_paths: File patterns to exclude
        """
        super().__init__(name, description, mode, paths, exclude_paths)
        self.pattern = re.compile(pattern)
        self.message_template = message
        self.invert = invert
        self.logger = get_logger()

    async def run(self, context: CheckContext) -> CheckResult:
        """Search for pattern in changed files."""
        if not context.filtered_files:
            return CheckResult(
                passed=True,
                message="No files to check",
                severity="info"
            )

        details = []

        for patch in context.patches:
            if patch.filename not in context.filtered_files:
                continue

            # Search in patch content
            for i, line in enumerate(patch.patch.split('\n'), 1):
                if self.pattern.search(line):
                    details.append(CheckDetail(
                        file_path=patch.filename,
                        line_number=i,
                        message=self.message_template
                    ))

        # Determine pass/fail based on invert flag
        if self.invert:
            # Should REQUIRE pattern - fail if not found
            passed = len(details) > 0
            if not passed:
                message = f"Required pattern not found: {self.pattern.pattern}"
            else:
                message = f"Required pattern found {len(details)} time(s)"
        else:
            # Should FORBID pattern - fail if found
            passed = len(details) == 0
            if not passed:
                message = f"Forbidden pattern found {len(details)} time(s): {self.pattern.pattern}"
            else:
                message = "No forbidden patterns detected"

        return CheckResult(
            passed=passed,
            message=message,
            details=details,
            severity="warning" if not passed else "info"
        )


class FileSizeCheck(BaseCheck):
    """
    Check for file and PR size limits.

    Prevents overly large files or PRs that are difficult to review.
    """

    def __init__(
        self,
        name: str,
        description: str,
        max_file_size_kb: Optional[int] = None,
        max_pr_lines: Optional[int] = None,
        mode: Literal["advisory", "blocking"] = "advisory",
        paths: Optional[list[str]] = None,
        exclude_paths: Optional[list[str]] = None
    ):
        """
        Initialize file size check.

        Args:
            name: Check identifier
            description: Human-readable description
            max_file_size_kb: Maximum file size in KB
            max_pr_lines: Maximum total lines changed in PR
            mode: Check behavior
            paths: File patterns to include
            exclude_paths: File patterns to exclude
        """
        super().__init__(name, description, mode, paths, exclude_paths)
        self.max_file_size_kb = max_file_size_kb
        self.max_pr_lines = max_pr_lines
        self.logger = get_logger()

    async def run(self, context: CheckContext) -> CheckResult:
        """Check file and PR sizes."""
        if not context.filtered_files:
            return CheckResult(
                passed=True,
                message="No files to check",
                severity="info"
            )

        details = []
        total_lines = 0

        for patch in context.patches:
            if patch.filename not in context.filtered_files:
                continue

            # Count lines changed
            lines_changed = patch.num_plus_lines + patch.num_minus_lines
            total_lines += lines_changed

            # Check file size if limit is set
            if self.max_file_size_kb:
                # Estimate file size from patch (not perfect but reasonable)
                # In a real implementation, you'd fetch actual file size from git provider
                patch_size_kb = len(patch.patch.encode('utf-8')) / 1024

                if patch_size_kb > self.max_file_size_kb:
                    details.append(CheckDetail(
                        file_path=patch.filename,
                        message=f"File change size ({patch_size_kb:.1f} KB) exceeds limit ({self.max_file_size_kb} KB)"
                    ))

        # Check total PR lines if limit is set
        if self.max_pr_lines and total_lines > self.max_pr_lines:
            details.append(CheckDetail(
                file_path="PR",
                message=f"Total lines changed ({total_lines}) exceeds limit ({self.max_pr_lines})"
            ))

        passed = len(details) == 0

        if passed:
            message = f"Size check passed (Total: {total_lines} lines)"
        else:
            message = f"Size limits exceeded ({len(details)} violation(s))"

        return CheckResult(
            passed=passed,
            message=message,
            details=details,
            severity="warning" if not passed else "info"
        )


class RequiredFilesCheck(BaseCheck):
    """
    Ensure certain files are modified together.

    Example: If package.json changes, package-lock.json should also change.
    """

    def __init__(
        self,
        name: str,
        description: str,
        trigger_files: list[str],
        required_files: list[str],
        message: str = "Required files not modified",
        mode: Literal["advisory", "blocking"] = "advisory",
        paths: Optional[list[str]] = None,
        exclude_paths: Optional[list[str]] = None
    ):
        """
        Initialize required files check.

        Args:
            name: Check identifier
            description: Human-readable description
            trigger_files: Patterns for files that trigger the requirement
            required_files: Patterns for files that must also be modified
            message: Message to show if required files are missing
            mode: Check behavior
            paths: File patterns to include
            exclude_paths: File patterns to exclude
        """
        super().__init__(name, description, mode, paths, exclude_paths)
        self.trigger_files = trigger_files
        self.required_files = required_files
        self.message_template = message
        self.logger = get_logger()

    async def run(self, context: CheckContext) -> CheckResult:
        """Check if required files are modified together."""
        changed_files = set(context.files_changed)

        # Check if any trigger files were modified
        import fnmatch
        trigger_matched = any(
            any(fnmatch.fnmatch(f, pattern) for pattern in self.trigger_files)
            for f in changed_files
        )

        if not trigger_matched:
            return CheckResult(
                passed=True,
                message="Trigger files not modified",
                severity="info"
            )

        # Check if required files were also modified
        required_matched = all(
            any(fnmatch.fnmatch(f, pattern) for f in changed_files)
            for pattern in self.required_files
        )

        if required_matched:
            return CheckResult(
                passed=True,
                message="All required files were modified",
                severity="info"
            )

        # Find which required files are missing
        missing = [
            pattern for pattern in self.required_files
            if not any(fnmatch.fnmatch(f, pattern) for f in changed_files)
        ]

        details = [
            CheckDetail(
                file_path="PR",
                message=f"Missing required file pattern: {pattern}"
            )
            for pattern in missing
        ]

        return CheckResult(
            passed=False,
            message=f"{self.message_template} ({len(missing)} missing)",
            details=details,
            severity="warning"
        )


class ForbiddenPatternsCheck(BaseCheck):
    """
    Check for secrets and sensitive data patterns.

    Blocks commits containing common secret patterns like API keys,
    passwords, and other sensitive information.
    """

    # Common secret patterns (basic set - extend as needed)
    DEFAULT_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[a-z0-9]{20,}', "API key detected"),
        (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?[^\s]{8,}', "Hardcoded password detected"),
        (r'(?i)(secret|token)\s*[=:]\s*["\']?[a-z0-9_\-]{20,}', "Secret/token detected"),
        (r'(?i)(aws_access_key_id|aws_secret_access_key)', "AWS credentials detected"),
        (r'-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----', "Private key detected"),
        (r'(?i)Bearer\s+[a-zA-Z0-9_\-\.]{20,}', "Bearer token detected"),
    ]

    def __init__(
        self,
        name: str,
        description: str,
        custom_patterns: Optional[list[tuple[str, str]]] = None,
        mode: Literal["advisory", "blocking"] = "blocking",  # Default to blocking for security
        paths: Optional[list[str]] = None,
        exclude_paths: Optional[list[str]] = None
    ):
        """
        Initialize forbidden patterns check.

        Args:
            name: Check identifier
            description: Human-readable description
            custom_patterns: Additional patterns to check (pattern, message) tuples
            mode: Check behavior
            paths: File patterns to include
            exclude_paths: File patterns to exclude (e.g., ["**/*.env.example"])
        """
        super().__init__(name, description, mode, paths, exclude_paths)

        # Compile all patterns
        self.patterns = [
            (re.compile(pattern), message)
            for pattern, message in self.DEFAULT_PATTERNS
        ]

        if custom_patterns:
            self.patterns.extend([
                (re.compile(pattern), message)
                for pattern, message in custom_patterns
            ])

        self.logger = get_logger()

    async def run(self, context: CheckContext) -> CheckResult:
        """Search for forbidden secret patterns."""
        if not context.filtered_files:
            return CheckResult(
                passed=True,
                message="No files to check",
                severity="info"
            )

        details = []

        for patch in context.patches:
            if patch.filename not in context.filtered_files:
                continue

            # Only check added lines (lines starting with +)
            for i, line in enumerate(patch.patch.split('\n'), 1):
                if not line.startswith('+'):
                    continue

                # Remove the + prefix
                content = line[1:]

                # Check all patterns
                for pattern, message in self.patterns:
                    if pattern.search(content):
                        details.append(CheckDetail(
                            file_path=patch.filename,
                            line_number=i,
                            message=message,
                            suggestion="Remove sensitive data and use environment variables or secret management"
                        ))

        passed = len(details) == 0

        if passed:
            message = "No secrets or sensitive data detected"
        else:
            message = f"⚠️ SECURITY: {len(details)} potential secret(s) detected"

        return CheckResult(
            passed=passed,
            message=message,
            details=details,
            severity="error" if not passed else "info"
        )
