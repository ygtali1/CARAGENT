from pathlib import Path
import uuid


def pytest_configure(config):
    # Use a new workspace directory; some Windows user temp folders are inaccessible.
    if not config.option.basetemp:
        parent = Path(__file__).resolve().parent.parent / "data" / "test-tmp"
        parent.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(parent / ("run-" + uuid.uuid4().hex))
