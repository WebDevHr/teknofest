# Modern Kamera Uygulaması

PyQt5 ile geliştirilmiş modern, tam ekran kamera uygulaması. Balon tespiti, angajman tespiti ve şekil tespiti özelliklerine sahiptir.

## Özellikler

- Tam ekran kamera görüntüsü
- Animasyonlu kenar çubukları
- Log görüntüleme ve kaydetme
- Görüntü yakalama ve kaydetme
- Derin öğrenme tabanlı nesne tespiti
- Klasik görüntü işleme ile şekil tespiti
- Açık/koyu tema desteği

## Kurulum

1. Projeyi klonlayın:
```
git clone https://github.com/kullanici/kamera-app.git
cd kamera-app
```

2. Gereksinimleri yükleyin:
```
pip install -r requirements.txt
```

3. İlk kurulum:
```
python setup_data_dir.py
```

4. .env.example dosyasını kopyalayıp .env olarak kaydedin ve gerekli ayarları yapın:
```
cd camera_app
cp .env.example .env
```

5. .env dosyasını düzenleyin:
```
# Ana veri dizini (varsayılan: proje_dizini/data)
DATA_DIR=C:\\path\\to\\your\\data

# Model dizini
MODEL_DIR=C:\\path\\to\\your\\models

# Model dosyaları
BALLOON_MODEL=bests_balloon_30_dark.pt
ENGAGEMENT_MODEL=engagement-best.pt
```

## Dizin Yapısı

Yeni düzenlenmiş dizin yapısı:

```
proje_kök/
├── camera_app/             # Ana uygulama kodu
│   ├── icons/              # Uygulama ikonları
│   ├── models/             # Model dosyaları (yolo, vb.)
│   ├── services/           # Servis modülleri
│   ├── ui/                 # Kullanıcı arayüzü bileşenleri
│   ├── utils/              # Yardımcı modüller
│   ├── .env                # Çevresel değişkenler (gizli)
│   └── .env.example        # Örnek çevresel değişkenler
│
├── data/                   # Veri dizini
│   ├── captures/           # Yakalanan görüntüler
│   └── logs/               # Log dosyaları
│
├── .gitignore              # Git tarafından yoksayılacak dosyalar
├── README.md               # Bu dosya
├── requirements.txt        # Python bağımlılıkları
└── setup_data_dir.py       # Kurulum betiği
```

## Çalıştırma

Uygulamayı çalıştırmak için:

```
cd camera_app
python main.py
```

## Geliştiriciler İçin

Yeni eklenen bir gizli model veya hassas yolu varsa, lütfen `.env` dosyasına ekleyin ve `.env.example` dosyasını güncelleyin. Bu şekilde diğer geliştiriciler kendi ortamlarını nasıl yapılandıracaklarını bileceklerdir.

## Lisans

Bu proje [LICENSE] altında lisanslanmıştır. 