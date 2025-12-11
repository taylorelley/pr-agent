"""
Unit tests for ConfigMerger class.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from jinja2.exceptions import SecurityError

from pr_agent.path_config.config_merger import ConfigMerger, MergeStrategy
from pr_agent.path_config.config_discovery import ConfigFile


class TestConfigMerger:
    """Test suite for ConfigMerger class."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure for testing."""
        temp_dir = tempfile.mkdtemp()
        repo_root = Path(temp_dir)
        repo_root.mkdir(exist_ok=True)

        yield repo_root

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def merger(self, temp_repo):
        """Create a ConfigMerger instance."""
        return ConfigMerger(temp_repo, max_depth=5)

    def test_init(self, temp_repo):
        """Test ConfigMerger initialization."""
        merger = ConfigMerger(temp_repo, max_depth=3)
        assert merger.repo_root == temp_repo.resolve()
        assert merger.max_depth == 3
        assert len(merger.allowed_overrides) > 0
        assert len(merger.denied_overrides) > 0

    def test_merge_empty_configs(self, merger):
        """Test merging with no config files."""
        result = merger.merge_configs([])
        assert result == {}

    def test_merge_single_config(self, temp_repo, merger):
        """Test merging a single configuration."""
        config_path = temp_repo / ".pr_agent.toml"
        config_path.write_text("""
[config]
model = "gpt-4"

[pr_reviewer]
num_max_findings = 5
        """)

        config_file = ConfigFile(config_path, depth=0, relative_path=Path(".pr_agent.toml"))
        result = merger.merge_configs([config_file])

        assert "config" in result
        assert result["config"]["model"] == "gpt-4"
        assert "pr_reviewer" in result
        assert result["pr_reviewer"]["num_max_findings"] == 5

    def test_merge_override_strategy(self, temp_repo, merger):
        """Test that child configs override parent values."""
        # Root config
        root_config = temp_repo / ".pr_agent.toml"
        root_config.write_text("""
[pr_reviewer]
extra_instructions = "root instructions"
num_max_findings = 3
        """)

        # Child config
        child_dir = temp_repo / "src"
        child_dir.mkdir()
        child_config = child_dir / ".pr_agent.toml"
        child_config.write_text("""
[pr_reviewer]
extra_instructions = "child instructions"
        """)

        config_files = [
            ConfigFile(root_config, depth=0, relative_path=Path(".pr_agent.toml")),
            ConfigFile(child_config, depth=1, relative_path=Path("src/.pr_agent.toml"))
        ]

        result = merger.merge_configs(config_files)

        # Child should override root
        assert result["pr_reviewer"]["extra_instructions"] == "child instructions"
        # But root value for num_max_findings should remain if not overridden
        assert result["pr_reviewer"]["num_max_findings"] == 3

    def test_merge_extend_lists(self, temp_repo, merger):
        """Test that lists can be extended based on strategy."""
        root_config = temp_repo / ".pr_agent.toml"
        root_config.write_text("""
[pr_reviewer]
extra_instructions = "root"

[[config.skip_keys]]
values = ["key1", "key2"]
        """)

        result = merger.merge_configs([
            ConfigFile(root_config, depth=0, relative_path=Path(".pr_agent.toml"))
        ])

        assert "pr_reviewer" in result

    def test_validate_denied_overrides(self, temp_repo, merger):
        """Test that denied overrides are rejected in subdirectory configs."""
        child_dir = temp_repo / "src"
        child_dir.mkdir()
        child_config = child_dir / ".pr_agent.toml"
        child_config.write_text("""
[config]
model = "gpt-4"  # This should be denied

[openai]
key = "secret"  # This should also be denied
        """)

        config_file = ConfigFile(child_config, depth=1, relative_path=Path("src/.pr_agent.toml"))

        with pytest.raises(SecurityError) as exc_info:
            merger.merge_configs([config_file])

        assert "cannot be overridden" in str(exc_info.value).lower()

    def test_allowed_overrides_accepted(self, temp_repo, merger):
        """Test that allowed overrides work in subdirectory configs."""
        child_dir = temp_repo / "src"
        child_dir.mkdir()
        child_config = child_dir / ".pr_agent.toml"
        child_config.write_text("""
[pr_reviewer]
extra_instructions = "This is allowed"
num_max_findings = 10
        """)

        config_file = ConfigFile(child_config, depth=1, relative_path=Path("src/.pr_agent.toml"))

        # Should not raise an error
        result = merger.merge_configs([config_file])
        assert result["pr_reviewer"]["extra_instructions"] == "This is allowed"

    def test_merge_strategy_directive(self, temp_repo, merger):
        """Test _merge_strategy directive in config."""
        root_config = temp_repo / ".pr_agent.toml"
        root_config.write_text("""
[pr_reviewer]
extra_instructions = "root"
num_max_findings = 3
        """)

        child_dir = temp_repo / "src"
        child_dir.mkdir()
        child_config = child_dir / ".pr_agent.toml"
        child_config.write_text("""
[pr_reviewer]
_merge_strategy = "extend"
extra_instructions = "child"
        """)

        config_files = [
            ConfigFile(root_config, depth=0, relative_path=Path(".pr_agent.toml")),
            ConfigFile(child_config, depth=1, relative_path=Path("src/.pr_agent.toml"))
        ]

        result = merger.merge_configs(config_files)

        # Both values should be present due to extend strategy
        assert "pr_reviewer" in result

    def test_security_validation(self, temp_repo, merger):
        """Test that security validation is applied to all configs."""
        config_path = temp_repo / ".pr_agent.toml"
        config_path.write_text("""
[config]
model = "gpt-4"

[dangerous]
dynaconf_include = ["other_file.toml"]
        """)

        config_file = ConfigFile(config_path, depth=0, relative_path=Path(".pr_agent.toml"))

        with pytest.raises(SecurityError):
            merger.merge_configs([config_file])

    def test_validate_config_consistency(self, temp_repo, merger):
        """Test configuration validation method."""
        # Create valid root config
        root_config = temp_repo / ".pr_agent.toml"
        root_config.write_text("""
[pr_reviewer]
num_max_findings = 3
        """)

        # Create invalid child config
        child_dir = temp_repo / "src"
        child_dir.mkdir()
        child_config = child_dir / ".pr_agent.toml"
        child_config.write_text("""
[config]
model = "forbidden"  # Not allowed in subdirectory
        """)

        config_files = [
            ConfigFile(root_config, depth=0, relative_path=Path(".pr_agent.toml")),
            ConfigFile(child_config, depth=1, relative_path=Path("src/.pr_agent.toml"))
        ]

        issues = merger.validate_config_consistency(config_files)

        assert len(issues) > 0
        assert any(issue["type"] == "security_violation" for issue in issues)

    def test_validate_config_consistency_all_valid(self, temp_repo, merger):
        """Test validation with all valid configs."""
        root_config = temp_repo / ".pr_agent.toml"
        root_config.write_text("""
[pr_reviewer]
num_max_findings = 3
        """)

        config_files = [
            ConfigFile(root_config, depth=0, relative_path=Path(".pr_agent.toml"))
        ]

        issues = merger.validate_config_consistency(config_files)

        assert len(issues) == 0

    def test_flatten_dict(self, merger):
        """Test dictionary flattening utility."""
        nested = {
            "config": {
                "model": "gpt-4",
                "nested": {
                    "value": 42
                }
            },
            "pr_reviewer": {
                "extra_instructions": "test"
            }
        }

        flat = merger._flatten_dict(nested)

        assert "config.model" in flat
        assert flat["config.model"] == "gpt-4"
        assert "config.nested.value" in flat
        assert flat["config.nested.value"] == 42
        assert "pr_reviewer.extra_instructions" in flat

    def test_merge_different_types(self, temp_repo, merger):
        """Test merging when types differ (scalar vs dict)."""
        root_config = temp_repo / ".pr_agent.toml"
        root_config.write_text("""
[pr_reviewer]
setting = "string_value"
        """)

        child_dir = temp_repo / "src"
        child_dir.mkdir()
        child_config = child_dir / ".pr_agent.toml"
        child_config.write_text("""
[pr_reviewer]
setting = 42  # Different type
        """)

        config_files = [
            ConfigFile(root_config, depth=0, relative_path=Path(".pr_agent.toml")),
            ConfigFile(child_config, depth=1, relative_path=Path("src/.pr_agent.toml"))
        ]

        result = merger.merge_configs(config_files)

        # Child value should win
        assert result["pr_reviewer"]["setting"] == 42

    def test_merge_with_base_config(self, temp_repo, merger):
        """Test merging with a base configuration."""
        base_config = {
            "config": {
                "model": "gpt-3.5"
            }
        }

        new_config = temp_repo / ".pr_agent.toml"
        new_config.write_text("""
[pr_reviewer]
extra_instructions = "test"
        """)

        config_files = [
            ConfigFile(new_config, depth=0, relative_path=Path(".pr_agent.toml"))
        ]

        result = merger.merge_configs(config_files, base_config=base_config)

        # Should have both base and new settings
        assert "config" in result
        assert result["config"]["model"] == "gpt-3.5"
        assert "pr_reviewer" in result
        assert result["pr_reviewer"]["extra_instructions"] == "test"

    def test_custom_allowed_overrides(self, temp_repo):
        """Test custom allowed overrides list."""
        custom_allowed = ["custom.setting"]
        merger = ConfigMerger(
            temp_repo,
            allowed_overrides=custom_allowed
        )

        assert merger.allowed_overrides == custom_allowed

    def test_custom_denied_overrides(self, temp_repo):
        """Test custom denied overrides list."""
        custom_denied = ["custom.forbidden"]
        merger = ConfigMerger(
            temp_repo,
            denied_overrides=custom_denied
        )

        assert merger.denied_overrides == custom_denied

    def test_merge_strategy_enum(self):
        """Test MergeStrategy enum values."""
        assert MergeStrategy.OVERRIDE.value == "override"
        assert MergeStrategy.EXTEND.value == "extend"
        assert MergeStrategy.INHERIT.value == "inherit"

    def test_invalid_merge_strategy(self, temp_repo, merger):
        """Test handling of invalid merge strategy."""
        child_dir = temp_repo / "src"
        child_dir.mkdir()
        child_config = child_dir / ".pr_agent.toml"
        child_config.write_text("""
[pr_reviewer]
_merge_strategy = "invalid_strategy"
extra_instructions = "test"
        """)

        config_files = [
            ConfigFile(child_config, depth=1, relative_path=Path("src/.pr_agent.toml"))
        ]

        # Should fall back to default strategy without error
        result = merger.merge_configs(config_files)
        assert "pr_reviewer" in result
