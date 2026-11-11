# Proje Diyagramları ve Sistem Mimarisi

## 1. Use Case Diyagramı
```mermaid
graph TD
    User["Kullanıcı / Afet Uzmanı"]
    
    subgraph System ["Uydu Görüntüleri ile Otomatik Arazi Değişimi ve Afet Hasar Tespiti Platformu"]
        UC1["Bölge ve Senaryo Seçimi Yap (Hatay/Manavgat)"]
        UC2["T1 ve T2 Çift Zamanlı Görüntü Yükle"]
        UC3["Otomatik Değişim Tespiti Analizi Başlat"]
        UC4["Slider Üzerinden T1/T2 Kıyaslaması Yap"]
        UC5["Segmentasyon Maskesi Katmanını İncele"]
        UC6["Afet/Hasar İstatistik Raporunu Görüntüle ve İndir"]
        UC7["Analiz Geçmişini Veritabanından Sorgula"]
    end

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    User --> UC6
    User --> UC7
    graph LR
    subgraph Frontend ["Kullanıcı Arayüzü (Frontend)"]
        UI["Leaflet.js / Mapbox GL JS"]
        Slider["Interactive Split-Slider Component"]
    end

    subgraph Backend ["FastAPI Sunucusu (Backend)"]
        API["REST API Layer (FastAPI)"]
        Val["Data Validator & Preprocessor"]
        Engine["ONNX Runtime Inference Engine"]
    end

    subgraph Storage ["Veri Depolama & Modeller"]
        DB[("PostgreSQL / SQLite Database")]
        Models[("Eğitilmiş ONNX Modeli (U-Net / Siamese)")]
        FileStore[("Drive / Local Storage (Images & Masks)")]
    end

    UI -->|HTTP POST: T1, T2 Images| API
    API --> Val
    Val -->|Aligned 512x512 Patches| Engine
    Engine -->|Loads Weights| Models
    Engine -->|Inference Result| API
    API -->|Save Metadata| DB
    API -->|Save Mask & Tiles| FileStore
    API -->|JSON Response| UI
    UI --> Slider
    flowchart TD
    subgraph Input ["1. Veri Kaynakları"]
        D1["SpaceNet-7"]
        D2["xBD Dataset"]
        D3["Sentinel-2 Satellite Data"]
    end

    subgraph Preprocessing ["2. Ön İşleme & Veri Hazırlama"]
        P1["Konumsal Hizalama (Co-registration)"]
        P2["Bant Normalizasyonu & Rescaling"]
        P3["512x512 Yama (Patch) Bölme"]
        P4["Data Augmentation (Albumentations)"]
    end

    subgraph Training ["3. Model Eğitimi & Doğrulama (PyTorch)"]
        M1["Bi-temporal Input Pairs (T1, T2)"]
        M2["Siamese ResNet-34 / U-Net Architecture"]
        M3["Loss Function (BCE + Dice Loss)"]
        M4["Validation (IoU & F1-Score Metrics)"]
    end

    subgraph Deployment ["4. Optimize & Servis Etme"]
        E1["PyTorch to ONNX Export"]
        E2["Quantization & Inference Optimization"]
        E3["FastAPI REST Endpoint Integration"]
    end

    Input --> Preprocessing
    P1 --> P2 --> P3 --> P4
    P4 --> Training
    M1 --> M2 --> M3 --> M4
    M4 --> Deployment
    E1 --> E2 --> E3
    flowchart TD
    Start([Başla]) --> Upload["Kullanıcı T1 ve T2 Görüntülerini Yükler"]
    Upload --> CheckFormat{"Format Uygun mu? (.png, .jpg, .tif)"}
    
    CheckFormat -- Hayır --> Err1["Hata: Geçersiz Dosya Formatı!"] --> Terminate([İşlemi Sonlandır])
    CheckFormat -- Evet --> CheckSize{"Çözünürlük ve Boyut Uygun mu?"}
    
    CheckSize -- Hayır --> Err2["Hata: Görüntü Boyutu Sınırı Aşıldı!"] --> Terminate
    CheckSize -- Evet --> Align["Görüntüleri Hizala ve 512x512 Boyutlandır"]
    Align --> Success["Veri Başarıyla Hazırlandı"] --> End([Sonraki Adıma Geç])
    flowchart TD
    Start([Başla]) --> Receive["Hizalanmış T1 ve T2 Yamalarını Al"]
    Receive --> LoadModel{"ONNX Modeli Yüklendi mi?"}
    
    LoadModel -- Hayır --> ErrModel["Hata 500: Model Yüklenemedi!"] --> Retry["Yeniden Dene"]
    Retry --> LoadModel
    
    LoadModel -- Evet --> Inference["ONNX Engine Çıkarımı Çalıştırır"]
    Inference --> CheckMemory{"Bellek Yeterli mi?"}
    
    CheckMemory -- Hayır --> ErrMem["Hata 503: Sunucu Yüklü!"] --> Abort([Analizi Durdur])
    CheckMemory -- Evet --> GenMask["İkili Değişim Maskesini Üret"]
    GenMask --> SaveDB["Veritabanına Kaydet ve JSON Dön"] --> End([Son])
    flowchart TD
    Start([Başla]) --> Fetch["Arayüz Maske ve Harita Katmanlarını Çağırır"]
    Fetch --> CheckNet{"Ağ Bağlantısı Aktif mi?"}
    
    CheckNet -- Hayır --> ErrNet["Hata: Bağlantı Kesildi!"] --> OfflineMsg["Çevrimdışı Uyarısı Göster"]
    CheckNet -- Evet --> RenderBase["Base Tile Mapbox Katmanını Yükle"]
    
    RenderBase --> RenderMask{"Değişim Maskesi GeoJSON Yüklendi mi?"}
    RenderMask -- Hayır --> ErrMask["Hata: Katman Yüklenemedi!"] --> RefreshBtn["Yeniden Yükle Butonu Göster"]
    RenderMask -- Evet --> InitSlider["Interactive Split-Slider Bileşenini Başlat"]
    InitSlider --> End([Kullanıcı Etkileşime Hazır])
