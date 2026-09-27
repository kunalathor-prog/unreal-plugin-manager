"""Executable entry point with dependency-independent startup error reporting."""
from app.diagnostics import configure_logging, startup_error


def launch() -> int:
    log_path = None
    try:
        log_path = configure_logging()
        from app.main import main
        return main()
    except Exception as exc:
        startup_error(exc, log_path)
        return 1


if __name__ == "__main__":
    raise SystemExit(launch())
