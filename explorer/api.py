"""Small HTTP API for the frontend: runs the scorer ranking and the explorer for the farmer's inputs.

    uv run python -m explorer.api            # http://127.0.0.1:8000/api/explorer
    uv run python -m explorer.api --port 8001

GET /api/explorer?w=water:5,risk:3,soil_health:3,nitrogen:2&crops=corn,soybean,sorghum&n=3

* ``w``     weights per scorer criterion (``ScoreParts``), any non-negative numbers; only their ratio matters.
            Missing criteria count 0. Without ``w`` all criteria weigh the same.
* ``crops`` main crops the picks may use. Without it every crop is allowed. The current rotation is
            always included.
* ``n``     number of picks besides the current rotation, 1-3 (default 3).
* ``rotation`` a rotation the farmer built, e.g. ``corn-soybean-sorghum``, ``corn-soybean-sorghum+triticale``
            (cover crop in every gap) or ``corn-soybean-sorghum+triticale_2`` (only after the 2nd crop; scored on
            request, ~1.5 s). It replaces the crop-history rotation as the current one; the picks stay the same.
* ``lat``, ``lon`` are accepted but not used yet: there is one field (``field.id``) until other fields are processed.

Answer: ``explorer.json`` (``ExplorerExport`` in schema.py).
Errors: 400 with ``{"error": "..."}``.
Standard library only, so no extra dependency. ``main`` runs a local server; on Vercel the WSGI ``app`` below
answers the same requests (``vercel.json``, service "backend").
"""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import get_args
from urllib.parse import parse_qs, urlparse

from explorer.build import N_PICKS, build_explorer
from explorer.schema import MainCropId, ScoreParts

CRITERIA = list(ScoreParts.model_fields)
MAIN_CROPS = set(get_args(MainCropId))


class BadRequest(ValueError):
    pass


def parse_request(query: str) -> dict:
    """Query string -> keyword arguments for ``build_explorer``. Raises BadRequest with a readable message."""
    q = {k: v[-1] for k, v in parse_qs(query).items()}

    weights = {c: 1.0 for c in CRITERIA}
    if q.get("w"):
        weights = {c: 0.0 for c in CRITERIA}
        for pair in q["w"].split(","):
            name, _, value = pair.partition(":")
            if name not in weights:
                continue  # unknown priority from an older frontend: ignore
            try:
                weights[name] = float(value)
            except ValueError:
                raise BadRequest(f"weight for '{name}' is not a number: {value!r}") from None
            if weights[name] < 0:
                raise BadRequest(f"weight for '{name}' must not be negative")
        if not any(weights.values()):
            raise BadRequest(f"at least one weight must be above 0 ({', '.join(CRITERIA)})")

    crops = None
    if q.get("crops"):
        crops = [c for c in q["crops"].split(",") if c]
        unknown = sorted(set(crops) - MAIN_CROPS)
        if unknown:
            raise BadRequest(f"unknown crops {unknown}, known: {sorted(MAIN_CROPS)}")

    n_picks = N_PICKS
    if q.get("n"):
        try:
            n_picks = int(q["n"])
        except ValueError:
            raise BadRequest(f"n is not a whole number: {q['n']!r}") from None
        if not 1 <= n_picks <= N_PICKS:
            raise BadRequest(f"n must be between 1 and {N_PICKS}")

    current = None
    if q.get("rotation"):
        current = q["rotation"].replace(" ", "+")  # an unencoded "+" arrives as a space
        crops_of, _, cover = current.partition("+")
        name, _, gaps = cover.partition("_")
        unknown = sorted(set(crops_of.split("-")) - MAIN_CROPS)
        if unknown or name not in ("", "triticale") or (gaps and not gaps.isdigit()):
            raise BadRequest(f"rotation {current!r}: use main crops {sorted(MAIN_CROPS)} joined by '-', optionally "
                             "'+triticale' (cover in every gap) or '+triticale_1' (cover only after the first crop)")

    return {"weights": weights, "crops": crops, "n_picks": n_picks, "current": current}


def answer(path: str, query: str) -> tuple[int, dict]:
    """Status code and JSON body for a GET request, shared by the local server and the Vercel app."""
    if path == "/api/health":
        return 200, {"ok": True}
    if path != "/api/explorer":
        return 404, {"error": f"unknown path {path}"}
    try:
        export, _ = build_explorer(**parse_request(query))
    except (BadRequest, ValueError) as e:
        return 400, {"error": str(e)}
    return 200, export.model_dump(mode="json")


def app(environ: dict, start_response) -> list[bytes]:
    """WSGI entry point for Vercel."""
    status, body = answer(environ.get("PATH_INFO", ""), environ.get("QUERY_STRING", ""))
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    start_response(f"{status} {HTTPStatus(status).phrase}",
                   [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(data)))])
    return [data]


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")  # the Vite dev server runs on another port
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 (name given by BaseHTTPRequestHandler)
        url = urlparse(self.path)
        self._send(*answer(url.path, url.query))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"explorer API on http://{args.host}:{args.port}/api/explorer")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
