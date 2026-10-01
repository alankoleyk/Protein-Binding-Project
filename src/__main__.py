import sys
from importlib import import_module


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except (ImportError, OSError) as exc:
        print(
            f"Unable to load Qt. Please activate the ProteinBinding environment: {exc}",
            file=sys.stderr,
        )
        return 1

    error = None
    try:
        for module in (
            "PySide6.QtWebEngineWidgets",
            "PySide6.QtWebChannel",
            "Bio",
            "numpy",
            "pandas",
            "scipy",
            "sklearn",
        ):
            import_module(module)
    except (ImportError, OSError) as exc:
        error = f"{module}: {type(exc).__name__}: {exc}"

    app = QApplication(sys.argv)
    app.setApplicationName("ProteinBinding")

    if error is not None:
        QMessageBox.critical(None, "ProteinBinding", f"Environment check failed:\n{error}")
        return 1

    QMessageBox.information(
        None,
        "ProteinBinding",
        "Environment OK!\nAll Qt and scientific Python dependencies imported successfully."
        f"\n\nPython: {sys.executable}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
