"""Production entry point: uvicorn with the app factory, structured logging and proxy headers.

TLS terminates at the reverse proxy."""

import uvicorn

from app.config import get_settings


def main() -> None:
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="0.0.0.0",  # noqa: S104  (inside the container; only the reverse proxy is published)
        port=8000,
        workers=get_settings().workers,
        log_config=None,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
