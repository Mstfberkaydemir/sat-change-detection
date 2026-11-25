"""Dosya yükleme doğrulama ve depolama yardımcıları (framework'ten bağımsız)."""
import shutil
from pathlib import Path

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


class StorageError(ValueError):
    """Geçersiz dosya (uzantı, boş, bozuk...). API'de 400'e çevrilir."""


class FileTooLargeError(StorageError):
    """Boyut sınırı aşıldı. API'de 413'e çevrilir."""


def validate_upload(filename: str, size_bytes: int, max_mb: int) -> str:
    """Uzantıyı ve boyutu doğrular; normalize edilmiş uzantıyı (ör. '.png') döndürür."""
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise StorageError(f"Geçersiz dosya formatı '{ext or filename}'. İzin verilenler: .png, .jpg, .tif")
    if size_bytes == 0:
        raise StorageError("Dosya boş")
    if size_bytes > max_mb * 1024 * 1024:
        raise FileTooLargeError(f"Görüntü boyutu sınırı aşıldı (en fazla {max_mb} MB)")
    return ext


def analysis_dir(storage_dir: Path, analysis_id: int) -> Path:
    path = Path(storage_dir) / "analyses" / str(analysis_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def relative_path(storage_dir: Path, absolute: Path) -> str:
    """DB'ye yazılacak, storage köküne göreli ve '/' ayraçlı yol."""
    return Path(absolute).resolve().relative_to(Path(storage_dir).resolve()).as_posix()


def resolve_path(storage_dir: Path, relative: str) -> Path:
    """Göreli yolu mutlak yola çevirir; storage dışına çıkan (../) yolları reddeder."""
    root = Path(storage_dir).resolve()
    path = (root / relative).resolve()
    if root != path and root not in path.parents:
        raise StorageError("Geçersiz dosya yolu")
    return path


def remove_analysis_files(storage_dir: Path, analysis_id: int) -> None:
    shutil.rmtree(Path(storage_dir) / "analyses" / str(analysis_id), ignore_errors=True)
