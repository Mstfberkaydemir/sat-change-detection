"""Framework'ten bağımsız çekirdek mantık testleri (güvenlik, depolama, çıkarım)."""
import cv2
import numpy as np
import pytest

from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.services import inference, storage


def test_password_hash_roundtrip():
    stored = hash_password("gizli-sifre-1")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("gizli-sifre-1", stored)
    assert not verify_password("yanlis", stored)
    assert not verify_password("x", "bozuk-format")
    assert not verify_password("x", "a$b$c$d")


def test_hash_is_salted():
    assert hash_password("ayni-sifre") != hash_password("ayni-sifre")


def test_jwt_roundtrip_and_failures():
    key = "k" * 40
    token = create_access_token("12", key, "HS256", 5)
    assert decode_access_token(token, key, "HS256") == "12"
    assert decode_access_token(token, "z" * 40, "HS256") is None
    assert decode_access_token("sacma", key, "HS256") is None
    assert decode_access_token(create_access_token("1", key, "HS256", -1), key, "HS256") is None


def test_validate_upload():
    assert storage.validate_upload("a.PNG", 10, 50) == ".png"
    for name, size in [("a.txt", 10), ("noext", 10), ("a.png", 0)]:
        with pytest.raises(storage.StorageError):
            storage.validate_upload(name, size, 50)
    with pytest.raises(storage.FileTooLargeError):
        storage.validate_upload("a.png", 51 * 1024 * 1024, 50)


def test_path_helpers_block_traversal(tmp_path):
    folder = storage.analysis_dir(tmp_path, 7)
    f = folder / "t1.png"
    f.write_bytes(b"x")
    rel = storage.relative_path(tmp_path, f)
    assert rel == "analyses/7/t1.png"
    assert storage.resolve_path(tmp_path, rel) == f.resolve()
    with pytest.raises(storage.StorageError):
        storage.resolve_path(tmp_path, "../etc/passwd")
    storage.remove_analysis_files(tmp_path, 7)
    assert not folder.exists()


def _pair():
    t1 = np.full((128, 128, 3), 100, np.uint8)
    t2 = t1.copy()
    t2[40:90, 40:90] = (30, 200, 220)
    return t1, t2


def test_detection_finds_changed_square():
    t1, t2 = _pair()
    result = inference.run_detection(t1, t2)
    assert 12 < result.change_percentage < 22  # gerçek kare alanı ~%15,3
    assert result.mask.shape == (128, 128)


def test_detection_no_change_and_global_brightness_shift():
    t1, _ = _pair()
    assert inference.run_detection(t1, t1).change_percentage == 0.0
    brighter = np.clip(t1.astype(int) + 15, 0, 255).astype(np.uint8)
    assert inference.run_detection(t1, brighter).change_percentage == 0.0


def test_detection_handles_different_sizes():
    t1, t2 = _pair()
    small = cv2.resize(t2, (64, 64))
    assert 8 < inference.run_detection(t1, small).change_percentage < 25


def test_decode_and_encode():
    t1, _ = _pair()
    png = inference.encode_png(t1)
    assert inference.decode_image(png).shape == (128, 128, 3)
    with pytest.raises(inference.ImageDecodeError):
        inference.decode_image(b"bu bir resim degil")


def test_read_image_non_ascii_path(tmp_path):
    t1, _ = _pair()
    folder = tmp_path / "türkçe_klasör"
    folder.mkdir()
    (folder / "ş.png").write_bytes(inference.encode_png(t1))
    assert inference.read_image(folder / "ş.png").shape == (128, 128, 3)
