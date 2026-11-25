# Aşama 4 – Backend İskeleti (FastAPI)

Tüm komutlar **`backend/`** klasöründen çalıştırılır.

## Kurulum

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate      |  Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env          # Windows: copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # çıkan değeri .env içindeki SECRET_KEY'e yazın
```

## Veritabanı (migration)

```bash
alembic upgrade head          # tabloları oluşturur (users, analyses, images, change_masks)
alembic current               # 0001 (head) görmelisiniz
alembic downgrade base        # (isteğe bağlı) hepsini geri alır
```

Modeli değiştirirseniz yeni migration üretin:

```bash
alembic revision --autogenerate -m "aciklama"
alembic upgrade head
```

## Çalıştırma

```bash
uvicorn app.main:app --reload
```

- Swagger arayüzü: http://127.0.0.1:8000/docs  (sağ üstte **Authorize**: önce `/auth/register`, sonra `/auth/login` ile alınan kullanıcı adı/şifreyi girin)
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json
- Postman: `postman/afet-hasar-api.postman_collection.json` dosyasını **Import** edin (sıra: Register → Login → Create analysis → Upload → Run → Download mask; Login testi token'ı otomatik kaydeder)

## Uç noktalar

| Metot | Yol | Açıklama | Yetki |
|---|---|---|---|
| GET | `/health` | Sağlık kontrolü | – |
| POST | `/auth/register` | Kayıt | – |
| POST | `/auth/login` | Giriş (form: username, password) → JWT | – |
| GET | `/auth/me` | Mevcut kullanıcı | JWT |
| POST | `/analyses` | Analiz oluştur (title, region_name) | JWT |
| GET | `/analyses` | Kendi analizlerini listele (`skip`, `limit`) | JWT |
| GET | `/analyses/{id}` | Analiz detayı | JWT |
| DELETE | `/analyses/{id}` | Analizi ve dosyalarını sil | JWT |
| POST | `/analyses/{id}/images` | T1 ve T2 yükle (multipart: `t1`, `t2`; opsiyonel `crs_projection`, `bounding_box`) | JWT |
| POST | `/analyses/{id}/run` | Değişim tespitini çalıştır | JWT |
| GET | `/analyses/{id}/mask` | Maskeyi PNG olarak indir | JWT |

## Testler

```bash
pytest -v
```

`tests/test_services.py` çekirdek mantığı (şifre, JWT, dosya doğrulama, değişim tespiti), `tests/test_api.py` uçtan uca akışı
(kayıt → giriş → analiz → yükleme → çalıştırma → maske) ve yetki sınırlarını (kullanıcılar birbirinin analizini göremez) sınar.

## Tasarım notları

- **ER diyagramına eklenenler:** `users.password_hash` (kimlik doğrulama için zorunlu) ve `analyses.status`.
  Diyagramı güncellemek isterseniz bu iki alanı `USERS` ve `ANALYSES` tablolarına ekleyin.
- **Şifreler** PBKDF2-SHA256 (600.000 iterasyon, tuzlu) ile saklanır; düz metin hiçbir yerde tutulmaz.
- **Dosya yolları** DB'de `STORAGE_DIR`'a göreli saklanır; `../` ile dışarı çıkış engellenir.
- **Yükleme doğrulaması:** uzantı (.png/.jpg/.tif), boyut sınırı (`MAX_UPLOAD_MB`) ve içeriğin gerçekten çözülebilir görüntü olması.
- **Çıkarım:** şimdilik klasik baseline (`app/services/inference.py`). Aşama 5'te ONNX modeli aynı `ChangeDetector`
  arayüzüyle eklenecek; endpoint kodu değişmeyecek.
- **Bilinen sınırlar (bilerek):** `mean_iou` yalnızca referans maske varken hesaplanabildiği için şimdilik boş döner;
  `geojson_path` coğrafi referanslama (Aşama 5) gelince doldurulacak; çok bantlı/16-bit GeoTIFF'ler 8-bit RGB'ye indirgenir.
- **PostgreSQL:** `.env` içinde `DATABASE_URL`'i değiştirin ve `requirements.txt` içindeki `psycopg2-binary` satırını açın.
