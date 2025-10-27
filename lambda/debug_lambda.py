#!/usr/bin/env python3
"""Small Lambda handler to debug HTTP connectivity from a VPC."""
import json
import os
import socket
import ssl
import time
import traceback
import urllib.parse
import urllib.request
from typing import Any, Dict, Tuple

_DEFAULT_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "5"))
_DEFAULT_METHOD = os.getenv("DEFAULT_METHOD", "GET").upper()
_DEFAULT_URL = os.getenv("DEFAULT_URL", "http://example.com")


def _build_request(event: Dict[str, Any]) -> Tuple[str, str, Dict[str, str], bytes]:
    url = event.get("url") or _DEFAULT_URL
    method = (event.get("method") or _DEFAULT_METHOD).upper()
    headers = event.get("headers") or {}
    body = event.get("body")

    if isinstance(body, str):
        body_bytes = body.encode("utf-8")
    elif isinstance(body, (bytes, bytearray)):
        body_bytes = bytes(body)
    elif body is None:
        body_bytes = b""
    else:
        body_bytes = json.dumps(body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    return url, method, headers, body_bytes


def _resolve_host(parsed_url: urllib.parse.ParseResult) -> Dict[str, Any]:
    host = parsed_url.hostname
    port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)

    try:
        resolution = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        addrs = [
            {
                "family": res[0].name,
                "socktype": res[1].name,
                "protocol": res[2],
                "address": res[4][0],
            }
            for res in resolution
        ]
    except Exception as exc:
        return {
            "host": host,
            "port": port,
            "error": f"DNS resolution failed: {exc}",
        }

    return {
        "host": host,
        "port": port,
        "addresses": addrs,
    }


def _perform_socket_check(host: str, port: int) -> Dict[str, Any]:
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=_DEFAULT_TIMEOUT) as conn:
            latency = time.time() - start
            peer = conn.getpeername()
            return {
                "success": True,
                "latency_ms": int(latency * 1000),
                "peername": peer,
            }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


def _fetch(url: str, method: str, headers: Dict[str, str], body: bytes) -> Dict[str, Any]:
    request = urllib.request.Request(url=url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, data=body or None, timeout=_DEFAULT_TIMEOUT) as response:
            content = response.read()
            return {
                "status": response.status,
                "reason": response.reason,
                "headers": dict(response.getheaders()),
                "body_sample": content[:1024].decode("utf-8", errors="replace"),
                "body_length": len(content),
            }
    except urllib.error.HTTPError as exc:
        return {
            "status": exc.code,
            "reason": exc.reason,
            "headers": dict(exc.headers.items()),
            "body_sample": exc.read()[:1024].decode("utf-8", errors="replace"),
            "error": str(exc),
        }
    except ssl.SSLError as exc:
        return {
            "error": f"TLS error: {exc}",
        }
    except Exception as exc:
        return {
            "error": f"Request failed: {exc}",
            "trace": traceback.format_exc(limit=2),
        }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    url, method, headers, body = _build_request(event or {})
    parsed_url = urllib.parse.urlparse(url)
    dns_info = _resolve_host(parsed_url)

    socket_check = None
    if parsed_url.hostname:
        socket_check = _perform_socket_check(parsed_url.hostname, parsed_url.port or (443 if parsed_url.scheme == "https" else 80))

    http_result = _fetch(url, method, headers, body)

    return {
        "input": {
            "url": url,
            "method": method,
            "headers": headers,
            "body_length": len(body),
        },
        "dns": dns_info,
        "socket": socket_check,
        "http": http_result,
        "environment": {
            "subnet_ids": os.getenv("AWS_SUBNET_IDS"),
            "security_group_ids": os.getenv("AWS_SECURITY_GROUP_IDS"),
            "execution_env": os.getenv("AWS_EXECUTION_ENV"),
            "region": os.getenv("AWS_REGION"),
        },
    }
