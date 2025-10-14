import io
import re
import pytest
from app import create_app
from app.models import (
    Accessorial,
    AirCostZone,
    BeyondRate,
    CostZone,
    HotshotRate,
    RateUpload,
    User,
    ZipZone,
    db,
)
from config import Config
from quote.theme import init_fsi_theme


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        init_fsi_theme(app)
        db.create_all()
        admin = User(
            name="Admin",
            email="admin@example.com",
            role="super_admin",
        )
        admin.set_password("StrongPass!1234")
        db.session.add(admin)
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    resp = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True)
    ).group(1)
    client.post(
        "/login",
        data={
            "email": "admin@example.com",
            "password": "StrongPass!1234",
            "csrf_token": token,
        },
        follow_redirects=False,
    )


def get_csrf(client, path):
    resp = client.get(path, follow_redirects=True)
    match = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"', resp.get_data(as_text=True)
    )
    return match.group(1) if match else ""


def test_manage_accessorials(client, app):
    login(client)
    token = get_csrf(client, "/admin/accessorials/new")
    resp = client.post(
        "/admin/accessorials/new",
        data={"name": "Liftgate", "amount": "50", "csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        acc = Accessorial.query.filter_by(name="Liftgate").first()
        assert acc is not None
        acc_id = acc.id
    token = get_csrf(client, f"/admin/accessorials/{acc_id}/edit")
    resp = client.post(
        f"/admin/accessorials/{acc_id}/edit",
        data={
            "name": "Liftgate2",
            "amount": "75",
            "is_percentage": "y",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        acc = db.session.get(Accessorial, acc_id)
        assert acc.name == "Liftgate2"
        assert acc.is_percentage is True
    token = get_csrf(client, "/admin/accessorials")
    resp = client.post(
        f"/admin/accessorials/{acc_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(Accessorial, acc_id) is None


def test_manage_beyond_rates(client, app):
    login(client)
    token = get_csrf(client, "/admin/beyond_rates/new")
    resp = client.post(
        "/admin/beyond_rates/new",
        data={"zone": "A", "rate": "1.5", "up_to_miles": "10", "csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        br = BeyondRate.query.filter_by(zone="A").first()
        assert br is not None
        br_id = br.id
    token = get_csrf(client, f"/admin/beyond_rates/{br_id}/edit")
    resp = client.post(
        f"/admin/beyond_rates/{br_id}/edit",
        data={"zone": "B", "rate": "2.0", "up_to_miles": "15", "csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        br = db.session.get(BeyondRate, br_id)
        assert br.zone == "B"
        assert br.rate == 2.0
    token = get_csrf(client, "/admin/beyond_rates")
    resp = client.post(
        f"/admin/beyond_rates/{br_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(BeyondRate, br_id) is None


def test_manage_hotshot_rates(client, app):
    login(client)
    token = get_csrf(client, "/admin/hotshot_rates/new")
    resp = client.post(
        "/admin/hotshot_rates/new",
        data={
            "miles": "100",
            "zone": "A",
            "per_lb": "1.0",
            "min_charge": "50",
            "weight_break": "500",
            "fuel_pct": "0.1",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        hs = HotshotRate.query.filter_by(miles=100).first()
        assert hs is not None
        hs_id = hs.id
    token = get_csrf(client, f"/admin/hotshot_rates/{hs_id}/edit")
    resp = client.post(
        f"/admin/hotshot_rates/{hs_id}/edit",
        data={
            "miles": "150",
            "zone": "B",
            "per_lb": "1.2",
            "min_charge": "60",
            "weight_break": "600",
            "fuel_pct": "0.15",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        hs = db.session.get(HotshotRate, hs_id)
        assert hs.miles == 150
        assert hs.zone == "B"
    token = get_csrf(client, "/admin/hotshot_rates")
    resp = client.post(
        f"/admin/hotshot_rates/{hs_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(HotshotRate, hs_id) is None


def test_manage_zip_zones(client, app):
    login(client)
    token = get_csrf(client, "/admin/zip_zones/new")
    resp = client.post(
        "/admin/zip_zones/new",
        data={"zipcode": "85001", "dest_zone": "1", "beyond": "", "csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        zz = ZipZone.query.filter_by(zipcode="85001").first()
        assert zz is not None
        zz_id = zz.id
    token = get_csrf(client, f"/admin/zip_zones/{zz_id}/edit")
    resp = client.post(
        f"/admin/zip_zones/{zz_id}/edit",
        data={
            "zipcode": "85002",
            "dest_zone": "2",
            "beyond": "A",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        zz = db.session.get(ZipZone, zz_id)
        assert zz.zipcode == "85002"
        assert zz.dest_zone == 2
    token = get_csrf(client, "/admin/zip_zones")
    resp = client.post(
        f"/admin/zip_zones/{zz_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(ZipZone, zz_id) is None


def test_manage_cost_zones(client, app):
    login(client)
    token = get_csrf(client, "/admin/cost_zones/new")
    resp = client.post(
        "/admin/cost_zones/new",
        data={"concat": "12", "cost_zone": "A", "csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        cz = CostZone.query.filter_by(concat="12").first()
        assert cz is not None
        cz_id = cz.id
    token = get_csrf(client, f"/admin/cost_zones/{cz_id}/edit")
    resp = client.post(
        f"/admin/cost_zones/{cz_id}/edit",
        data={"concat": "13", "cost_zone": "B", "csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        cz = db.session.get(CostZone, cz_id)
        assert cz.concat == "13"
        assert cz.cost_zone == "B"
    token = get_csrf(client, "/admin/cost_zones")
    resp = client.post(
        f"/admin/cost_zones/{cz_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(CostZone, cz_id) is None


def test_manage_air_cost_zones(client, app):
    login(client)
    token = get_csrf(client, "/admin/air_cost_zones/new")
    resp = client.post(
        "/admin/air_cost_zones/new",
        data={
            "zone": "A",
            "min_charge": "50",
            "per_lb": "1.5",
            "weight_break": "100",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        acz = AirCostZone.query.filter_by(zone="A").first()
        assert acz is not None
        acz_id = acz.id
    token = get_csrf(client, f"/admin/air_cost_zones/{acz_id}/edit")
    resp = client.post(
        f"/admin/air_cost_zones/{acz_id}/edit",
        data={
            "zone": "B",
            "min_charge": "60",
            "per_lb": "1.8",
            "weight_break": "120",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        acz = db.session.get(AirCostZone, acz_id)
        assert acz.zone == "B"
        assert acz.per_lb == 1.8
    token = get_csrf(client, "/admin/air_cost_zones")
    resp = client.post(
        f"/admin/air_cost_zones/{acz_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(AirCostZone, acz_id) is None


def test_upload_zip_zones(client, app):
    login(client)
    token = get_csrf(client, "/admin/zip_zones/upload")
    csv_data = "ZIP Code,Dest Zone,Beyond\n85001,1,\n"
    resp = client.post(
        "/admin/zip_zones/upload",
        data={
            "file": (io.BytesIO(csv_data.encode("utf-8")), "Zipcode_Zones.csv"),
            "action": "add",
            "csrf_token": token,
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert ZipZone.query.filter_by(zipcode="85001").first() is not None
        upload = RateUpload.query.filter_by(filename="Zipcode_Zones.csv").first()
        assert upload is not None
        assert upload.table_name == "zip_zones"


def test_upload_zip_zones_replace_overwrites_existing(client, app):
    login(client)
    with app.app_context():
        db.session.add(ZipZone(zipcode="85001", dest_zone=1, beyond=None))
        db.session.commit()
    token = get_csrf(client, "/admin/zip_zones/upload")
    csv_data = "ZIP Code,Dest Zone,Beyond\n85002,2,\n"
    resp = client.post(
        "/admin/zip_zones/upload",
        data={
            "file": (io.BytesIO(csv_data.encode("utf-8")), "Zipcode_Zones.csv"),
            "action": "replace",
            "csrf_token": token,
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert ZipZone.query.filter_by(zipcode="85001").first() is None
        replacement = ZipZone.query.filter_by(zipcode="85002").first()
        assert replacement is not None


def test_upload_zip_zones_rejects_wrong_headers(client):
    login(client)
    token = get_csrf(client, "/admin/zip_zones/upload")
    csv_data = "ZIPCODE,DEST ZONE,BEYOND\n85001,1,\n"
    resp = client.post(
        "/admin/zip_zones/upload",
        data={
            "file": (io.BytesIO(csv_data.encode("utf-8")), "Zipcode_Zones.csv"),
            "action": "add",
            "csrf_token": token,
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert "CSV headers must exactly match" in resp.get_data(as_text=True)


def test_download_zip_zones_returns_csv(client, app):
    login(client)
    with app.app_context():
        db.session.add(ZipZone(zipcode="85001", dest_zone=1, beyond=None))
        db.session.commit()
    resp = client.get("/admin/zip_zones/download")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    body = resp.get_data(as_text=True).splitlines()
    assert body[0] == "ZIP Code,Dest Zone,Beyond"
    assert "85001" in body[1]


def test_accessorial_requires_csrf(client, app):
    login(client)
    resp = client.post(
        "/admin/accessorials/new",
        data={"name": "No Token"},
        follow_redirects=False,
    )
    assert resp.status_code == 400
