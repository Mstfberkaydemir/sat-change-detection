# Uydu Görüntüleri ile Otomatik Arazi Değişimi ve Afet Hasar Tespiti Platformu

Bu proje, çift zamanlı (bi-temporal) uydu görüntüleri üzerinden semantik segmentasyon (U-Net) modelleri kullanarak arazi kullanımı değişimlerini ve doğal afet sonrası yapısal hasarları piksel düzeyinde tespit eden uçtan uca bir web platformudur.

## 🛠️ Teknoloji Yığını
- **Yapay Zekâ / Model:** PyTorch, U-Net, Segmentation Models Pytorch, OpenCV
- **Backend:** Python, FastAPI, ONNX Runtime
- **Frontend:** HTML5, JavaScript, Leaflet.js (Side-by-side Image Slider)
- **Veri Setleri:** xBD / SpaceNet-7 / Sentinel-2

## 📁 Proje Yapısı
- `notebooks/`: Model eğitimi ve veri analizi defterleri (Google Colab)
- `backend/`: FastAPI REST API servis kodları
- `frontend/`: Leaflet.js harita arayüzü
- `docs/`: Sistem mimarisi ve proje belgeleri