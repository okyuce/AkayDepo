"""
Loadsheet print-token + ZPL endpoint integration testleri.
"""
import pytest
import time
from datetime import date, datetime, timedelta
from uuid import uuid4, UUID
import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.auth import SECRET_KEY, ALGORITHM, create_access_token
from app.api.loadsheets import PRINT_TOKEN_TYPE
from app.models import (
    User, Depot, Cycle, Station, StationAssignment,
    Territory, Dealer, Product, Loadsheet, LoadsheetLine,
)


@pytest.fixture
def superadmin_user(session: Session):
    """Test için basit bir superadmin — depo kısıtı yok, depot_id None."""
    user = User(
        id=uuid4(),
        username="zpl_admin",
        password_hash="x",  # şifre kullanılmıyor; token doğrudan üretilecek
        full_name="ZPL Admin",
        role="superadmin",
        is_active=True,
        depot_id=None,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def superadmin_token(superadmin_user: User):
    return create_access_token({
        "sub": superadmin_user.username,
        "user_id": str(superadmin_user.id),
        "role": superadmin_user.role,
        "depot_id": None,
    })


@pytest.fixture
def superadmin_headers(superadmin_token: str):
    return {"Authorization": f"Bearer {superadmin_token}"}


@pytest.fixture
def loadsheet_with_deps(session: Session):
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
        name="Merkez",
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
        target_total_carton=5,
        target_total_pack=10,
        depot_id=None,
    )
    dealer = Dealer(
        id=uuid4(),
        code="BAYI001",
        name="Test Bayi",
        position_code="P01",
        route_order=1,
        territory_id=territory.id,
        depot_id=None,
    )
    product = Product(
        id=uuid4(),
        code="P001",
        name="Test Ürün",
        pack_per_carton=10,
        display_order=1,
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
    line = LoadsheetLine(
        id=uuid4(),
        loadsheet_id=loadsheet.id,
        product_id=product.id,
        qty_carton=2,
        qty_pack=3,
    )
    for o in [cycle, territory, station, assignment, dealer, product, loadsheet, line]:
        session.add(o)
    session.commit()
    session.refresh(loadsheet)
    return loadsheet


# ---------- print-token endpoint ----------

def test_print_token_requires_auth(client: TestClient, loadsheet_with_deps):
    """Bearer olmadan 403 (HTTPBearer default)."""
    response = client.post(f"/v1/loadsheets/{loadsheet_with_deps.id}/print-token")
    assert response.status_code == 403


def test_print_token_returns_jwt(client: TestClient, superadmin_headers, loadsheet_with_deps):
    response = client.post(
        f"/v1/loadsheets/{loadsheet_with_deps.id}/print-token",
        headers=superadmin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "expires_in" in data
    assert data["expires_in"] > 0
    assert data["loadsheet_id"] == str(loadsheet_with_deps.id)


def test_print_token_payload_is_scoped(client: TestClient, superadmin_headers, loadsheet_with_deps):
    response = client.post(
        f"/v1/loadsheets/{loadsheet_with_deps.id}/print-token",
        headers=superadmin_headers,
    )
    token = response.json()["token"]
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["type"] == PRINT_TOKEN_TYPE
    assert decoded["ls"] == str(loadsheet_with_deps.id)


def test_print_token_unknown_loadsheet_404(client: TestClient, superadmin_headers):
    response = client.post(
        f"/v1/loadsheets/{uuid4()}/print-token",
        headers=superadmin_headers,
    )
    assert response.status_code == 404


# ---------- ZPL endpoint ----------

def test_zpl_endpoint_without_token_401(client: TestClient, loadsheet_with_deps):
    response = client.get(f"/v1/loadsheets/{loadsheet_with_deps.id}/zpl")
    assert response.status_code == 401


def test_zpl_endpoint_invalid_token_401(client: TestClient, loadsheet_with_deps):
    response = client.get(
        f"/v1/loadsheets/{loadsheet_with_deps.id}/zpl",
        params={"token": "not-a-jwt"},
    )
    assert response.status_code == 401


def test_zpl_endpoint_wrong_token_type_401(client: TestClient, loadsheet_with_deps):
    """Normal session JWT'si print-token yerine geçmemeli."""
    wrong = jwt.encode(
        {"type": "session", "ls": str(loadsheet_with_deps.id), "exp": datetime.now() + timedelta(minutes=5)},
        SECRET_KEY, algorithm=ALGORITHM,
    )
    response = client.get(
        f"/v1/loadsheets/{loadsheet_with_deps.id}/zpl",
        params={"token": wrong},
    )
    assert response.status_code == 401


def test_zpl_endpoint_token_for_other_ls_403(client: TestClient, loadsheet_with_deps):
    other_ls_id = uuid4()
    token = jwt.encode(
        {
            "type": PRINT_TOKEN_TYPE,
            "ls": str(other_ls_id),
            "exp": datetime.now() + timedelta(minutes=2),
        },
        SECRET_KEY, algorithm=ALGORITHM,
    )
    response = client.get(
        f"/v1/loadsheets/{loadsheet_with_deps.id}/zpl",
        params={"token": token},
    )
    assert response.status_code == 403


def test_zpl_endpoint_expired_token_401(client: TestClient, loadsheet_with_deps):
    # PyJWT 2.x datetime'ı UTC olarak yorumladığı için integer epoch kullan.
    expired = jwt.encode(
        {
            "type": PRINT_TOKEN_TYPE,
            "ls": str(loadsheet_with_deps.id),
            "exp": int(time.time()) - 60,
        },
        SECRET_KEY, algorithm=ALGORITHM,
    )
    response = client.get(
        f"/v1/loadsheets/{loadsheet_with_deps.id}/zpl",
        params={"token": expired},
    )
    assert response.status_code == 401


def test_zpl_endpoint_returns_zpl_with_valid_token(
    client: TestClient, superadmin_headers, loadsheet_with_deps,
):
    """Tam akış: print-token al → ZPL fetch et."""
    token_resp = client.post(
        f"/v1/loadsheets/{loadsheet_with_deps.id}/print-token",
        headers=superadmin_headers,
    )
    token = token_resp.json()["token"]

    zpl_resp = client.get(
        f"/v1/loadsheets/{loadsheet_with_deps.id}/zpl",
        params={"token": token},
    )
    assert zpl_resp.status_code == 200
    assert zpl_resp.headers["content-type"].startswith("text/plain")
    assert zpl_resp.headers["cache-control"] == "no-store"
    zpl = zpl_resp.text
    assert zpl.startswith("^XA")
    assert zpl.rstrip().endswith("^XZ")
    assert "Test Bayi" in zpl
    assert "Test Ürün" in zpl
    assert "TOPLAM" in zpl


def test_zpl_endpoint_sets_printed_at(
    client: TestClient, session: Session, superadmin_headers, loadsheet_with_deps,
):
    assert loadsheet_with_deps.printed_at is None

    token_resp = client.post(
        f"/v1/loadsheets/{loadsheet_with_deps.id}/print-token",
        headers=superadmin_headers,
    )
    token = token_resp.json()["token"]

    client.get(
        f"/v1/loadsheets/{loadsheet_with_deps.id}/zpl",
        params={"token": token},
    )

    # Refresh from DB
    session.refresh(loadsheet_with_deps)
    assert loadsheet_with_deps.printed_at is not None


def test_zpl_endpoint_unknown_loadsheet_404(client: TestClient):
    """Token geçerli olsa bile fiş yoksa 404."""
    fake_id = uuid4()
    # Önce token üret (ama loadsheet yok; print-token endpoint'i 404 verir).
    # Buradaki test: zpl endpoint'i direkt yanlış token ile değil, geçerli token + DB'de
    # olmayan loadsheet senaryosunu test eder. Yine 403/404 makul — token tutarsız.
    token = jwt.encode(
        {
            "type": PRINT_TOKEN_TYPE,
            "ls": str(fake_id),
            "exp": datetime.now() + timedelta(minutes=2),
        },
        SECRET_KEY, algorithm=ALGORITHM,
    )
    response = client.get(
        f"/v1/loadsheets/{fake_id}/zpl",
        params={"token": token},
    )
    assert response.status_code == 404
