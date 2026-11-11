# Veritabanı Mimarisi ve Figma Prototip Tasarımı

## 1. ER (Entity-Relationship) Diyagramı
```mermaid
erDiagram
    USERS ||--o{ ANALYSES : "creates"
    ANALYSES ||--|| IMAGES : "uses"
    ANALYSES ||--|| CHANGE_MASKS : "generates"

    USERS {
        int id PK
        string username
        string email
        string role
        datetime created_at
    }

    ANALYSES {
        int id PK
        int user_id FK
        string title
        string region_name
        float change_percentage
        float mean_iou
        datetime analysis_date
    }

    IMAGES {
        int id PK
        int analysis_id FK
        string t1_image_path
        string t2_image_path
        string crs_projection
        string bounding_box
    }

    CHANGE_MASKS {
        int id PK
        int analysis_id FK
        string mask_path
        string geojson_path
        int detected_change_pixels
    }
    
2. Veri Sözlüğü (Data Dictionary)

Tablo: users
Alan Adı Veri Tipi Kısıtlama Açıklama 
id INTEGER PRIMARY KEY, AUTOINC Benzersiz kullanıcı ID
username VARCHAR(50) NOT NULL, UNIQUE Kullanıcı adı
email VARCHAR(100) NOT NULL, UNIQUE E-posta adresi
role VARCHAR(20) DEFAULT 'analyst' Rol (Admin/Analyst)
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP Kayıt tarihi

Tablo: analyses
Alan Adı Veri Tipi Kısıtlama Açıklama
id INTEGER PRIMARY KEY, AUTOINC Analiz ID
user_id INTEGER FOREIGN KEY (users.id) Analizi yapan kullanıcı ID
title VARCHAR(100) NOT NULL Analiz başlığı
region_name VARCHAR(50) NOT NULL İnceleme bölgesi
change_percentage FLOAT NOT NULL Değişim yüzdesi (%)
mean_iou FLOAT NULLABLE Güvenilirlik skoru
analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP İşlem tarihi

Tablo: images
Alan Adı Veri Tipi Kısıtlama Açıklama
id INTEGER PRIMARY KEY, AUTOINC Görüntü kaydı ID
analysis_id INTEGER FOREIGN KEY (analyses.id) İlgili analiz ID
t1_image_path VARCHAR(255) NOT NULL T1 görüntü dosya yolu
t2_image_path VARCHAR(255)NOT NULL T2 görüntü dosya yolu
crs_projection VARCHAR(30) DEFAULT 'EPSG:4326' Koordinat referansı
bounding_box VARCHAR(100) NULLABLE Bounding box koordinatları

Tablo: change_masks
Alan Adı Veri Tipi Kısıtlama Açıklama
id INTEGER PRIMARY KEY, AUTOINC Maske kaydı ID
analysis_id INTEGER FOREIGN KEY (analyses.id) Bağlı analiz ID
mask_path VARCHAR(255) NOT NULL Değişim maskesi PNG/GeoTIFF yolu
geojson_path VARCHAR(255) NULLABLE Vektör GeoJSON yolu
detected_change_pixels INTEGER NOT NULL Değişen piksel sayısı

3. Figma Tıklanabilir Prototip (6 Ekran Mimarisi)
Screen 1 — Landing Page / Dashboard: Sistem tanıtımı ve 12. Kalkınma Planı afete hazırlık vurgulu giriş.
Screen 2 — Region & Dataset Selection: Bölge (Hatay/Manavgat) ve uydu tipi (Sentinel-2/SpaceNet-7/xBD) seçimi.
Screen 3 — Image Upload & Preprocessing UI: T1 ve T2 görsellerini yükleme, otomatik hizalama paneli.
Screen 4 — Interactive Split-Slider Viewer: Canlı T1-T2 karşılaştırmalı kaydırmalı harita ekranı.
Screen 5 — AI Segmentation & Heatmap Layer: Yapay zeka çıktı maskesi ve katman opaklık kontrolü.
Screen 6 — Damage Statistics & Export Report: % Değişim analizi, metrik istatistikleri ve PDF/GeoJSON indirme.
