"""Serve the app on HTTP and HTTPS, with a separate CA download endpoint."""
import asyncio
import os
import signal
from contextlib import contextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from app.main import app as web_app

TLS_DIR = Path(os.environ.get("INVENTORY_TLS_DIR", Path.home() / ".inventory" / "tls"))
ca_app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class ManagedServer(uvicorn.Server):
    @contextmanager
    def capture_signals(self):
        # The parent coordinates shutdown for all listeners together.
        yield


@ca_app.get("/ca.crt")
def download_ca() -> FileResponse:
    path = TLS_DIR / "ca.crt"
    if not path.is_file():
        raise HTTPException(404, "Certificat local indisponible.")
    return FileResponse(path, media_type="application/x-x509-ca-cert", filename="inventory-local-ca.crt")


async def main() -> None:
    configs = [
        uvicorn.Config(web_app, host="0.0.0.0", port=18765, log_level="info"),
        uvicorn.Config(
        web_app, host="0.0.0.0", port=18766, lifespan="off",
        ssl_keyfile=str(TLS_DIR / "server.key"), ssl_certfile=str(TLS_DIR / "server.crt"),
        log_level="info",
        ),
        uvicorn.Config(ca_app, host="0.0.0.0", port=18767, log_level="warning"),
    ]
    servers = [ManagedServer(config) for config in configs]
    loop = asyncio.get_running_loop()

    def request_shutdown() -> None:
        for server in servers:
            server.should_exit = True

    loop.add_signal_handler(signal.SIGINT, request_shutdown)
    loop.add_signal_handler(signal.SIGTERM, request_shutdown)
    await asyncio.gather(*(server.serve() for server in servers))


if __name__ == "__main__":
    asyncio.run(main())
