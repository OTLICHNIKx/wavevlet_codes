from app.core.config import RESULTS_ROOT
from app.core.security import resolve_results_dir


def test_windows_results_path_is_resolved_inside_current_root() -> None:
    stored = r"E:\project\research_results\web\abc_experiment"
    resolved = resolve_results_dir(stored)
    assert resolved == RESULTS_ROOT / "web" / "abc_experiment"
