# AGPL-3.0 License
# Copyright (c) Qodo Ltd.

"""
Pre-merge check engine for PR-Agent.

This module provides a framework for running configurable named checks
that can act as advisory or blocking gates before merge.
"""

from pr_agent.checks.base_check import BaseCheck
from pr_agent.checks.check_context import CheckContext
from pr_agent.checks.check_result import CheckResult, CheckDetail

__all__ = [
    "BaseCheck",
    "CheckContext",
    "CheckResult",
    "CheckDetail",
]
