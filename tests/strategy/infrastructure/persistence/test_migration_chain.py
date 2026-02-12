"""
Property-Based Tests for MigrationChain

Feature: persistence-resilience-enhancement, Property 8: Migration chain sequential application

Tests that applying the migration chain from version N to current is equivalent
to applying each individual migration step sequentially.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import Any, Dict

from src.strategy.infrastructure.persistence.migration_chain import MigrationChain


# --- Strategies ---

# Generate simple JSON-safe data dictionaries
json_values = st.recursive(
    st.one_of(
        st.integers(min_value=-10000, max_value=10000),
        st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
        st.text(min_size=0, max_size=20),
        st.booleans(),
        st.none(),
    ),
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=5),
    ),
    max_leaves=10,
)

json_data = st.dictionaries(
    keys=st.text(min_size=1, max_size=15),
    values=json_values,
    min_size=0,
    max_size=8,
)


def make_deterministic_migration(version: int):
    """Create a deterministic migration function for version N -> N+1.

    Each migration adds a marker field so we can verify sequential application.
    """

    def migrate(data: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(data)
        result[f"_migrated_from_v{version}"] = True
        return result

    return migrate


class TestMigrationChainProperties:
    """Property-based tests for MigrationChain"""

    @settings(max_examples=100)
    @given(
        data=json_data,
        start_version=st.integers(min_value=1, max_value=10),
        chain_length=st.integers(min_value=1, max_value=8),
    )
    def test_property_8_migration_chain_sequential_application(
        self,
        data: Dict[str, Any],
        start_version: int,
        chain_length: int,
    ):
        """
        Property 8: Migration chain sequential application

        For any data with schema version N (where N < current version),
        applying the migration chain should produce data with the current
        schema version, and the migration should be equivalent to applying
        each individual migration step sequentially from N to current.

        Feature: persistence-resilience-enhancement, Property 8: Migration chain sequential application
        Validates: Requirements 4.3
        """
        target_version = start_version + chain_length

        # Build a full migration chain
        chain = MigrationChain()
        for v in range(start_version, target_version):
            chain.register(v, make_deterministic_migration(v))

        # Apply the full chain in one call
        result_full = chain.migrate(dict(data), start_version, target_version)

        # Apply each step individually (sequential)
        result_sequential = dict(data)
        for v in range(start_version, target_version):
            single_chain = MigrationChain()
            single_chain.register(v, make_deterministic_migration(v))
            result_sequential = single_chain.migrate(result_sequential, v, v + 1)

        # Both approaches must produce identical results
        assert result_full == result_sequential

        # Verify all migration markers are present
        for v in range(start_version, target_version):
            assert result_full[f"_migrated_from_v{v}"] is True

    @settings(max_examples=100)
    @given(
        data=json_data,
        start_version=st.integers(min_value=1, max_value=20),
    )
    def test_property_8_no_op_when_same_version(
        self,
        data: Dict[str, Any],
        start_version: int,
    ):
        """
        Property 8 (edge case): Migrating from version N to N returns data unchanged.

        Feature: persistence-resilience-enhancement, Property 8: Migration chain sequential application
        Validates: Requirements 4.3
        """
        chain = MigrationChain()
        result = chain.migrate(dict(data), start_version, start_version)
        assert result == data


class TestMigrationChainUnit:
    """Unit tests for MigrationChain edge cases"""

    def test_register_duplicate_raises_value_error(self):
        """Registering the same from_version twice should raise ValueError."""
        chain = MigrationChain()
        chain.register(1, lambda d: d)
        with pytest.raises(ValueError, match="already registered"):
            chain.register(1, lambda d: d)

    def test_migrate_missing_step_raises_value_error(self):
        """Migrating with a gap in the chain should raise ValueError."""
        chain = MigrationChain()
        chain.register(1, lambda d: d)
        # Missing version 2 migration
        chain.register(3, lambda d: d)
        with pytest.raises(ValueError, match="Missing migration from version 2"):
            chain.migrate({}, 1, 4)

    def test_migrate_single_step(self):
        """Single step migration works correctly."""
        chain = MigrationChain()
        chain.register(1, lambda d: {**d, "upgraded": True})
        result = chain.migrate({"key": "value"}, 1, 2)
        assert result == {"key": "value", "upgraded": True}

    def test_migrate_preserves_data_integrity(self):
        """Migration chain preserves all original data fields."""
        chain = MigrationChain()
        chain.register(1, lambda d: {**d, "v2_field": "added"})
        chain.register(2, lambda d: {**d, "v3_field": "added"})

        original = {"name": "test", "value": 42}
        result = chain.migrate(dict(original), 1, 3)

        assert result["name"] == "test"
        assert result["value"] == 42
        assert result["v2_field"] == "added"
        assert result["v3_field"] == "added"

    def test_migrate_backward_returns_unchanged(self):
        """Migrating from higher to lower version returns data unchanged."""
        chain = MigrationChain()
        chain.register(1, lambda d: {**d, "should_not_appear": True})
        data = {"key": "value"}
        result = chain.migrate(dict(data), 3, 1)
        assert result == data
