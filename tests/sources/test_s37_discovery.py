"""T123 acceptance: the S37 (2018 landslide inventory / ISRO Atlas) discovery record passes the
discovery contract only with cited evidence and explicit access, licence and history status."""

import re

from pypdf import PdfReader


def text(path) -> str:
    page = path.read_text(encoding="utf-8", errors="replace")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))


def test_s37_discovery_contract(record):
    assert record("S37").problems() == []


def test_s37_is_blocked_with_explicit_status(record):
    d = record("S37").discovery
    assert d.outcome == "blocked"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "restricted",
        "partial",
        "fail",
    )
    assert d.no_card and not d.account_required
    assert {"T124", "T129", "T136"} <= set(d.dependents)
    assert all(f.upstream is None and f.unit_status == "absent" for f in d.field_map)
    assert "shapefile" in d.retry_condition


def test_no_documents_committed(record):
    assert record("S37").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S37").check_local_hashes()


def test_atlas_page_links_only_the_pdf(record):
    path = record("S37").raw("e05")
    assert "~80,000 landslides" in text(path)
    page = path.read_text(encoding="utf-8", errors="replace")
    pattern = r'href="([^"]*(?:atlas|landslide)[^"]*\.(?:pdf|zip|shp|geojson|csv|kml))"'
    links = re.findall(pattern, page, re.I)
    assert links == ["./assets/pdf/atlas/landslide/Landslides_Atlas_of_India_Updated_25Aug2023.pdf"]


def test_terms_allow_non_commercial_use_with_attribution(record):
    terms = text(record("S37").raw("e06"))
    assert "non-commercial purposes with proper attribution" in terms
    assert "Source: NRSC, ISRO/DOS" in terms
    assert "All Rights Reserved" in text(record("S37").raw("e01"))


def test_bhuvan_page_is_an_app_shell_without_data_links(record):
    page = record("S37").raw("e08").read_text(encoding="utf-8", errors="replace")
    assert "<div>Loading...</div>" in page
    assert not re.search(r"\.(shp|geojson|csv|kml|zip)\b", page, re.I)


def test_atlas_gives_kerala_counts_only(record):
    reader = PdfReader(record("S37").raw("e07"))
    assert len(reader.pages) == 94
    table = reader.pages[33].extract_text()
    assert "Table 2. Landslides inventory database" in table
    kerala = table[table.index("17 Kerala") : table.index("18 Tamil Nadu")]
    numbers = re.findall(r"\d+", kerala)
    assert numbers == "17 9 45 5191 2018 756 2019 09 2020 29 2021 6039".split()
    assert 9 + 45 + 5191 + 756 + 9 + 29 == 6039
    assert not re.search(r"latitude|longitude", table, re.I)
