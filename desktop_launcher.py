"""Packaged entry point with an error dialog even when Tk cannot import."""
from desktop_support import startup_error


if __name__ == "__main__":
    try:
        from desktop import main
        result = main()
    except Exception as exc:
        startup_error(exc)
        result = 1
    raise SystemExit(result)
