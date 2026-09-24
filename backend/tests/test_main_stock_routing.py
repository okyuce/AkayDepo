"""
AnaStok yönlendirme testleri (loadsheet_generator).

Kural: bayinin döngüdeki toplam siparişi (karton + paket/10) 200 ve üstündeyse
fişi AnaStok'a gider. Revizyonla geçersizleşen önceki sipariş toplama katılmaz
(planlayıcının bölge yükünde de); revizyonda iptal edilen tamamlanmış fişin
stoğu o fişin kendi istasyonuna iade edilir.
"""
from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.models import (
    Cycle, Dealer, Loadsheet, LoadsheetLine, Order, OrderLine, Product,
    Station, StationAssignment, StationInventory, StockMovement, Territory,
)
from app.services.loadsheet_generator import LoadsheetGenerator
from app.services.station_planner import StationPlanner


@pytest.fixture
def world(session: Session):
    """Tek bayi, tek ürün. Territory İstasyon-1'e atanmış; İstasyon-1'de 1000 karton stok var."""
    cycle = Cycle(id=uuid4(), cycle_no=1, run_time="14:00", plan_date=date(2026, 9, 24), status="active")
    territory = Territory(id=uuid4(), code="TERR030701-Test", name="Test", display_number="T01")
    station = Station(id=uuid4(), name="İstasyon-1", active=True)
    main_stock = Station(id=uuid4(), name="AnaStok", active=True, is_main_stock=True)
    dealer = Dealer(
        id=uuid4(), code="BAYI001", name="Test Bayi", position_code="P01",
        route_order=1, territory_id=territory.id,
    )
    product = Product(id=uuid4(), code="MLR100", name="Test Ürün", pack_per_carton=10, display_order=1)
    assignment = StationAssignment(
        id=uuid4(), cycle_id=cycle.id, plan_date=cycle.plan_date, station_id=station.id,
        territory_id=territory.id, load_rank=1, target_total_carton=0, target_total_pack=0,
    )
    inventory = StationInventory(station_id=station.id, product_id=product.id, quantity_carton=1000, quantity_pack=0)
    # FK sırasıyla: ilişki tanımı olmadığı için flush sırası garanti değil (Postgres FK'yi denetler)
    for o in [cycle, territory, station, main_stock, product]:
        session.add(o)
    session.flush()
    for o in [dealer, assignment, inventory]:
        session.add(o)
    session.commit()
    return SimpleNamespace(
        session=session, cycle=cycle, territory=territory, station=station,
        main_stock=main_stock, dealer=dealer, product=product,
    )


def add_order(w, batch: int, carton: int, pack: int = 0, previous: Order = None,
              delivery: date = date(2026, 9, 25), extra_lines=()) -> Order:
    """Excel import'unun yazdığı sipariş. `previous` verilirse revizyondur (tam yeni içerik).
    `extra_lines`: her biri ayrı üründe ek (karton, paket) satırları."""
    order = Order(
        cycle_id=w.cycle.id, external_order_code=f"SIP-{batch}", payment_type="Nakit",
        order_date=datetime(2026, 9, 24, 10, 0), delivery_date=delivery,
        territory_id=w.territory.id, dealer_id=w.dealer.id, revision_group_id=uuid4(),
        revision_no=1, source_sheet="Recipe2", import_batch=batch,
        is_revision=previous is not None,
        previous_order_id=previous.id if previous else None,
    )
    w.session.add(order)
    w.session.flush()
    w.session.add(OrderLine(order_id=order.id, product_id=w.product.id, qty_carton=carton, qty_pack=pack))
    for extra_carton, extra_pack in extra_lines:
        product = Product(id=uuid4(), code=f"EK-{uuid4().hex[:8]}", name="Ek Ürün")
        w.session.add(product)
        w.session.flush()
        w.session.add(OrderLine(order_id=order.id, product_id=product.id, qty_carton=extra_carton, qty_pack=extra_pack))
    w.session.commit()
    return order


def plan_batch(w, batch: int) -> Loadsheet:
    """Planlama Oluştur gibi: sadece son batch'in fişini üretir (planning.py)."""
    LoadsheetGenerator(w.session).generate_loadsheets_for_cycle(w.cycle.id, only_batch=batch)
    return w.session.exec(
        select(Loadsheet).where(Loadsheet.cycle_id == w.cycle.id, Loadsheet.batch_number == batch)
    ).one()


def station_of(w, loadsheet: Loadsheet):
    return w.session.get(StationAssignment, loadsheet.assignment_id).station_id


def complete(w, loadsheet: Loadsheet):
    """complete_loadsheet gibi: fiş yüklenir, her satır fişin kendi istasyonunun stoğundan
    paket eşdeğeriyle (1 karton = 10 paket) düşer."""
    station_id = station_of(w, loadsheet)
    for line in w.session.exec(select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == loadsheet.id)).all():
        inventory = w.session.exec(
            select(StationInventory).where(
                StationInventory.station_id == station_id,
                StationInventory.product_id == line.product_id,
            )
        ).one()
        total_packs = inventory.quantity_carton * 10 + inventory.quantity_pack - (line.qty_carton * 10 + line.qty_pack)
        inventory.quantity_carton, inventory.quantity_pack = total_packs // 10, total_packs % 10
        w.session.add(inventory)
    loadsheet.status = "loaded"
    loadsheet.loaded_at = loadsheet.completed_at = datetime.now()
    w.session.add(loadsheet)
    w.session.commit()


# ---------- eşik ----------

@pytest.mark.parametrize("carton, pack, to_main_stock", [
    (200, 0, True),    # 200 ve üstü → AnaStok
    (199, 10, True),   # 10 paket = 1 karton → 200,0
    (199, 9, False),   # 199,9 → eşiğin altı
    (300, 0, True),
])
def test_threshold_boundary(world, carton, pack, to_main_stock):
    add_order(world, 1, carton, pack)
    ls = plan_batch(world, 1)
    assert station_of(world, ls) == (world.main_stock.id if to_main_stock else world.station.id)


def test_threshold_exact_200_with_pack_lines(world):
    """199 krt + 10 ayrı satırda 1'er paket = tam 200 → AnaStok. Satır satır `paket / 10.0`
    toplandığında Postgres 199,99999999999994 veriyordu. (SQLite telafili topladığı için
    eski kod burada da geçer; asıl güvence tamsayı paket toplamı.)"""
    add_order(world, 1, 199, extra_lines=[(0, 1)] * 10)
    assert station_of(world, plan_batch(world, 1)) == world.main_stock.id


def test_inactive_main_stock_keeps_dealer_on_station(world):
    """AnaStok kapalıysa eşik üstü bayi de territory'nin istasyonunda kalır."""
    world.main_stock.active = False
    world.session.add(world.main_stock)
    world.session.commit()
    add_order(world, 1, 250)
    assert station_of(world, plan_batch(world, 1)) == world.station.id


# ---------- revizyon: toplam ----------

def test_revision_does_not_double_count_previous_order(world):
    """110 → 100 revizyonu: bayinin gerçek toplamı 100. Önceki sipariş de sayılırsa 210 olup AnaStok'a düşüyordu."""
    first = add_order(world, 1, 110)
    ls1 = plan_batch(world, 1)
    add_order(world, 2, 100, previous=first)
    ls2 = plan_batch(world, 2)

    assert station_of(world, ls1) == world.station.id
    assert station_of(world, ls2) == world.station.id
    assert ls2.is_revision and ls2.parent_loadsheet_id == ls1.id


def test_revision_chain_counts_only_latest_version(world):
    """80 → 75 → 70: her sürüm sayılırsa 225 olup AnaStok'a düşüyordu."""
    v1 = add_order(world, 1, 80)
    plan_batch(world, 1)
    v2 = add_order(world, 2, 75, previous=v1)
    plan_batch(world, 2)
    add_order(world, 3, 70, previous=v2)
    assert station_of(world, plan_batch(world, 3)) == world.station.id


def test_non_revision_orders_are_summed(world):
    """Revizyon olmayan ikinci sipariş (farklı teslimat tarihi) bayi toplamına eklenir: 120 + 90 = 210."""
    add_order(world, 1, 120)
    plan_batch(world, 1)
    add_order(world, 2, 90, delivery=date(2026, 9, 26))
    assert station_of(world, plan_batch(world, 2)) == world.main_stock.id


# ---------- revizyon: stok iadesi ----------

def test_revision_refund_goes_to_previous_loadsheet_station(world):
    """180 (yüklendi, İstasyon-1) → 220 revizyonu: yeni fiş eşiği aştığı için AnaStok'a gider,
    iptal edilen fişin stoğu ise düşüldüğü İstasyon-1'e iade edilmeli (AnaStok'a değil)."""
    first = add_order(world, 1, 180)
    ls1 = plan_batch(world, 1)
    complete(world, ls1)  # İstasyon-1: 1000 → 820
    add_order(world, 2, 220, previous=first)
    ls2 = plan_batch(world, 2)

    assert station_of(world, ls2) == world.main_stock.id
    world.session.refresh(ls1)
    assert ls1.status == "cancelled" and ls1.cancelled_by_revision

    refunds = world.session.exec(select(StockMovement).where(StockMovement.movement_type == "refund")).all()
    assert [(m.station_id, m.quantity_carton) for m in refunds] == [(world.station.id, 180)]
    station_inv = world.session.exec(
        select(StationInventory).where(StationInventory.station_id == world.station.id)
    ).one()
    assert station_inv.quantity_carton == 1000
    assert world.session.exec(
        select(StationInventory).where(StationInventory.station_id == world.main_stock.id)
    ).first() is None


# ---------- planlayıcı: bölge yükü ----------

def test_territory_load_excludes_superseded_orders(world):
    """110 → 100 revizyonu: bölge yükü 100 olmalı. Önceki sipariş de sayılırsa 210 çıkıp
    target_total_carton'u (plan ekranı) ve "çok büyük bölge" uyarısını şişiriyordu."""
    first = add_order(world, 1, 110)
    add_order(world, 2, 100, previous=first)
    loads = StationPlanner(world.session)._calculate_territory_loads(world.cycle.id)
    assert loads == {world.territory.code: 100.0}
