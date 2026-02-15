"""
Response file writer.
Creates response JSON files organized by agent/mode/date.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class ResponseWriter:
    """
    Writes response files to: responses/{agentid}/{mode}/{YYYYMMDD}/
    """

    def __init__(self, responses_dir: Path):
        """
        Initialize response writer.

        Args:
            responses_dir: Base responses directory
        """
        self.responses_dir = responses_dir

    def write_success(
        self,
        agent_id: str,
        mode: str,
        order_type: str,
        timestamp: str,
        client_order_id: str,
        data: Dict[str, Any],
        request_order_id: Optional[str] = None
    ) -> Path:
        """
        Write a success response.

        Args:
            agent_id: Agent identifier
            mode: paper or live
            order_type: Order type
            timestamp: Original order timestamp
            client_order_id: Client order ID
            data: Response data from Alpaca
            request_order_id: Optional request order ID

        Returns:
            Path to created response file
        """
        response = {
            "request_order_id": request_order_id,
            "agent_id": agent_id,
            "client_order_id": client_order_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success",
            "data": data,
            "error": None
        }

        return self._write_response(agent_id, mode, order_type, timestamp, response)

    def write_error(
        self,
        agent_id: str,
        mode: str,
        order_type: str,
        timestamp: str,
        client_order_id: str,
        error_type: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        request_order_id: Optional[str] = None
    ) -> Path:
        """
        Write an error response.

        Args:
            agent_id: Agent identifier
            mode: paper or live
            order_type: Order type
            timestamp: Original order timestamp
            client_order_id: Client order ID
            error_type: Type of error (validation_error, api_error, duplicate_error, etc.)
            error_message: Error message
            error_details: Optional additional error details
            request_order_id: Optional request order ID

        Returns:
            Path to created response file
        """
        response = {
            "request_order_id": request_order_id,
            "agent_id": agent_id,
            "client_order_id": client_order_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "data": None,
            "error": {
                "type": error_type,
                "message": error_message,
                "details": error_details or {}
            }
        }

        return self._write_response(agent_id, mode, order_type, timestamp, response)

    def _write_response(
        self,
        agent_id: str,
        mode: str,
        order_type: str,
        timestamp: str,
        response: Dict[str, Any]
    ) -> Path:
        """
        Write response to appropriate location.

        Args:
            agent_id: Agent identifier
            mode: paper or live
            order_type: Order type
            timestamp: Original order timestamp (YYYYMMDDHHMMSSffffff)
            response: Response data

        Returns:
            Path to created file
        """
        # Extract date from timestamp (YYYYMMDD)
        date_str = timestamp[:8]

        # Create directory structure: responses/{agentid}/{mode}/{YYYYMMDD}/
        output_dir = self.responses_dir / agent_id / mode / date_str
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create filename: response_{mode}_{agentid}_{ordertype}_{timestamp}.json
        filename = f"response_{mode}_{agent_id}_{order_type}_{timestamp}.json"
        output_path = output_dir / filename

        # Write JSON
        with open(output_path, 'w') as f:
            json.dump(response, f, indent=2)

        return output_path
