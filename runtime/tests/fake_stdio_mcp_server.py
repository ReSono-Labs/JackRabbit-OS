"""Standalone fake MCP stdio server: newline-delimited JSON-RPC on stdin/stdout.

Run: python fake_stdio_mcp_server.py [--fail [--slow] [--stderr <text>]]
Modes:
  default      — initialize/tools/list/tools/call work normally.
  --fail       — respond to initialize with a JSON-RPC error (connection fails).
  --slow       — sleep 5s before answering tools/list (for timeout tests).
  --stderr     — write the given text to stderr during initialize diagnostics test.
"""

from __future__ import annotations

import json
import sys
import time

PROTOCOL_VERSION = "2025-11-25"


def main() -> int:
    args = sys.argv[1:]
    fail = "--fail" in args
    slow = "--slow" in args
    stderr_text = None
    if "--stderr" in args:
        stderr_text = args[args.index("--stderr") + 1]

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        request_id = request.get("id")
        method = request.get("method", "")
        if request_id is None:
            continue  # notification
        if method == "initialize":
            if fail:
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": "fake initialize failure"}}) + "\n")
                sys.stdout.flush()
                return 1
            if stderr_text is not None:
                sys.stderr.write(stderr_text + "\n")
                sys.stderr.flush()
            payload = {
                "jsonrpc": "2.0", "id": request_id, "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fake-stdio", "version": "1.0.0"},
                },
            }
        elif method == "tools/list":
            if slow:
                time.sleep(5)
            payload = {"jsonrpc": "2.0", "id": request_id, "result": {"tools": [
                {"name": "say", "description": "Say something.", "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}},
            ]}}
        elif method == "tools/call":
            args_val = request.get("params", {}).get("arguments", {})
            payload = {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(args_val)}], "isError": False}}
        else:
            payload = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}
        sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
