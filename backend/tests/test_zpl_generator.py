"""
ZPL Generator unit testleri.
build_zpl saf fonksiyon — DB gerektirmez. build_label_data + generate_loadsheet_zpl
in-memory DB ile sınanır.
"""
import pytest
from datetime import date
from uuid import uuid4
from sqlmodel import Session

from app.services.zpl_generator import (
    build_zpl,
    build_label_data,
    generate_loadsheet_zpl,
    _zpl_escape,
    _wrap_text,
    LABEL_WIDTH_DOTS,
)
from app.models import (
    Cycle, Station, StationAssignment, Territory, Dealer, Product,
    Loadsheet, LoadsheetLine,
)


# ---------- pure helpers ----------

def test_zpl_escape_handles_special_chars():
    assert _zpl_escape("normal") == "normal"
    # ^ ve ~ ZPL komut başlatır — temizlenmeli.
    assert "^" not in _zpl_escape("BAYI ^ A")
    assert "~" not in _zpl_escape("X ~ Y")
    # backslash escaped.
    assert _zpl_escape("a\\b") == "a\\\\b"


def test_zpl_escape_none_returns_empty():
    assert _zpl_escape(None) == ""


def test_wrap_text_short_returns_single():
    assert _wrap_text("KISA", 22) == ["KISA"]


def test_wrap_text_long_splits_on_words():
    lines = _wrap_text("BU UZUN BIR URUN ADIDIR VE BIRDEN FAZLA SATIRA SARMASI GEREKIR", 22)
    assert len(lines) > 1
    for line in lines:
        assert len(line) <= 22 or " " not in line  # tek kelime uzunsa kabul


# ---------- build_zpl (pure) ----------

def _minimal_label_data(**overrides):
    base = {
        "loadsheet_no": 1,
        "package_number": "T07-B01",
        "dealer_code": "BAYI001",
        "dealer_name": "TEST BAYISI",
        "territory_code": "TERR030704-Mevlana",
        "territory_name": "Mevlana",
        "lines": [
            {"product_code": "P1", "product_name": "Marlboro Red", "qty_carton": 2, "qty_pack": 3},
            {"product_code": "P2", "product_name": "Parliament Night Blue", "qty_carton": 1, "qty_pack": 0},
        ],
        "total_carton": 3,
        "total_pack": 3,
    }
    base.update(overrides)
    return base


def test_build_zpl_has_envelope():
    zpl = build_zpl(_minimal_label_data())
    assert zpl.startswith("^XA")
    assert zpl.rstrip().endswith("^XZ")


def test_build_zpl_uses_utf8_and_width():
    zpl = build_zpl(_minimal_label_data())
    assert "^CI28" in zpl
    assert f"^PW{LABEL_WIDTH_DOTS}" in zpl
    assert "^LL" in zpl  # label length set


def test_build_zpl_includes_fis_number():
    zpl = build_zpl(_minimal_label_data(loadsheet_no=7))
    assert "FIŞ-7" in zpl


def test_build_zpl_includes_route_order():
    zpl = build_zpl(_minimal_label_data(route_order=6))
    assert "RUT 6" in zpl


def test_build_zpl_omits_route_when_zero_or_missing():
    # route_order yoksa / 0 ise RUT satırı basılmamalı.
    assert "RUT" not in build_zpl(_minimal_label_data(route_order=0))
    assert "RUT" not in build_zpl(_minimal_label_data())


def test_build_zpl_includes_package_dealer_territory():
    zpl = build_zpl(_minimal_label_data())
    assert "T07-B01" in zpl
    assert "TEST BAYISI" in zpl
    assert "BAYI001" in zpl
    # Territory sadece code olarak basılır (isim kodun içinde zaten var).
    assert "TERR030704-Mevlana" in zpl
    # İsim TEKRAR edilmemeli.
    assert "Mevlana - Mevlana" not in zpl


def test_build_zpl_includes_company_name():
    # Firma adı (AKAY) sağ üstte her fişte basılır.
    assert "AKAY" in build_zpl(_minimal_label_data())


def test_build_zpl_includes_all_lines_and_totals():
    zpl = build_zpl(_minimal_label_data())
    assert "Marlboro Red" in zpl
    assert "Parliament Night Blue" in zpl
    assert "TOPLAM" in zpl
    # Toplam karton 3 — sayı string'i ZPL'de görünmeli.
    assert "FD3^FS" in zpl


def test_build_zpl_no_lines_still_valid():
    zpl = build_zpl(_minimal_label_data(lines=[], total_carton=0, total_pack=0))
    assert "^XA" in zpl
    assert "^XZ" in zpl
    assert "TOPLAM" in zpl


def test_build_zpl_escapes_dealer_name_with_caret():
    zpl = build_zpl(_minimal_label_data(dealer_name="BAD^NAME"))
    # ^ → space dönüştü; ham "BAD^NAME" string'i ZPL'de bulunmamalı.
    # FD ile başlayan field data içinde "BAD^NAME" geçmemeli.
    assert "BAD^NAME" not in zpl
    assert "BAD NAME" in zpl


# ---------- DB-backed (build_label_data + generate_loadsheet_zpl) ----------

@pytest.fixture
def populated_loadsheet(session: Session):
    """Cycle, station, territory, dealer, product, loadsheet — hepsi minimal."""
    cycle = Cycle(
        id=uuid4(),
        cycle_no=1,
        run_time="14:00",
        plan_date=date.today(),
        status="active",
        depot_id=None,
    )
    territory = Territory(
        id=uuid4(),
        code="T07",
        name="MerkezTerritory",
        display_number="07",
        depot_id=None,
    )
    station = Station(id=uuid4(), name="İstasyon-1", active=True, depot_id=None)
    assignment = StationAssignment(
        id=uuid4(),
        cycle_id=cycle.id,
        plan_date=date.today(),
        station_id=station.id,
        territory_id=territory.id,
        load_rank=1,
        target_total_carton=10,
        target_total_pack=20,
        depot_id=None,
    )
    dealer = Dealer(
        id=uuid4(),
        code="BAYI001",
        name="Test Bayisi A.Ş.",
        position_code="P01",
        route_order=1,
        territory_id=territory.id,
        depot_id=None,
    )
    p1 = Product(
        id=uuid4(),
        code="P001",
        name="Marlboro Red",
        pack_per_carton=10,
        display_order=1,
        depot_id=None,
    )
    p2 = Product(
        id=uuid4(),
        code="P002",
        name="Parliament Night Blue",
        pack_per_carton=10,
        display_order=2,
        depot_id=None,
    )
    loadsheet = Loadsheet(
        id=uuid4(),
        cycle_id=cycle.id,
        assignment_id=assignment.id,
        dealer_id=dealer.id,
        sheet_no="LS-001",
        package_number="T07-B01",
        batch_number=1,
        status="pending",
        depot_id=None,
    )
    line1 = LoadsheetLine(
        id=uuid4(),
        loadsheet_id=loadsheet.id,
        product_id=p1.id,
        qty_carton=2,
        qty_pack=3,
    )
    line2 = LoadsheetLine(
        id=uuid4(),
        loadsheet_id=loadsheet.id,
        product_id=p2.id,
        qty_carton=1,
        qty_pack=0,
    )

    for obj in [cycle, territory, station, assignment, dealer, p1, p2, loadsheet, line1, line2]:
        session.add(obj)
    session.commit()
    session.refresh(loadsheet)
    return loadsheet


def test_build_label_data_pulls_dealer_and_territory(session: Session, populated_loadsheet):
    data = build_label_data(session, populated_loadsheet, depot_id=None)
    assert data["dealer_code"] == "BAYI001"
    assert data["dealer_name"] == "Test Bayisi A.Ş."
    assert data["territory_code"] == "T07"
    assert data["package_number"] == "T07-B01"
    assert data["loadsheet_no"] == 1  # tek fiş — ilk sıra
    assert data["route_order"] == 1  # dealer.route_order — fişe RUT olarak basılır


def test_build_label_data_includes_lines_in_order(session: Session, populated_loadsheet):
    data = build_label_data(session, populated_loadsheet, depot_id=None)
    assert len(data["lines"]) == 2
    # display_order'a göre: P001 (1) < P002 (2)
    assert data["lines"][0]["product_code"] == "P001"
    assert data["lines"][1]["product_code"] == "P002"
    assert data["total_carton"] == 3
    assert data["total_pack"] == 3


def test_generate_loadsheet_zpl_end_to_end(session: Session, populated_loadsheet):
    zpl = generate_loadsheet_zpl(session, populated_loadsheet.id, depot_id=None)
    assert zpl.startswith("^XA")
    assert zpl.rstrip().endswith("^XZ")
    assert "Test Bayisi" in zpl
    assert "Marlboro Red" in zpl
    assert "Parliament Night Blue" in zpl
    assert "TOPLAM" in zpl


def test_generate_loadsheet_zpl_unknown_id_raises(session: Session):
    with pytest.raises(KeyError):
        generate_loadsheet_zpl(session, uuid4(), depot_id=None)
