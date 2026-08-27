"""Slice 1 scaffolding baseline: proves the pytest harness and both fake MCP servers."""

from __future__ import annotations

import http.client
import json
import subprocess
import sys

from .fake_sse_server import FakeSseMcpServer, PROTOCOL_VERSION


def _read_until_blank(resp):
    lines = []
    while True:
        line = resp.readline()
        if not line:
            break
        lines.append(line)
        if line == b"\n":
            break
    return b"".join(lines)


def test_harness_imports_and_python_version():
    assert sys.version_info >= (3, 12)
    assert PROTOCOL_VERSION == "2025-11-25"


def test_fake_sse_server_stream_and_json_rpc():
    server = FakeSseMcpServer()
    server.start()
    try:
        host, port = server.host_port
        # 1) GET /sse streams the endpoint event
        conn = http.client.HTTPConnection(host, port, timeout=3)
        conn.request("GET", "/sse", headers={"Accept": "text/event-stream"})
        resp = conn.getresponse()
        assert resp.status == 200
        assert resp.getheader("Content-Type") == "text/event-stream"
        payload = _read_until_blank(resp)
        assert b"event: endpoint" in payload, payload
        conn.close()
        # 2) POST /messages handles initialize JSON-RPC
        conn = http.client.HTTPConnection(host, port, timeout=3)
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                           "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "smoke", "version": "0"}}})
        conn.request("POST", "/messages", body=body.encode(),
                     headers={"Content-Type": "application/json", "MCP-Protocol-Version": PROTOCOL_VERSION})
        resp = conn.getresponse()
        data = json.loads(resp.read())
        assert data["result"]["serverInfo"]["name"] == "fake-sse", data
        conn.close()
    finally:
        server.stop()


def test_fake_stdio_server_handshake():
    import os as _os
    script = _os.path.join(_os.path.dirname(__file__), "fake_stdio_mcp_server.py")
    proc = subprocess.Popen([sys.executable, script], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "smoke", "version": "0"}}}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        data = json.loads(line)
        assert data["result"]["serverInfo"]["name"] == "fake-stdio", data
    finally:
        proc.kill()
        proc.wait()
