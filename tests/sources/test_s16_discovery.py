"""T017 acceptance: the S16 (WorldPop India population) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status."""

import json
import struct


def bigtiff_tags(path) -> dict[int, tuple]:
    """Numeric tags of the first IFD of a little-endian BigTIFF (header only, no pixels)."""
    sizes, fmt = {3: 2, 4: 4, 12: 8, 16: 8}, {3: "H", 4: "I", 12: "d", 16: "Q"}
    with open(path, "rb") as fh:
        b = fh.read(1 << 22)
    assert b[:4] == b"II+\x00"
    off = struct.unpack_from("<Q", b, 8)[0]
    out = {}
    for i in range(struct.unpack_from("<Q", b, off)[0]):
        e = off + 8 + 20 * i
        tag, typ, cnt = struct.unpack_from("<HHQ", b, e)
        if typ in fmt:
            size = sizes[typ] * cnt
            data = (
                b[e + 12 : e + 20]
                if size <= 8
                else b[struct.unpack_from("<Q", b, e + 12)[0] :][:size]
            )
            out[tag] = struct.unpack_from("<" + fmt[typ] * cnt, data)
    return out


def test_s16_discovery_contract(record):
    assert record("S16").problems() == []


def test_s16_status(record):
    d = record("S16").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert d.no_card and not d.account_required


def test_no_data_committed(record):
    assert record("S16").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S16").check_local_hashes()


def test_entries_are_counts_per_pixel_under_cc_by(record):
    rec = record("S16")
    entries = json.loads(rec.raw("e03").read_text("utf-8"))["data"]
    assert sorted(int(e["popyear"]) for e in entries) == list(range(2015, 2031))
    assert all("number of people per pixel" in e["desc"] for e in entries)
    assert all(e["license"] == "https://hub.worldpop.org/data/licence.txt" for e in entries)
    assert "Creative Commons Attribution\n4.0 International License" in rec.raw("e04").read_text(
        "utf-8"
    )


def test_geotiff_grid(record):
    t = bigtiff_tags(record("S16").raw("e05"))
    assert (t[256][0], t[257][0], t[258][0], t[339][0]) == (3504, 3451, 32, 3)  # float32
    assert t[259][0] == 5 and t[322][0] == 512  # LZW tiles: sums need a raster reader (T018)
    assert round(t[33550][0], 7) == 0.0083333
