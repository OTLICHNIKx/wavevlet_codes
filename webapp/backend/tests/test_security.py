import uuid
from pathlib import Path

from app.core.config import RESULTS_ROOT
from app.core.security import make_results_dir, make_slug


def test_safe_results_path() -> None:
    path = Path(make_results_dir(uuid.uuid4(), "../../unsafe name"))
    assert path.is_relative_to(RESULTS_ROOT)
    assert ".." not in path.name
    assert make_slug("Привет / test") == "test"
