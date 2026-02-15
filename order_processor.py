#!/usr/bin/env python3
"""
Main order processor with file watching and processing pipeline.
Monitors orders/incoming/ and processes orders through validation, API calls, and response writing.
"""

import json
import os
import sys
import time
import signal
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.validators import validate_order_file, ValidationError
from src.alpaca_client import AlpacaClient, AlpacaClientError
from src.ledger import SimpleLedger
from src.response_writer import ResponseWriter


# Configuration
BASE_DIR = Path(__file__).parent
ORDERS_DIR = BASE_DIR / "orders"
INCOMING_DIR = ORDERS_DIR / "incoming"
PROCESSING_DIR = ORDERS_DIR / "processing"
COMPLETED_DIR = ORDERS_DIR / "completed"
FAILED_DIR = ORDERS_DIR / "failed"
RESPONSES_DIR = BASE_DIR / "responses"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

# Ensure directories exist
for dir_path in [INCOMING_DIR, PROCESSING_DIR, COMPLETED_DIR, FAILED_DIR, RESPONSES_DIR, LOGS_DIR, DATA_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    LOGS_DIR / "order_processor_{time:YYYYMMDD}.log",
    rotation="1 day",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}",
    level="DEBUG"
)


class OrderProcessor:
    """Main order processing logic."""

    def __init__(self):
        """Initialize order processor."""
        # Load environment variables
        load_dotenv()

        # Initialize components
        self.ledger = SimpleLedger(DATA_DIR / "processed_orders.txt")
        self.response_writer = ResponseWriter(RESPONSES_DIR)
        self.alpaca_clients = {}  # Cache clients by mode

        # Statistics
        self.stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "duplicates": 0
        }

        logger.info("Order processor initialized")
        logger.info(f"Ledger loaded: {self.ledger.get_stats()['total_processed']} previously processed orders")

    def get_alpaca_client(self, mode: str) -> AlpacaClient:
        """Get or create Alpaca client for mode."""
        if mode not in self.alpaca_clients:
            try:
                self.alpaca_clients[mode] = AlpacaClient(mode=mode)
                logger.info(f"Initialized Alpaca client for {mode} mode")
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca client for {mode}: {e}")
                raise

        return self.alpaca_clients[mode]

    def process_order_file(self, file_path: Path) -> None:
        """
        Process a single order file through the pipeline.

        Pipeline:
        1. Validate filename and JSON
        2. Move to processing/
        3. Check for duplicates
        4. Call Alpaca API
        5. Write response
        6. Move to completed/ or failed/
        """
        filename = file_path.name
        logger.info(f"Processing order file: {filename}")

        # Step 1: Validate
        try:
            filename_parts, validated_order = validate_order_file(file_path)
            logger.debug(f"Validation successful: {filename_parts}")
        except ValidationError as e:
            logger.error(f"Validation failed for {filename}: {e}")
            self._handle_validation_error(file_path, str(e))
            return
        except Exception as e:
            logger.error(f"Unexpected error during validation of {filename}: {e}")
            self._handle_unknown_error(file_path, e)
            return

        # Step 2: Move to processing/
        try:
            processing_path = PROCESSING_DIR / filename
            file_path.rename(processing_path)
            logger.debug(f"Moved to processing: {filename}")
        except Exception as e:
            logger.error(f"Failed to move {filename} to processing: {e}")
            return

        # Extract details
        agent_id = filename_parts['agent_id']
        mode = filename_parts['mode']
        order_type = filename_parts['order_type']
        timestamp = filename_parts['timestamp']
        client_order_id = validated_order.client_order_id

        # Step 3: Check for duplicates in ledger
        is_dup, dup_reason = self.ledger.is_duplicate(client_order_id)

        if is_dup:
            logger.warning(f"Duplicate order detected: {client_order_id}. Reason: {dup_reason}")
            self._handle_duplicate(processing_path, filename_parts, client_order_id, dup_reason)
            return

        # Step 4: Get Alpaca client
        try:
            alpaca_client = self.get_alpaca_client(mode)
        except Exception as e:
            logger.error(f"Failed to get Alpaca client: {e}")
            self._handle_client_init_error(processing_path, filename_parts, client_order_id, str(e))
            return

        # Step 5: Call Alpaca API
        try:
            logger.info(f"Submitting {order_type} order to Alpaca ({mode} mode)")
            response_data = alpaca_client.process_order(
                order_type=order_type,
                payload=validated_order.payload,
                client_order_id=client_order_id
            )
            logger.info(f"Order successful: {client_order_id}")

            # Record in ledger
            self.ledger.record(client_order_id)

            # Step 5: Write success response
            response_path = self.response_writer.write_success(
                agent_id=agent_id,
                mode=mode,
                order_type=order_type,
                timestamp=timestamp,
                client_order_id=client_order_id,
                data=response_data
            )
            logger.info(f"Response written to: {response_path}")

            # Step 6: Move to completed/
            completed_path = COMPLETED_DIR / filename
            processing_path.rename(completed_path)
            logger.debug(f"Moved to completed: {filename}")

            # Update stats
            self.stats['processed'] += 1
            self.stats['successful'] += 1

        except AlpacaClientError as e:
            logger.error(f"Alpaca API error for {client_order_id}: {e}")
            self._handle_api_error(processing_path, filename_parts, client_order_id, str(e))
        except Exception as e:
            logger.error(f"Unexpected error processing {client_order_id}: {e}")
            self._handle_unknown_error(processing_path, e, filename_parts, client_order_id)

    def _handle_validation_error(self, file_path: Path, error_msg: str) -> None:
        """Handle validation errors."""
        filename = file_path.name

        # Try to extract what we can from filename
        try:
            parts = filename[:-5].split('_')
            if len(parts) == 4:
                mode, agent_id, order_type, timestamp = parts
            else:
                mode = "unknown"
                agent_id = "unknown"
                order_type = "unknown"
                timestamp = "00000000000000000000"
        except:
            mode = "unknown"
            agent_id = "unknown"
            order_type = "unknown"
            timestamp = "00000000000000000000"

        # Write error response
        try:
            self.response_writer.write_error(
                agent_id=agent_id,
                mode=mode,
                order_type=order_type,
                timestamp=timestamp,
                client_order_id="unknown",
                error_type="validation_error",
                error_message=error_msg
            )
        except:
            pass  # Best effort

        # Move to failed/
        failed_path = FAILED_DIR / filename
        file_path.rename(failed_path)

        self.stats['processed'] += 1
        self.stats['failed'] += 1

    def _handle_duplicate(self, processing_path: Path, filename_parts: dict, client_order_id: str, reason: str) -> None:
        """Handle duplicate orders."""
        response_path = self.response_writer.write_error(
            agent_id=filename_parts['agent_id'],
            mode=filename_parts['mode'],
            order_type=filename_parts['order_type'],
            timestamp=filename_parts['timestamp'],
            client_order_id=client_order_id,
            error_type="duplicate_error",
            error_message=f"Duplicate order detected: {reason}"
        )
        logger.info(f"Duplicate error response written to: {response_path}")

        # Move to failed/
        failed_path = FAILED_DIR / processing_path.name
        processing_path.rename(failed_path)

        self.stats['processed'] += 1
        self.stats['duplicates'] += 1
        self.stats['failed'] += 1

    def _handle_api_error(self, processing_path: Path, filename_parts: dict, client_order_id: str, error_msg: str) -> None:
        """Handle Alpaca API errors."""
        response_path = self.response_writer.write_error(
            agent_id=filename_parts['agent_id'],
            mode=filename_parts['mode'],
            order_type=filename_parts['order_type'],
            timestamp=filename_parts['timestamp'],
            client_order_id=client_order_id,
            error_type="api_error",
            error_message=error_msg
        )
        logger.info(f"API error response written to: {response_path}")

        # Move to failed/
        failed_path = FAILED_DIR / processing_path.name
        processing_path.rename(failed_path)

        self.stats['processed'] += 1
        self.stats['failed'] += 1

    def _handle_client_init_error(self, processing_path: Path, filename_parts: dict, client_order_id: str, error_msg: str) -> None:
        """Handle Alpaca client initialization errors."""
        response_path = self.response_writer.write_error(
            agent_id=filename_parts['agent_id'],
            mode=filename_parts['mode'],
            order_type=filename_parts['order_type'],
            timestamp=filename_parts['timestamp'],
            client_order_id=client_order_id,
            error_type="client_init_error",
            error_message=f"Failed to initialize Alpaca client: {error_msg}"
        )

        # Move to failed/
        failed_path = FAILED_DIR / processing_path.name
        processing_path.rename(failed_path)

        self.stats['processed'] += 1
        self.stats['failed'] += 1

    def _handle_unknown_error(self, file_path: Path, error: Exception, filename_parts: Optional[dict] = None, client_order_id: Optional[str] = None) -> None:
        """Handle unexpected errors."""
        import traceback

        if filename_parts:
            try:
                self.response_writer.write_error(
                    agent_id=filename_parts['agent_id'],
                    mode=filename_parts['mode'],
                    order_type=filename_parts['order_type'],
                    timestamp=filename_parts['timestamp'],
                    client_order_id=client_order_id or "unknown",
                    error_type="unknown_error",
                    error_message=str(error),
                    error_details={"traceback": traceback.format_exc()}
                )
            except:
                pass  # Best effort

        # Move to failed/
        failed_path = FAILED_DIR / file_path.name
        file_path.rename(failed_path)

        self.stats['processed'] += 1
        self.stats['failed'] += 1

    def print_stats(self) -> None:
        """Print processing statistics."""
        ledger_stats = self.ledger.get_stats()
        logger.info("=" * 60)
        logger.info("Processing Statistics")
        logger.info("=" * 60)
        logger.info(f"Total Processed: {self.stats['processed']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Duplicates: {self.stats['duplicates']}")
        logger.info(f"Ledger Size: {ledger_stats['total_processed']} orders")
        logger.info("=" * 60)


class OrderFileHandler(FileSystemEventHandler):
    """File system event handler for new order files."""

    def __init__(self, processor: OrderProcessor):
        """Initialize handler."""
        self.processor = processor
        super().__init__()

    def on_created(self, event: FileCreatedEvent):
        """Handle new file creation."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Ignore non-JSON files
        if not file_path.suffix == '.json':
            return

        # Ignore temporary files
        if file_path.name.startswith('.') or file_path.name.endswith('.tmp'):
            return

        # Small delay to ensure file is fully written
        time.sleep(0.1)

        # Process the order
        try:
            self.processor.process_order_file(file_path)
        except Exception as e:
            logger.error(f"Unhandled error processing {file_path.name}: {e}")


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Alpaca Exchange Tower - Order Processor")
    logger.info("=" * 60)
    logger.info(f"Watching: {INCOMING_DIR}")
    logger.info(f"Press Ctrl+C to stop")
    logger.info("=" * 60)

    # Initialize processor
    processor = OrderProcessor()

    # Setup file watcher
    event_handler = OrderFileHandler(processor)
    observer = Observer()
    observer.schedule(event_handler, str(INCOMING_DIR), recursive=False)
    observer.start()

    logger.info("Order processor started. Waiting for orders...")

    # Graceful shutdown handler
    def signal_handler(sig, frame):
        logger.info("Shutting down gracefully...")
        observer.stop()
        processor.print_stats()
        logger.info("Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        processor.print_stats()

    observer.join()


if __name__ == "__main__":
    main()
