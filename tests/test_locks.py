"""T007 acceptance: all direct tools have exact locks; the source-policy checker rejects secrets and
paid services; workflows are SHA-pinned and read-only. (CI being green on both OSes is checked on
GitHub, not here.)"""

import importlib.util
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("audit", ROOT / "scripts" / "audit_dependencies.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

# Exact pins from plan section 5, plus the optional OCR toolchain (D49).
SECTION5 = {
    "core": {"duckdb": "1.5.6", "pandas": "3.1.1", "numpy": "2.5.4", "pyarrow": "26.0.1",
             "httpx": "0.28.1", "pydantic": "2.14.2", "typer": "0.27.3", "pyyaml": "6.0.3"},
    "dev": {"pytest": "9.2.0", "pytest-cov": "7.1.0", "ruff": "0.17.3", "pip-tools": "7.6.2"},
    "geo": {"geopandas": "1.2.0", "shapely": "2.2.0", "pyproj": "3.8.0", "rasterio": "1.5.2",
            "xarray": "2026.9.0", "netcdf4": "1.7.5.1.post1", "h3": "4.5.0", "pmtiles": "3.8.1",
            "osmium": "4.3.2", "libpysal": "4.15.1", "esda": "2.10.0", "pykrige": "1.7.3",
            "networkx": "3.7", "imdlib": "0.4.0"},
    "ml": {"scikit-learn": "1.9.1", "lightgbm": "4.7.0", "statsmodels": "0.15.0", "scipy": "1.18.1",
           "optuna": "5.0.0", "shap": "0.54.1", "mlflow": "3.18.0", "matplotlib": "3.11.2",
           "plotly": "7.1.0"},
    "dl": {"torch": "2.15.0", "transformers": "5.22.1", "sentence-transformers": "6.2.0",
           "safetensors": "0.8.0", "onnx": "1.23.2", "onnxruntime": "1.31.1"},
    "ocr": {"pypdf": "6.21.4", "tesserocr": "2.12.0", "pillow": "13.0.0"},
}  # fmt: skip


@pytest.mark.parametrize("group", audit.GROUPS)
def test_direct_pins_match_section5_and_are_locked(group):
    direct = audit.pins(ROOT / "requirements" / f"{group}.in")
    locked = audit.pins(ROOT / "requirements" / f"{group}.txt")
    assert direct == SECTION5[group]
    for name, version in direct.items():
        assert locked[name] == version


def test_repository_passes_policy():
    assert audit.policy(ROOT) == []


def test_ocr_toolchain_is_included_in_dependency_policy():
    assert "ocr" in audit.GROUPS
    assert "ocr" in audit.NO_TORCH_GROUPS


def test_torch_only_in_dl_lock():
    for group in audit.NO_TORCH_GROUPS:
        assert "torch" not in audit.pins(ROOT / "requirements" / f"{group}.txt")
    assert "torch" in audit.pins(ROOT / "requirements" / "dl.txt")


# --- the checker rejects bad inputs ------------------------------------------------------------


@pytest.fixture
def repo(tmp_path):
    for d in ("requirements", "configs", ".github", "src"):
        shutil.copytree(ROOT / d, tmp_path / d)
    assert audit.policy(tmp_path) == []
    return tmp_path


def _append(path: Path, text: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def test_rejects_unpinned_requirement(repo):
    _append(repo / "requirements" / "core.in", "requests>=2\n")
    assert any("not an exact == pin" in p for p in audit.policy(repo))


def test_rejects_lock_drift(repo):
    lock = repo / "requirements" / "core.txt"
    lock.write_text(lock.read_text(encoding="utf-8").replace("duckdb==1.5.6", "duckdb==2.0.0"))
    assert any("duckdb locked at 2.0.0" in p for p in audit.policy(repo))


def test_rejects_lock_entry_without_hash(repo):
    _append(repo / "requirements" / "dev.txt", "leftpad==1.0.0\n")
    assert any("leftpad==1.0.0 has no hash" in p for p in audit.policy(repo))


def test_rejects_torch_outside_dl(repo):
    _append(
        repo / "requirements" / "ml.txt", "torch==2.15.0 \\\n    --hash=sha256:" + "0" * 64 + "\n"
    )
    assert any("pulls in torch" in p for p in audit.policy(repo))


@pytest.mark.parametrize(
    "line",
    [
        "    api_key: Zx81bQp0Lm2Nv7Rt4Kw9",
        "token: ghp_abcdefghijklmnopqrstuvwxyz0123",
        "bot: 1234567890:AAH9xYzAbCdEfGhIjKlMnOpQrStUvWxYz12",
        "hf: hf_AbCdEfGhIjKlMnOpQrStUvWx",
    ],
)
def test_rejects_secret_values_in_configs(repo, line):
    _append(repo / "configs" / "budgets.yaml", f"# fine\nextra:\n{line}\n")
    assert any("looks like a secret value" in p for p in audit.policy(repo))


def test_env_var_names_are_allowed(repo):
    assert not audit.check_secrets(repo)  # ka.yaml already holds secret_env names


@pytest.mark.parametrize("host", audit.PAID_HOSTS)
def test_rejects_paid_services(repo, host):
    (repo / "src" / "atlas" / "paid.py").write_text(f'URL = "https://{host}/v1"\n')
    assert any(f"paid service {host}" in p for p in audit.policy(repo))


def test_rejects_paid_source_config(repo):
    ka = repo / "configs" / "states" / "ka.yaml"
    ka.write_text(ka.read_text(encoding="utf-8").replace("cost: free\n", "cost: paid\n", 1))
    assert any("ka.yaml" in p for p in audit.policy(repo))


@pytest.mark.parametrize(
    "old,new,message",
    [
        (
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/checkout@v7",
            "not pinned",
        ),
        ("contents: read", "contents: write", "contents: read"),
        ("  pull_request:\n", "  pull_request_target:\n", "pull_request_target"),
        (
            "python -m pytest -q",
            "python -m pytest -q  # ${{ secrets.HF_TOKEN }}",
            "secrets referenced",
        ),
    ],
)
def test_workflow_rules(repo, old, new, message):
    ci = repo / ".github" / "workflows" / "ci.yml"
    text = ci.read_text(encoding="utf-8")
    assert old in text
    ci.write_text(text.replace(old, new), encoding="utf-8")
    assert any(message in p for p in audit.policy(repo))


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("duckdb-1.5.6-cp312-cp312-win_amd64.whl", "yes"),
        ("pyarrow-26.0.1-cp310-abi3-win_amd64.whl", "yes"),
        ("ruff-0.17.3-py3-none-win_amd64.whl", "yes"),
        ("httpx-0.28.1-py3-none-any.whl", "yes"),
        ("torch-2.15.0-cp313-cp313-win_amd64.whl", "NO"),
        ("osmium-4.3.2-cp312-cp312-manylinux_2_28_x86_64.whl", "NO"),
    ],
)
def test_windows_wheel_detection(filename, expected):
    urls = [{"filename": filename, "packagetype": "bdist_wheel"}]
    assert audit._windows_wheel(urls).startswith(expected)
