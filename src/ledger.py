"""
Simple text file ledger for duplicate detection.
Persists processed orders across restarts with minimal overhead.
"""

from pathlib import Path
from typing import Optional, Tuple


class SimpleLedger:
    """
    Lightweight file-based ledger for duplicate order detection.

    Features:
    - One line per client_order_id in text file
    - In-memory set for O(1) lookups
    - Atomic file append operations
    - Persists across processor restarts
    - Human-readable format
    """

    def __init__(self, ledger_file: Path):
        """
        Initialize ledger.

        Args:
            ledger_file: Path to ledger text file
        """
        self.ledger_file = ledger_file
        self.processed = set()  # In-memory set for fast lookups

        # Ensure directory exists
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing ledger into memory
        self._load()

    def _load(self):
        """Load all processed order IDs from file into memory set."""
        if self.ledger_file.exists():
            with open(self.ledger_file, 'r') as f:
                # Read each line, strip whitespace, add to set
                for line in f:
                    order_id = line.strip()
                    if order_id:  # Skip empty lines
                        self.processed.add(order_id)

    def is_duplicate(self, client_order_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if order has already been processed.

        Args:
            client_order_id: The client order ID to check

        Returns:
            Tuple of (is_duplicate: bool, reason: Optional[str])
        """
        if client_order_id in self.processed:
            return True, "Order already processed (found in ledger)"
        return False, None

    def record(self, client_order_id: str) -> None:
        """
        Record order as processed.

        This is an atomic operation:
        1. Add to in-memory set
        2. Append to file

        Args:
            client_order_id: The client order ID to record
        """
        # Add to in-memory set
        self.processed.add(client_order_id)

        # Append to file (atomic operation)
        with open(self.ledger_file, 'a') as f:
            f.write(f'{client_order_id}\n')

    def get_stats(self) -> dict:
        """
        Get statistics about processed orders.

        Returns:
            Dictionary with stats
        """
        return {
            'total_processed': len(self.processed),
            'ledger_size': len(self.processed)
        }

    def clear(self) -> None:
        """
        Clear all processed orders (for testing only).

        WARNING: This will delete the ledger file!
        """
        self.processed.clear()
        if self.ledger_file.exists():
            self.ledger_file.unlink()

    def contains(self, client_order_id: str) -> bool:
        """
        Check if order ID exists in ledger (simple bool check).

        Args:
            client_order_id: The client order ID to check

        Returns:
            True if exists, False otherwise
        """
        return client_order_id in self.processed

    def get_all_orders(self) -> list:
        """
        Get all processed order IDs.

        Returns:
            List of all client_order_ids
        """
        return list(self.processed)
