# AGPL-3.0 License

"""
Check orchestration and execution management.
"""

import asyncio
from typing import Optional

from pr_agent.checks.base_check import BaseCheck
from pr_agent.checks.check_context import CheckContext
from pr_agent.checks.check_result import CheckResult
from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class CheckOrchestrator:
    """
    Manages the execution of multiple checks and aggregates results.

    Handles parallel execution, result aggregation, and reporting
    to the git provider.
    """

    def __init__(self, checks: list[BaseCheck]):
        """
        Initialize the orchestrator with a list of checks.

        Args:
            checks: List of check instances to execute
        """
        self.checks = checks
        self.logger = get_logger()

    async def run_all(self, context: CheckContext) -> dict[str, CheckResult]:
        """
        Execute all checks and aggregate results.

        Args:
            context: Check context with PR information

        Returns:
            Dictionary mapping check names to results
        """
        parallel_execution = get_settings().get("checks", {}).get("parallel_execution", True)

        if parallel_execution:
            return await self._run_parallel(context)
        else:
            return await self._run_sequential(context)

    async def _run_parallel(self, context: CheckContext) -> dict[str, CheckResult]:
        """
        Execute checks in parallel.

        Args:
            context: Check context

        Returns:
            Results dictionary
        """
        self.logger.info(f"Running {len(self.checks)} checks in parallel")

        tasks = []
        for check in self.checks:
            tasks.append(self._run_single_check(check, context))

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for check, result in zip(self.checks, results_list):
            if isinstance(result, Exception):
                self.logger.error(f"Check {check.name} failed with exception: {result}")
                results[check.name] = CheckResult(
                    passed=False,
                    message=f"Check failed with error: {str(result)}",
                    severity="error"
                )
            else:
                results[check.name] = result

        return results

    async def _run_sequential(self, context: CheckContext) -> dict[str, CheckResult]:
        """
        Execute checks sequentially.

        Args:
            context: Check context

        Returns:
            Results dictionary
        """
        self.logger.info(f"Running {len(self.checks)} checks sequentially")

        results = {}
        for check in self.checks:
            try:
                result = await self._run_single_check(check, context)
                results[check.name] = result
            except Exception as e:
                self.logger.error(f"Check {check.name} failed with exception: {e}")
                results[check.name] = CheckResult(
                    passed=False,
                    message=f"Check failed with error: {str(e)}",
                    severity="error"
                )

        return results

    async def _run_single_check(self, check: BaseCheck, context: CheckContext) -> CheckResult:
        """
        Execute a single check with logging.

        Args:
            check: Check to execute
            context: Check context

        Returns:
            Check result
        """
        self.logger.info(f"Running check: {check.name} ({check.mode} mode)")

        # Filter context for this check
        filtered_context = check.filter_context(context)

        # Skip if no relevant files
        if filtered_context.filtered_files is not None and len(filtered_context.filtered_files) == 0:
            self.logger.info(f"Check {check.name} skipped - no matching files")
            return CheckResult(
                passed=True,
                message="No relevant files to check",
                severity="info"
            )

        # Run the check
        result = await check.run(filtered_context)

        self.logger.info(f"Check {check.name} completed: {result}")
        return result

    def has_blocking_failures(self, results: dict[str, CheckResult]) -> bool:
        """
        Determine if any blocking checks failed.

        Args:
            results: Results dictionary

        Returns:
            True if any blocking check failed
        """
        for check in self.checks:
            if check.mode == "blocking":
                result = results.get(check.name)
                if result and not result.passed:
                    return True
        return False
