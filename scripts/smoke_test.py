"""The end-to-end smoke test.

It runs the whole thing for real: a small fixture shop is served over HTTP, the
server is started, the admin API is used to log in, to crawl the fixture shop
and to change a price, and the storefront API is asked whether it serves the
new price.

    python scripts/smoke_test.py

Every step prints what it did. The script exits with a non-zero status when a
step fails, so it can be used in CI as well as by hand.
"""

from __future__ import annotations

import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "shop"

#: The address the committed fixture points at. The script rewrites it to the
#: address it actually serves the fixture on.
CANONICAL_BASE = "http://127.0.0.1:8765"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "smoke-test-password"
NEW_PRICE = "99.99"

STARTUP_TIMEOUT = 60.0
CRAWL_TIMEOUT = 120.0


class SmokeFailure(RuntimeError):
    """A step of the smoke test did not work."""


def step(message: str) -> None:
    print(f"  {message}", flush=True)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """A request handler that does not fill the screen with log lines."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def prepare_fixture(target: Path, base: str) -> Path:
    """Copy the fixture shop and point it at the address it is served on."""
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURE, target, dirs_exist_ok=True)
    for path in sorted(target.rglob("*")):
        if path.is_file() and path.suffix in {".html", ".xml", ".txt", ".svg"}:
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace(CANONICAL_BASE, base), encoding="utf-8")
    return target


def make_handler(directory: Path) -> type[http.server.SimpleHTTPRequestHandler]:
    """A request handler that serves one directory and keeps quiet."""

    class Handler(QuietHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(directory), **kwargs)

    return Handler


def bind_fixture_shop(directory: Path) -> http.server.ThreadingHTTPServer:
    """Take a port for the fixture shop. It does not serve yet."""
    return http.server.ThreadingHTTPServer(("127.0.0.1", 0), make_handler(directory))


def start_fixture_shop(server: http.server.ThreadingHTTPServer) -> str:
    """Serve the fixture shop and return the address it is served on."""
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    return f"http://127.0.0.1:{port}"


def start_application(data_dir: Path, port: int) -> subprocess.Popen[bytes]:
    """Start the server the way a person would run it."""
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONPATH": str(ROOT / "backend"),
            "CATALOG_FORGE_DATA": str(data_dir),
            "CATALOG_FORGE_ADMIN_USERNAME": ADMIN_USERNAME,
            "CATALOG_FORGE_ADMIN_PASSWORD": ADMIN_PASSWORD,
            # The fixture shop lives on this machine, so the crawler is allowed
            # to reach a private address for this test only.
            "CATALOG_FORGE_ALLOW_PRIVATE": "1",
            "CATALOG_FORGE_CRAWLER_DELAY_SECONDS": "0",
            "CATALOG_FORGE_CRAWLER_MAX_PAGES": "50",
            "PYTHONUNBUFFERED": "1",
        }
    )
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "info",
        ],
        cwd=str(ROOT),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def free_port() -> int:
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def wait_for_the_server(base: str, process: subprocess.Popen[bytes]) -> None:
    """Wait until the server answers, or give up with its own words."""
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = ""
            if process.stdout is not None:
                output = process.stdout.read().decode("utf-8", "replace")
            raise SmokeFailure(f"The server stopped before it was ready.\n{output}")
        try:
            response = httpx.get(f"{base}/api/health", timeout=2.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise SmokeFailure("The server did not become ready in time.")


def run_crawl(
    client: httpx.Client, headers: dict[str, str], shop: str
) -> dict[str, object]:
    """Start a crawl of the fixture shop and wait for it to finish."""
    started = client.post("/api/admin/crawls", json={"url": shop}, headers=headers)
    if started.status_code != 202:
        raise SmokeFailure(
            f"The crawl did not start: {started.status_code} {started.text}"
        )
    run_id = int(started.json()["id"])
    step(f"crawl run #{run_id} started")

    deadline = time.monotonic() + CRAWL_TIMEOUT
    run: dict[str, object] = {}
    while time.monotonic() < deadline:
        answer = client.get(f"/api/admin/crawls/{run_id}")
        answer.raise_for_status()
        run = answer.json()
        if run["status"] not in {"pending", "running"}:
            break
        time.sleep(0.4)

    if run.get("status") != "completed":
        raise SmokeFailure(
            f"The crawl did not finish: status {run.get('status')}, "
            f"error {run.get('error')}"
        )

    imported = int(run.get("products_imported") or 0)
    if imported < 2:
        raise SmokeFailure(
            f"The crawl imported {imported} products, but two were expected."
        )
    step(
        f"the crawl imported {imported} products from {run.get('pages_crawled')} pages"
    )
    return run


def probe_write_lock(database: Path) -> str:
    """Say whether the database can be written to right now."""
    import sqlite3

    probe = sqlite3.connect(database, timeout=2.0)
    try:
        probe.execute("BEGIN IMMEDIATE")
        probe.rollback()
        return "free"
    except sqlite3.OperationalError as error:
        return f"held ({error})"
    finally:
        probe.close()


def check_the_price_round_trip(
    client: httpx.Client, headers: dict[str, str], database: Path
) -> None:
    """Change a price through the admin API and read it back from the shop."""
    listing = client.get("/api/products")
    listing.raise_for_status()
    items = listing.json()["items"]
    if not items:
        raise SmokeFailure("The storefront served no products after the crawl.")

    product = items[0]
    product_id = int(product["id"])
    old_price = product["price"]
    step(f"the storefront serves {product['title']} at {old_price}")
    step(f"the database write lock is {probe_write_lock(database)}")

    changed = client.patch(
        f"/api/admin/products/{product_id}/price",
        json={"price": NEW_PRICE},
        headers=headers,
    )
    if changed.status_code != 200:
        raise SmokeFailure(
            f"The price was not changed: {changed.status_code} {changed.text}"
        )
    step(f"the admin API set the price to {NEW_PRICE}")

    after = client.get("/api/products")
    after.raise_for_status()
    updated = next(
        (item for item in after.json()["items"] if item["id"] == product_id), None
    )
    if updated is None:
        raise SmokeFailure("The product disappeared from the storefront.")
    if updated["price"] != NEW_PRICE:
        raise SmokeFailure(
            f"The storefront still serves {updated['price']}, not {NEW_PRICE}."
        )
    step(f"the storefront serves {updated['price']}")

    detail = client.get(f"/api/admin/products/{product_id}")
    detail.raise_for_status()
    if not detail.json()["price_manually_edited"]:
        raise SmokeFailure(
            "The price was not marked as set by hand, so a crawl could undo it."
        )
    step("the price is marked as set by hand")

    images = detail.json()["images"]
    if not images:
        raise SmokeFailure("The images of the product were not imported.")
    step(f"{len(images)} image(s) were imported and stored locally")


def main() -> int:
    print("Catalog Forge smoke test", flush=True)

    if not FIXTURE.exists():
        print(f"The fixture shop is missing: {FIXTURE}", flush=True)
        return 1

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    process: subprocess.Popen[bytes] | None = None
    server: http.server.ThreadingHTTPServer | None = None

    with tempfile.TemporaryDirectory(prefix="catalog-forge-smoke-") as workdir:
        root = Path(workdir)
        try:
            print("1. serving the fixture shop", flush=True)
            shop_dir = root / "shop"
            server = bind_fixture_shop(shop_dir)
            shop_base = f"http://127.0.0.1:{server.server_address[1]}"
            prepare_fixture(shop_dir, shop_base)
            start_fixture_shop(server)
            step(f"the fixture shop is at {shop_base}")

            print("2. starting the server", flush=True)
            process = start_application(root / "data", port)
            wait_for_the_server(base, process)
            step(f"the server is at {base}")

            print("3. logging into the admin API", flush=True)
            with httpx.Client(base_url=base, timeout=30.0) as client:
                login = client.post(
                    "/api/admin/login",
                    json={
                        "username": ADMIN_USERNAME,
                        "password": ADMIN_PASSWORD,
                    },
                )
                if login.status_code != 200:
                    raise SmokeFailure(
                        f"The login failed: {login.status_code} {login.text}"
                    )
                session = login.json()
                headers = {"X-CSRF-Token": session["csrf_token"]}
                step(f"signed in as {session['username']}")

                print("4. crawling the fixture shop", flush=True)
                run_crawl(client, headers, shop_base)

                print("5. changing a price and reading it back", flush=True)
                check_the_price_round_trip(
                    client, headers, root / "data" / "catalog.db"
                )

        except SmokeFailure as failure:
            print(f"\nFAILED: {failure}", flush=True)
            return 1
        except Exception as failure:  # noqa: BLE001 - the script reports anything
            print(f"\nFAILED: {failure!r}", flush=True)
            return 1
        finally:
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
            if server is not None:
                server.shutdown()
                server.server_close()
            if process is not None and process.stdout is not None:
                print("\n--- the server said ---", flush=True)
                print(process.stdout.read().decode("utf-8", "replace"), flush=True)

    print("\nPASSED: the shop crawls, the admin panel edits, the shop serves.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
