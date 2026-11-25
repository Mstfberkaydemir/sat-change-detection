"""Uçtan uca API testleri (kayıt -> giriş -> analiz -> yükleme -> çalıştırma -> maske)."""
import cv2
import numpy as np


def png_bytes(changed: bool) -> bytes:
    img = np.full((128, 128, 3), 100, np.uint8)
    if changed:
        img[40:90, 40:90] = (30, 200, 220)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def register(client, username="berkay", email=None, password="gizli-sifre-1"):
    return client.post(
        "/auth/register",
        json={"username": username, "email": email or f"{username}@example.com", "password": password},
    )


def auth_headers(client, username="berkay", password="gizli-sifre-1"):
    register(client, username, password=password)
    resp = client.post("/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def new_analysis(client, headers, title="Hatay analizi", region="Hatay"):
    resp = client.post("/analyses", json={"title": title, "region_name": region}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def upload(client, headers, analysis_id, t1=None, t2=None, t1_name="t1.png", t2_name="t2.png"):
    files = {
        "t1": (t1_name, t1 if t1 is not None else png_bytes(False), "image/png"),
        "t2": (t2_name, t2 if t2 is not None else png_bytes(True), "image/png"),
    }
    return client.post(f"/analyses/{analysis_id}/images", files=files, headers=headers)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_login_me(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "berkay" and body["role"] == "analyst"
    assert "password" not in body and "password_hash" not in body

    headers = auth_headers(client)
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["email"] == "berkay@example.com"


def test_register_duplicate_and_validation(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409
    assert register(client, username="baska", email="berkay@example.com").status_code == 409
    assert register(client, username="ab").status_code == 422  # çok kısa
    assert register(client, username="yeni", email="gecersiz").status_code == 422
    assert register(client, username="yeni2", password="kisa").status_code == 422


def test_login_wrong_password(client):
    register(client)
    resp = client.post("/auth/login", data={"username": "berkay", "password": "yanlis-sifre"})
    assert resp.status_code == 401
    resp = client.post("/auth/login", data={"username": "yok", "password": "gizli-sifre-1"})
    assert resp.status_code == 401


def test_protected_endpoints_require_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/analyses").status_code == 401
    assert client.post("/analyses", json={"title": "a", "region_name": "b"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer sacma"}).status_code == 401


def test_analysis_crud_and_pagination(client):
    headers = auth_headers(client)
    first = new_analysis(client, headers, "ilk", "Hatay")
    assert first["status"] == "created" and first["image"] is None and first["change_mask"] is None
    new_analysis(client, headers, "ikinci", "Manavgat")

    listed = client.get("/analyses", headers=headers).json()
    assert len(listed) == 2
    assert len(client.get("/analyses?limit=1", headers=headers).json()) == 1
    assert client.get("/analyses?limit=0", headers=headers).status_code == 422

    assert client.get(f"/analyses/{first['id']}", headers=headers).json()["title"] == "ilk"
    assert client.delete(f"/analyses/{first['id']}", headers=headers).status_code == 204
    assert client.get(f"/analyses/{first['id']}", headers=headers).status_code == 404


def test_users_cannot_access_each_others_analyses(client):
    h1 = auth_headers(client, "kullanici1")
    h2 = auth_headers(client, "kullanici2")
    analysis = new_analysis(client, h1)
    assert client.get(f"/analyses/{analysis['id']}", headers=h2).status_code == 404
    assert client.delete(f"/analyses/{analysis['id']}", headers=h2).status_code == 404
    assert client.post(f"/analyses/{analysis['id']}/run", headers=h2).status_code == 404
    assert client.get("/analyses", headers=h2).json() == []


def test_upload_rejects_bad_files(client):
    headers = auth_headers(client)
    aid = new_analysis(client, headers)["id"]
    assert upload(client, headers, aid, t1=b"metin", t1_name="t1.txt").status_code == 400  # uzantı
    assert upload(client, headers, aid, t2=b"bu resim degil").status_code == 400  # bozuk içerik
    assert upload(client, headers, aid, t1=b"", t1_name="t1.png").status_code in (400, 422)  # boş dosya


def test_run_requires_images(client):
    headers = auth_headers(client)
    aid = new_analysis(client, headers)["id"]
    assert client.post(f"/analyses/{aid}/run", headers=headers).status_code == 409
    assert client.get(f"/analyses/{aid}/mask", headers=headers).status_code == 404


def test_full_flow(client):
    headers = auth_headers(client)
    aid = new_analysis(client, headers)["id"]

    up = upload(client, headers, aid)
    assert up.status_code == 200, up.text
    body = up.json()
    assert body["status"] == "images_uploaded"
    assert body["image"]["t1_image_path"] == f"analyses/{aid}/t1.png"

    run = client.post(f"/analyses/{aid}/run", headers=headers)
    assert run.status_code == 200, run.text
    result = run.json()
    assert result["status"] == "completed"
    assert 12 < result["change_percentage"] < 22
    assert result["change_mask"]["detected_change_pixels"] > 0

    mask = client.get(f"/analyses/{aid}/mask", headers=headers)
    assert mask.status_code == 200
    assert mask.headers["content-type"] == "image/png"
    decoded = cv2.imdecode(np.frombuffer(mask.content, np.uint8), cv2.IMREAD_GRAYSCALE)
    assert decoded.shape == (128, 128) and set(np.unique(decoded)) <= {0, 255}

    # Aynı analize yeniden yükleme eski sonucu sıfırlar
    again = upload(client, headers, aid)
    assert again.status_code == 200
    assert again.json()["status"] == "images_uploaded"
    assert again.json()["change_mask"] is None and again.json()["change_percentage"] is None
