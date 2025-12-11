"""
Path-scoped configuration system for PR-Agent.

This module enables multiple .pr_agent.toml files in subdirectories with path-based
rule merging, allowing teams to customize behavior for different parts of a monorepo.
"""

from pr_agent.path_config.config_discovery import ConfigDiscovery
from pr_agent.path_config.config_merger import ConfigMerger, MergeStrategy
from pr_agent.path_config.config_resolver import ConfigResolver

__all__ = [
    'ConfigDiscovery',
    'ConfigMerger',
    'ConfigResolver',
    'MergeStrategy',
]
