"""
Unit tests for src/ledger.py

Tests the SimpleLedger duplicate detection system including:
- Ledger initialization and loading
- Duplicate detection
- Order recording and persistence
- Restart persistence
- Statistics and helper methods
"""

import pytest
from pathlib import Path

from src.ledger import SimpleLedger


class TestLedgerInitialization:
    """Test ledger initialization and loading."""

    def test_create_new_ledger(self, temp_dir):
        """Test creating a new ledger with no existing file."""
        ledger_file = temp_dir / "test_ledger.txt"
        ledger = SimpleLedger(ledger_file)

        assert ledger.ledger_file == ledger_file
        assert len(ledger.processed) == 0
        assert ledger_file.parent.exists()

    def test_create_ledger_creates_parent_directory(self, temp_dir):
        """Test ledger creates parent directories if they don't exist."""
        ledger_file = temp_dir / "nested" / "dir" / "ledger.txt"
        ledger = SimpleLedger(ledger_file)

        assert ledger_file.parent.exists()
        assert len(ledger.processed) == 0

    def test_load_existing_ledger(self, temp_dir):
        """Test loading existing ledger from file."""
        ledger_file = temp_dir / "test_ledger.txt"

        # Create ledger file with sample data
        with open(ledger_file, 'w') as f:
            f.write("order1_20260214120000000000_stockbuy\n")
            f.write("order2_20260214120100000000_stocksell\n")
            f.write("order3_20260214120200000000_cryptobuy\n")

        # Load ledger
        ledger = SimpleLedger(ledger_file)

        assert len(ledger.processed) == 3
        assert "order1_20260214120000000000_stockbuy" in ledger.processed
        assert "order2_20260214120100000000_stocksell" in ledger.processed
        assert "order3_20260214120200000000_cryptobuy" in ledger.processed

    def test_load_ledger_ignores_empty_lines(self, temp_dir):
        """Test loading ledger ignores empty lines."""
        ledger_file = temp_dir / "test_ledger.txt"

        # Create ledger with empty lines
        with open(ledger_file, 'w') as f:
            f.write("order1_20260214120000000000_stockbuy\n")
            f.write("\n")  # Empty line
            f.write("order2_20260214120100000000_stocksell\n")
            f.write("   \n")  # Whitespace line
            f.write("order3_20260214120200000000_cryptobuy\n")

        ledger = SimpleLedger(ledger_file)

        assert len(ledger.processed) == 3

    def test_load_ledger_strips_whitespace(self, temp_dir):
        """Test loading ledger strips leading/trailing whitespace."""
        ledger_file = temp_dir / "test_ledger.txt"

        with open(ledger_file, 'w') as f:
            f.write("  order1_20260214120000000000_stockbuy  \n")
            f.write("\torder2_20260214120100000000_stocksell\t\n")

        ledger = SimpleLedger(ledger_file)

        assert "order1_20260214120000000000_stockbuy" in ledger.processed
        assert "order2_20260214120100000000_stocksell" in ledger.processed


class TestDuplicateDetection:
    """Test duplicate detection functionality."""

    def test_new_order_not_duplicate(self, temp_dir):
        """Test new order is not detected as duplicate."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        is_dup, reason = ledger.is_duplicate("new_order_id")

        assert is_dup is False
        assert reason is None

    def test_recorded_order_is_duplicate(self, temp_dir):
        """Test recorded order is detected as duplicate."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        # Record an order
        ledger.record("order1_20260214120000000000_stockbuy")

        # Check if it's a duplicate
        is_dup, reason = ledger.is_duplicate("order1_20260214120000000000_stockbuy")

        assert is_dup is True
        assert "already processed" in reason.lower()

    def test_duplicate_detection_case_sensitive(self, temp_dir):
        """Test duplicate detection is case-sensitive."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        ledger.record("order_lowercase")

        # Different case should not be duplicate
        is_dup, reason = ledger.is_duplicate("ORDER_LOWERCASE")
        assert is_dup is False

    def test_duplicate_detection_after_restart(self, temp_dir):
        """Test duplicate detection persists after restart."""
        ledger_file = temp_dir / "ledger.txt"

        # Create ledger and record order
        ledger1 = SimpleLedger(ledger_file)
        ledger1.record("order1_20260214120000000000_stockbuy")

        # Simulate restart by creating new ledger instance
        ledger2 = SimpleLedger(ledger_file)

        # Check if order is still detected as duplicate
        is_dup, reason = ledger2.is_duplicate("order1_20260214120000000000_stockbuy")

        assert is_dup is True
        assert "already processed" in reason.lower()


class TestOrderRecording:
    """Test order recording functionality."""

    def test_record_new_order(self, temp_dir):
        """Test recording a new order."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        ledger.record("order1_20260214120000000000_stockbuy")

        assert "order1_20260214120000000000_stockbuy" in ledger.processed
        assert ledger.contains("order1_20260214120000000000_stockbuy")

    def test_record_order_persists_to_file(self, temp_dir):
        """Test recorded order is written to file."""
        ledger_file = temp_dir / "ledger.txt"
        ledger = SimpleLedger(ledger_file)

        ledger.record("order1_20260214120000000000_stockbuy")

        # Read file directly
        with open(ledger_file, 'r') as f:
            content = f.read()

        assert "order1_20260214120000000000_stockbuy" in content

    def test_record_multiple_orders(self, temp_dir):
        """Test recording multiple orders."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        orders = [
            "order1_20260214120000000000_stockbuy",
            "order2_20260214120100000000_stocksell",
            "order3_20260214120200000000_cryptobuy",
        ]

        for order_id in orders:
            ledger.record(order_id)

        assert len(ledger.processed) == 3
        for order_id in orders:
            assert order_id in ledger.processed

    def test_record_same_order_twice_idempotent(self, temp_dir):
        """Test recording same order twice doesn't duplicate in set."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        ledger.record("order1_20260214120000000000_stockbuy")
        ledger.record("order1_20260214120000000000_stockbuy")

        # Set should only have one entry
        assert len(ledger.processed) == 1

        # But file will have duplicate entries (append-only)
        with open(ledger.ledger_file, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 2  # Both appends written


class TestLedgerPersistence:
    """Test ledger persistence across restarts."""

    def test_persistence_after_restart(self, temp_dir):
        """Test ledger content persists after restart."""
        ledger_file = temp_dir / "ledger.txt"

        # Session 1: Record orders
        ledger1 = SimpleLedger(ledger_file)
        ledger1.record("order1_20260214120000000000_stockbuy")
        ledger1.record("order2_20260214120100000000_stocksell")
        ledger1.record("order3_20260214120200000000_cryptobuy")

        # Session 2: New instance should load existing orders
        ledger2 = SimpleLedger(ledger_file)

        assert len(ledger2.processed) == 3
        assert "order1_20260214120000000000_stockbuy" in ledger2.processed
        assert "order2_20260214120100000000_stocksell" in ledger2.processed
        assert "order3_20260214120200000000_cryptobuy" in ledger2.processed

    def test_append_to_existing_ledger(self, temp_dir):
        """Test appending new orders to existing ledger."""
        ledger_file = temp_dir / "ledger.txt"

        # Session 1
        ledger1 = SimpleLedger(ledger_file)
        ledger1.record("order1_20260214120000000000_stockbuy")

        # Session 2: Add more orders
        ledger2 = SimpleLedger(ledger_file)
        ledger2.record("order2_20260214120100000000_stocksell")

        # Session 3: Verify all orders present
        ledger3 = SimpleLedger(ledger_file)

        assert len(ledger3.processed) == 2
        assert "order1_20260214120000000000_stockbuy" in ledger3.processed
        assert "order2_20260214120100000000_stocksell" in ledger3.processed


class TestStatisticsAndHelpers:
    """Test statistics and helper methods."""

    def test_get_stats_empty_ledger(self, temp_dir):
        """Test stats for empty ledger."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        stats = ledger.get_stats()

        assert stats['total_processed'] == 0
        assert stats['ledger_size'] == 0

    def test_get_stats_with_orders(self, temp_dir):
        """Test stats with recorded orders."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        ledger.record("order1_20260214120000000000_stockbuy")
        ledger.record("order2_20260214120100000000_stocksell")
        ledger.record("order3_20260214120200000000_cryptobuy")

        stats = ledger.get_stats()

        assert stats['total_processed'] == 3
        assert stats['ledger_size'] == 3

    def test_contains_method(self, temp_dir):
        """Test contains() helper method."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        ledger.record("order1_20260214120000000000_stockbuy")

        assert ledger.contains("order1_20260214120000000000_stockbuy") is True
        assert ledger.contains("nonexistent_order") is False

    def test_get_all_orders(self, temp_dir):
        """Test get_all_orders() method."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        orders = [
            "order1_20260214120000000000_stockbuy",
            "order2_20260214120100000000_stocksell",
            "order3_20260214120200000000_cryptobuy",
        ]

        for order_id in orders:
            ledger.record(order_id)

        all_orders = ledger.get_all_orders()

        assert len(all_orders) == 3
        assert set(all_orders) == set(orders)

    def test_clear_ledger(self, temp_dir):
        """Test clearing the ledger."""
        ledger_file = temp_dir / "ledger.txt"
        ledger = SimpleLedger(ledger_file)

        ledger.record("order1_20260214120000000000_stockbuy")
        ledger.record("order2_20260214120100000000_stocksell")

        assert len(ledger.processed) == 2
        assert ledger_file.exists()

        # Clear ledger
        ledger.clear()

        assert len(ledger.processed) == 0
        assert not ledger_file.exists()


class TestPerformance:
    """Test performance characteristics."""

    def test_large_ledger_loading(self, temp_dir):
        """Test loading large ledger is reasonably fast."""
        ledger_file = temp_dir / "large_ledger.txt"

        # Create ledger with 10,000 entries
        with open(ledger_file, 'w') as f:
            for i in range(10000):
                f.write(f"order{i}_20260214120000{i:06d}_stockbuy\n")

        # Load should be fast
        ledger = SimpleLedger(ledger_file)

        assert len(ledger.processed) == 10000

    def test_duplicate_check_is_fast(self, temp_dir):
        """Test duplicate checking is O(1) with large ledger."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        # Add many orders
        for i in range(1000):
            ledger.record(f"order{i}_20260214120000{i:06d}_stockbuy")

        # Check for duplicate should be instant (O(1) set lookup)
        is_dup, reason = ledger.is_duplicate("order500_20260214120000000500_stockbuy")
        assert is_dup is True

        is_dup, reason = ledger.is_duplicate("new_order_99999")
        assert is_dup is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_order_id(self, temp_dir):
        """Test handling of empty order ID."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        ledger.record("")

        # Empty string is valid but shouldn't cause issues
        assert "" in ledger.processed

    def test_very_long_order_id(self, temp_dir):
        """Test handling of very long order ID."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        long_id = "a" * 1000
        ledger.record(long_id)

        assert long_id in ledger.processed
        assert ledger.contains(long_id)

    def test_order_id_with_special_chars(self, temp_dir):
        """Test order IDs with special characters."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        special_ids = [
            "order-with-dashes",
            "order_with_underscores",
            "order.with.dots",
            "order@with#special$chars",
        ]

        for order_id in special_ids:
            ledger.record(order_id)

        assert len(ledger.processed) == len(special_ids)
        for order_id in special_ids:
            assert ledger.contains(order_id)

    def test_unicode_order_id(self, temp_dir):
        """Test handling of unicode characters in order ID."""
        ledger = SimpleLedger(temp_dir / "ledger.txt")

        unicode_id = "order_测试_émojis_🚀"
        ledger.record(unicode_id)

        assert unicode_id in ledger.processed

        # Verify persistence
        ledger2 = SimpleLedger(ledger.ledger_file)
        assert unicode_id in ledger2.processed
