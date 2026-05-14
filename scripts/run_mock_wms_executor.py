#!/usr/bin/env python3

from __future__ import annotations

import sys
import ipaddress
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener, urlopen

# Import the authoritative package module and re-export its public API
from amr_warehouse_sim import mock_wms_executor as _pkg


# Copy public symbols from the package into this shim, except the HTTP helpers
# which we implement locally so tests can monkeypatch `build_opener`/`urlopen`.
for _name in dir(_pkg):
    if _name.startswith('_'):
        continue
    if _name in (
        'fetch_http_json',
        'patch_http_json',
        '_open_http_url',
        '_url_targets_loopback_host',
        '_request_url',
    ):
        continue
    globals()[_name] = getattr(_pkg, _name)


def _request_url(request_or_url: str | Request) -> str:
    if isinstance(request_or_url, Request):
        return str(request_or_url.full_url)
    return request_or_url


def _url_targets_loopback_host(url_or_request: str | Request) -> bool:
    hostname = urlparse(_request_url(url_or_request)).hostname
    if hostname is None:
        return False
    if hostname == 'localhost':
        return True

    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _open_http_url(url_or_request: str | Request, *, timeout_sec: float = 5.0):
    timeout = max(timeout_sec, 0.1)
    if _url_targets_loopback_host(url_or_request):
        # Local API calls should not be routed through ambient shell proxies.
        return build_opener(ProxyHandler({})).open(url_or_request, timeout=timeout)
    return urlopen(url_or_request, timeout=timeout)


def fetch_http_json(url: str, *, timeout_sec: float = 5.0) -> object:
    try:
        with _open_http_url(url, timeout_sec=timeout_sec) as response:
            body = response.read().decode('utf-8')
    except HTTPError as exc:
        raise _pkg.HttpTaskSourceUnavailableError(
            f'HTTP {exc.code} while requesting {url}.'
        ) from exc
    except URLError as exc:
        raise _pkg.HttpTaskSourceUnavailableError(
            f'Could not reach {url}: {exc.reason}.'
        ) from exc
    except OSError as exc:
        raise _pkg.HttpTaskSourceUnavailableError(
            f'Could not reach {url}: {exc}.'
        ) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise _pkg.InvalidHttpTaskPayloadError(
            f'HTTP response from {url} was not valid JSON.'
        ) from exc


def patch_http_json(url: str, payload: dict[str, object], *, timeout_sec: float = 5.0) -> object:
    request = Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PATCH',
    )
    try:
        with _open_http_url(request, timeout_sec=timeout_sec) as response:
            body = response.read().decode('utf-8')
    except HTTPError as exc:
        raise _pkg.HttpTaskSourceUnavailableError(
            f'HTTP {exc.code} while requesting {url}.'
        ) from exc
    except URLError as exc:
        raise _pkg.HttpTaskSourceUnavailableError(
            f'Could not reach {url}: {exc.reason}.'
        ) from exc
    except OSError as exc:
        raise _pkg.HttpTaskSourceUnavailableError(
            f'Could not reach {url}: {exc}.'
        ) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise _pkg.InvalidHttpTaskPayloadError(
            f'HTTP response from {url} was not valid JSON.'
        ) from exc


# Keep a reference to the package main for CLI invocation.
_main = _pkg.main


if __name__ == '__main__':
    raise SystemExit(_main(sys.argv[1:]))
