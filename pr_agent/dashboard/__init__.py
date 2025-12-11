# AGPL-3.0 License

"""
Organization-level dashboard for PR-Agent.

This module provides metrics collection, visualization, and
a web API for viewing trends across repositories.
"""

from pr_agent.dashboard.metrics.collector import MetricsCollector

__all__ = [
    "MetricsCollector",
]
