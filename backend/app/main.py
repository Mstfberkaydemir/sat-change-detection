"""FastAPI uygulaması. Swagger: /docs  |  ReDoc: /redoc  |  OpenAPI JSON: /openapi.json"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import analyses, auth

API_VERSION = "0.1.0"

DESCRIPTION = """
Uydu görüntüleri ile otomatik arazi değişimi ve afet hasar tespiti platformunun REST API'si.

**Akış:** `POST /auth/register` → `POST /auth/login` → (Swagger'da **Authorize**) →
`POST /analyses` → `POST /analyses/{id}/images` → `POST /analyses/{id}/run` → `GET /analyses/{id}/mask`
"""

TAGS = [
    {"name": "system", "description": "Sağlık kontrolü"},
    {"name": "auth", "description": "Kayıt, giriş (JWT) ve mevcut kullanıcı"},
    {"name": "analyses", "description": "Analiz oluşturma, görüntü yükleme, çalıştırma ve sonuçlar"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.app_name,
    version=API_VERSION,
    description=DESCRIPTION,
    openapi_tags=TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analyses.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "version": API_VERSION}
