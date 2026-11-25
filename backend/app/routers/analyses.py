"""Analiz uç noktaları: oluştur / listele / getir / sil, görüntü yükle, analizi çalıştır, maskeyi indir."""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Analysis, ChangeMask, Image, User, utcnow
from ..schemas import AnalysisCreate, AnalysisOut
from ..services import inference, storage

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _query():
    return select(Analysis).options(selectinload(Analysis.image), selectinload(Analysis.change_mask))


def _get_owned(db: Session, analysis_id: int, user: User) -> Analysis:
    analysis = db.scalar(_query().where(Analysis.id == analysis_id, Analysis.user_id == user.id))
    if analysis is None:  # başkasının analizi de 404 döner (varlığını sızdırmaz)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analiz bulunamadı")
    return analysis


def _out(analysis: Analysis) -> AnalysisOut:
    # Oturum açıkken şemaya çevir (lazy-load / detached sorunlarını önler)
    return AnalysisOut.model_validate(analysis)


@router.post("", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
def create_analysis(payload: AnalysisCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    analysis = Analysis(user_id=user.id, title=payload.title, region_name=payload.region_name)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return _out(analysis)


@router.get("", response_model=list[AnalysisOut])
def list_analyses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.scalars(
        _query()
        .where(Analysis.user_id == user.id)
        .order_by(Analysis.analysis_date.desc(), Analysis.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return [_out(a) for a in rows]


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _out(_get_owned(db, analysis_id, user))


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    analysis = _get_owned(db, analysis_id, user)
    db.delete(analysis)
    db.commit()
    storage.remove_analysis_files(settings.storage_dir, analysis_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{analysis_id}/images", response_model=AnalysisOut)
def upload_images(
    analysis_id: int,
    t1: UploadFile = File(..., description="Afet öncesi görüntü (.png, .jpg, .tif)"),
    t2: UploadFile = File(..., description="Afet sonrası görüntü (.png, .jpg, .tif)"),
    crs_projection: Optional[str] = Form(None, description="Ör. EPSG:4326"),
    bounding_box: Optional[str] = Form(None, description="Ör. 36.1,36.0,36.3,36.3"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    analysis = _get_owned(db, analysis_id, user)

    limit_bytes = settings.max_upload_mb * 1024 * 1024
    saved = []
    try:
        for label, upload in (("t1", t1), ("t2", t2)):
            data = upload.file.read(limit_bytes + 1)  # sınırdan fazlasını belleğe almaz
            ext = storage.validate_upload(upload.filename or "", len(data), settings.max_upload_mb)
            inference.decode_image(data)  # gerçekten çözülebilen bir görüntü mü?
            saved.append((label, ext, data))
    except storage.FileTooLargeError as exc:
        raise HTTPException(413, str(exc))  # sabit adı starlette sürümlerinde değiştiği için sayı yazıldı
    except (storage.StorageError, inference.ImageDecodeError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{label}: {exc}")

    folder = storage.analysis_dir(settings.storage_dir, analysis.id)
    for old in [*folder.glob("t[12].*"), folder / "mask.png"]:  # önceki yüklemeden kalan dosyaları temizle
        old.unlink(missing_ok=True)
    paths = {}
    for label, ext, data in saved:
        target = folder / f"{label}{ext}"
        target.write_bytes(data)
        paths[label] = storage.relative_path(settings.storage_dir, target)

    if analysis.image is None:
        analysis.image = Image(
            t1_image_path=paths["t1"], t2_image_path=paths["t2"],
            crs_projection=crs_projection, bounding_box=bounding_box,
        )
    else:
        analysis.image.t1_image_path = paths["t1"]
        analysis.image.t2_image_path = paths["t2"]
        analysis.image.crs_projection = crs_projection
        analysis.image.bounding_box = bounding_box

    if analysis.change_mask is not None:  # yeni görüntüler -> eski sonuç geçersiz
        db.delete(analysis.change_mask)
        analysis.change_mask = None
    analysis.status = "images_uploaded"
    analysis.change_percentage = None
    db.commit()
    db.refresh(analysis)
    return _out(analysis)


@router.post("/{analysis_id}/run", response_model=AnalysisOut)
def run_analysis(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    analysis = _get_owned(db, analysis_id, user)
    if analysis.image is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Önce T1 ve T2 görüntülerini yükleyin")

    try:
        t1 = inference.read_image(storage.resolve_path(settings.storage_dir, analysis.image.t1_image_path))
        t2 = inference.read_image(storage.resolve_path(settings.storage_dir, analysis.image.t2_image_path))
    except (OSError, storage.StorageError, inference.ImageDecodeError) as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Görüntüler okunamadı: {exc}")

    result = inference.run_detection(t1, t2)

    mask_file = storage.analysis_dir(settings.storage_dir, analysis.id) / "mask.png"
    mask_file.write_bytes(inference.encode_png(result.mask * 255))
    mask_rel = storage.relative_path(settings.storage_dir, mask_file)

    if analysis.change_mask is None:
        analysis.change_mask = ChangeMask(mask_path=mask_rel, detected_change_pixels=result.changed_pixels)
    else:
        analysis.change_mask.mask_path = mask_rel
        analysis.change_mask.detected_change_pixels = result.changed_pixels

    analysis.change_percentage = result.change_percentage
    analysis.status = "completed"
    analysis.analysis_date = utcnow()
    db.commit()
    db.refresh(analysis)
    return _out(analysis)


@router.get("/{analysis_id}/mask", response_class=FileResponse, responses={200: {"content": {"image/png": {}}}})
def download_mask(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    analysis = _get_owned(db, analysis_id, user)
    if analysis.change_mask is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bu analiz için henüz maske üretilmedi")
    try:
        path = storage.resolve_path(settings.storage_dir, analysis.change_mask.mask_path)
    except storage.StorageError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Maske dosyası bulunamadı")
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Maske dosyası bulunamadı")
    return FileResponse(path, media_type="image/png", filename=f"analysis_{analysis_id}_mask.png")
