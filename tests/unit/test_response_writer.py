"""
Unit tests for src/response_writer.py

Tests response file generation including:
- Success response format
- Error response format
- File path creation (agent/mode/date structure)
- JSON serialization
- Directory creation
"""

import json
import pytest
from datetime import datetime
from pathlib import Path

from src.response_writer import ResponseWriter


class TestResponseWriterInitialization:
    """Test ResponseWriter initialization."""

    def test_initialize_with_directory(self, test_responses_dir):
        """Test initializing response writer with directory."""
        writer = ResponseWriter(test_responses_dir)

        assert writer.responses_dir == test_responses_dir


class TestSuccessResponseWriting:
    """Test writing success responses."""

    def test_write_success_response(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test writing a successful order response."""
        writer = ResponseWriter(test_responses_dir)

        response_path = writer.write_success(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            data=mock_alpaca_order_response
        )

        assert response_path.exists()
        assert response_path.suffix == '.json'

    def test_success_response_content(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test success response has correct content."""
        writer = ResponseWriter(test_responses_dir)

        client_order_id = f"testbot_{fixed_timestamp}_stockbuy"
        response_path = writer.write_success(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=client_order_id,
            data=mock_alpaca_order_response
        )

        # Read response
        with open(response_path, 'r') as f:
            response = json.load(f)

        assert response['status'] == 'success'
        assert response['agent_id'] == 'testbot'
        assert response['client_order_id'] == client_order_id
        assert response['data'] == mock_alpaca_order_response
        assert response['error'] is None
        assert 'timestamp' in response

    def test_success_response_path_structure(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test success response is saved in correct directory structure."""
        writer = ResponseWriter(test_responses_dir)

        response_path = writer.write_success(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            data=mock_alpaca_order_response
        )

        # Path should be: responses/testbot/paper/20260214/response_paper_testbot_stockbuy_20260214120000000000.json
        assert response_path.parent.name == "20260214"  # Date folder
        assert response_path.parent.parent.name == "paper"  # Mode folder
        assert response_path.parent.parent.parent.name == "testbot"  # Agent folder

    def test_success_response_filename_format(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test success response filename follows correct format."""
        writer = ResponseWriter(test_responses_dir)

        response_path = writer.write_success(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            data=mock_alpaca_order_response
        )

        # Filename should be: response_paper_testbot_stockbuy_20260214120000000000.json
        expected_filename = f"response_paper_testbot_stockbuy_{fixed_timestamp}.json"
        assert response_path.name == expected_filename

    def test_success_response_with_request_order_id(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test success response includes optional request_order_id."""
        writer = ResponseWriter(test_responses_dir)

        response_path = writer.write_success(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            data=mock_alpaca_order_response,
            request_order_id="abc123"
        )

        with open(response_path, 'r') as f:
            response = json.load(f)

        assert response['request_order_id'] == "abc123"


class TestErrorResponseWriting:
    """Test writing error responses."""

    def test_write_error_response(self, test_responses_dir, fixed_timestamp):
        """Test writing an error response."""
        writer = ResponseWriter(test_responses_dir)

        response_path = writer.write_error(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            error_type="validation_error",
            error_message="Invalid symbol"
        )

        assert response_path.exists()
        assert response_path.suffix == '.json'

    def test_error_response_content(self, test_responses_dir, fixed_timestamp):
        """Test error response has correct content."""
        writer = ResponseWriter(test_responses_dir)

        client_order_id = f"testbot_{fixed_timestamp}_stockbuy"
        response_path = writer.write_error(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=client_order_id,
            error_type="api_error",
            error_message="Insufficient funds"
        )

        with open(response_path, 'r') as f:
            response = json.load(f)

        assert response['status'] == 'error'
        assert response['agent_id'] == 'testbot'
        assert response['client_order_id'] == client_order_id
        assert response['data'] is None
        assert response['error']['type'] == 'api_error'
        assert response['error']['message'] == 'Insufficient funds'
        assert 'timestamp' in response

    def test_error_response_with_details(self, test_responses_dir, fixed_timestamp):
        """Test error response with additional error details."""
        writer = ResponseWriter(test_responses_dir)

        error_details = {
            "required": 1500.00,
            "available": 500.00
        }

        response_path = writer.write_error(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            error_type="api_error",
            error_message="Insufficient funds",
            error_details=error_details
        )

        with open(response_path, 'r') as f:
            response = json.load(f)

        assert response['error']['details'] == error_details

    def test_error_response_path_structure(self, test_responses_dir, fixed_timestamp):
        """Test error response is saved in correct directory structure."""
        writer = ResponseWriter(test_responses_dir)

        response_path = writer.write_error(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            error_type="validation_error",
            error_message="Invalid order"
        )

        # Same structure as success responses
        assert response_path.parent.name == "20260214"
        assert response_path.parent.parent.name == "paper"
        assert response_path.parent.parent.parent.name == "testbot"


class TestDirectoryCreation:
    """Test automatic directory creation."""

    def test_creates_agent_directory(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test response writer creates agent directory if it doesn't exist."""
        writer = ResponseWriter(test_responses_dir)

        response_path = writer.write_success(
            agent_id="newagent",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"newagent_{fixed_timestamp}_stockbuy",
            data=mock_alpaca_order_response
        )

        agent_dir = test_responses_dir / "newagent"
        assert agent_dir.exists()
        assert agent_dir.is_dir()

    def test_creates_mode_directory(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test response writer creates mode directory if it doesn't exist."""
        writer = ResponseWriter(test_responses_dir)

        response_path = writer.write_success(
            agent_id="testbot",
            mode="live",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            data=mock_alpaca_order_response
        )

        mode_dir = test_responses_dir / "testbot" / "live"
        assert mode_dir.exists()
        assert mode_dir.is_dir()

    def test_creates_date_directory(self, test_responses_dir, mock_alpaca_order_response):
        """Test response writer creates date directory from timestamp."""
        writer = ResponseWriter(test_responses_dir)

        # Use different date
        timestamp = "20260315143000000000"

        response_path = writer.write_success(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=timestamp,
            client_order_id=f"testbot_{timestamp}_stockbuy",
            data=mock_alpaca_order_response
        )

        date_dir = test_responses_dir / "testbot" / "paper" / "20260315"
        assert date_dir.exists()
        assert date_dir.is_dir()


class TestMultipleAgentsAndModes:
    """Test handling multiple agents and modes."""

    def test_multiple_agents_separate_directories(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test multiple agents get separate directories."""
        writer = ResponseWriter(test_responses_dir)

        agents = ["sentiment", "momentum", "crypto"]

        for agent in agents:
            writer.write_success(
                agent_id=agent,
                mode="paper",
                order_type="stockbuy",
                timestamp=fixed_timestamp,
                client_order_id=f"{agent}_{fixed_timestamp}_stockbuy",
                data=mock_alpaca_order_response
            )

        # Verify each agent has its own directory
        for agent in agents:
            agent_dir = test_responses_dir / agent
            assert agent_dir.exists()
            assert agent_dir.is_dir()

    def test_same_agent_multiple_modes(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test same agent can have responses in both modes."""
        writer = ResponseWriter(test_responses_dir)

        modes = ["paper", "live"]

        for mode in modes:
            writer.write_success(
                agent_id="testbot",
                mode=mode,
                order_type="stockbuy",
                timestamp=fixed_timestamp,
                client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
                data=mock_alpaca_order_response
            )

        # Verify both mode directories exist
        for mode in modes:
            mode_dir = test_responses_dir / "testbot" / mode
            assert mode_dir.exists()
            assert mode_dir.is_dir()

    def test_multiple_dates_separate_folders(self, test_responses_dir, mock_alpaca_order_response):
        """Test responses from different dates go to separate folders."""
        writer = ResponseWriter(test_responses_dir)

        timestamps = [
            "20260214120000000000",
            "20260215120000000000",
            "20260216120000000000",
        ]

        for timestamp in timestamps:
            writer.write_success(
                agent_id="testbot",
                mode="paper",
                order_type="stockbuy",
                timestamp=timestamp,
                client_order_id=f"testbot_{timestamp}_stockbuy",
                data=mock_alpaca_order_response
            )

        # Verify each date has its own folder
        for timestamp in timestamps:
            date_str = timestamp[:8]
            date_dir = test_responses_dir / "testbot" / "paper" / date_str
            assert date_dir.exists()
            assert date_dir.is_dir()


class TestJSONSerialization:
    """Test JSON serialization."""

    def test_response_is_valid_json(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test written response is valid JSON."""
        writer = ResponseWriter(test_responses_dir)

        response_path = writer.write_success(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            data=mock_alpaca_order_response
        )

        # Should be able to parse JSON
        with open(response_path, 'r') as f:
            response = json.load(f)

        assert isinstance(response, dict)

    def test_response_is_formatted(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test response JSON is formatted with indentation."""
        writer = ResponseWriter(test_responses_dir)

        response_path = writer.write_success(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            data=mock_alpaca_order_response
        )

        with open(response_path, 'r') as f:
            content = f.read()

        # Should have indentation (pretty-printed)
        assert '\n' in content
        assert '  ' in content  # Indentation


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_agent_id(self, test_responses_dir, mock_alpaca_order_response, fixed_timestamp):
        """Test handling of very long agent ID."""
        writer = ResponseWriter(test_responses_dir)

        long_agent = "a" * 100

        response_path = writer.write_success(
            agent_id=long_agent,
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"{long_agent}_{fixed_timestamp}_stockbuy",
            data=mock_alpaca_order_response
        )

        assert response_path.exists()

    def test_special_characters_in_data(self, test_responses_dir, fixed_timestamp):
        """Test handling of special characters in response data."""
        writer = ResponseWriter(test_responses_dir)

        data_with_special_chars = {
            "message": "Order failed: insufficient funds $1,500.00 > $500.00",
            "symbol": "AAPL",
            "unicode": "测试 émojis 🚀"
        }

        response_path = writer.write_success(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            data=data_with_special_chars
        )

        with open(response_path, 'r') as f:
            response = json.load(f)

        assert response['data'] == data_with_special_chars

    def test_nested_data_structures(self, test_responses_dir, fixed_timestamp):
        """Test handling of deeply nested data structures."""
        writer = ResponseWriter(test_responses_dir)

        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep value"
                    }
                },
                "array": [1, 2, 3, {"key": "value"}]
            }
        }

        response_path = writer.write_success(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=f"testbot_{fixed_timestamp}_stockbuy",
            data=nested_data
        )

        with open(response_path, 'r') as f:
            response = json.load(f)

        assert response['data'] == nested_data
