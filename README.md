# Modern 2 DOF pan-tilt sistem

## Proje Genel Bakış ve Mimari Detaylar

Bu proje, PyQt5 kullanılarak geliştirilmiş, modern ve tam ekran çalışan bir kamera uygulamasıdır. Uygulamanın temel amacı, kamera görüntüsü üzerinden gerçek zamanlı olarak balon, şekil ve angajman tahtası tespiti gibi görevleri yerine getirmek ve kullanıcıya sezgisel, hızlı bir arayüz sunmaktır. Proje, hem kullanıcı deneyimi hem de geliştirici deneyimi açısından birçok iyi yazılım pratiğini barındırır.

### 1. Modüler ve Servis Tabanlı Mimari

Uygulamanın ana felsefesi, her işlevin kendi bağımsız servisi içinde yönetilmesidir. Bu sayede kodun bakımı, test edilmesi ve genişletilmesi oldukça kolaylaşır. Servisler, genellikle Singleton veya Observer gibi tasarım desenleriyle yazılmıştır.

#### a. LoggerService
- **Amaç:** Uygulama genelinde loglama yapmak, hata ve bilgi mesajlarını dosyaya ve arayüze aktarmak.
- **Özellikler:**  
  - Singleton olarak tasarlanmıştır, yani uygulamanın her yerinden aynı örneğe erişilir.
  - Thread-safe (çoklu iş parçacığına dayanıklı) olacak şekilde mutex kullanır.
  - Logları hem dosyaya hem de arayüzdeki log paneline aktarır.
  - Farklı seviyelerde loglama (info, warning, error) destekler.

#### b. CameraService
- **Amaç:** Kameradan görüntü almak, görüntüleri işlemek ve arayüze aktarmak.
- **Özellikler:**  
  - PyQt sinyalleriyle (signals) çalışır, böylece arayüzle kolayca entegre olur.
  - Kamera başlatma, durdurma, görüntü yakalama ve FPS hesaplama gibi işlevler içerir.
  - Hataları kendi içinde yakalar ve LoggerService ile loglar.

#### c. BalloonDetectorService
- **Amaç:** Kamera görüntüsünde balon tespiti ve takibi yapmak.
- **Özellikler:**  
  - Derin öğrenme (YOLO) ve klasik görüntü işleme yöntemlerini bir arada kullanabilir.
  - Kalman filtresi ile balon takibi yapar.
  - Hataları kendi içinde yakalar ve loglar.
  - Tespit edilen balonları arayüze sinyal olarak iletir.

#### d. EngagementBoardService
- **Amaç:** Angajman tahtası üzerindeki karakterleri (A/B) ve şekilleri tespit etmek.
- **Özellikler:**  
  - YOLO tabanlı model ve OCR (optik karakter tanıma) ile çalışır.
  - Tespit edilen karakter ve şekilleri arayüze sinyal olarak iletir.
  - Hataları kendi içinde yakalar ve loglar.

#### e. EngagementModeService
- **Amaç:** Angajman modunda, farklı renk ve şekilleri tespit etmek.
- **Özellikler:**  
  - YOLO modeli ile 9 farklı renk-şekil kombinasyonunu tespit eder.
  - GPU desteği otomatik olarak algılanır ve kullanılır.
  - Sonuçlar arayüze sinyal olarak iletilir.

#### f. Diğer Servisler
- **MockService:** Test ve geliştirme amaçlı sahte veri üretir.
- **PanTiltService:** Kamera hareketini (pan/tilt) kontrol eder ve takip algoritmalarıyla entegre çalışır.

### 2. Kullanıcı Arayüzü (UI)

- **Ana Pencere (MainWindow):**  
  - Uygulamanın ana kontrol noktasıdır. Tüm servisleri başlatır, yönetir ve arayüzdeki bileşenleri koordine eder.
  - Tam ekran, animasyonlu kenar çubukları, tema desteği ve FPS göstergesi gibi modern özellikler içerir.
  - Kullanıcıdan gelen olayları (buton tıklamaları, acil durdurma, vs.) ilgili servislere yönlendirir.
  - Hataları ve önemli olayları loglar ve kullanıcıya bildirir.

- **LogSidebar:**  
  - Uygulama boyunca oluşan logları renkli ve biçimlendirilmiş şekilde gösterir.
  - Otomatik kaydırma ve temizleme özellikleri vardır.

- **CameraView:**  
  - Kamera görüntüsünü ve tespit sonuçlarını ekranda gösterir.
  - Acil durumlarda uyarı mesajları ve özel ekranlar gösterebilir.

### 3. Hata Yönetimi ve Loglama

- **Yerel Hata Yakalama:**  
  - Her servis, kendi içinde try/except blokları ile hata yakalar ve LoggerService ile loglar.
- **Global Exception Handler:**  
  - Uygulamanın en üst seviyesinde (main.py) bir global exception handler (`sys.excepthook`) tanımlanmıştır.
  - Beklenmeyen bir hata oluştuğunda, hata detayları log dosyasına kaydedilir ve kullanıcıya bir hata penceresiyle bildirilir.
  - Bu sayede uygulama çökse bile hata kaybolmaz ve kolayca tespit edilebilir.

### 4. Konfigürasyon ve Ortam Yönetimi

- **.env Dosyası:**  
  - Model ve veri dizinleri, hassas yollar ve diğer ayarlar .env dosyası ile yönetilir.
  - Ortam değişkenleri otomatik olarak yüklenir ve Config sınıfı üzerinden erişilir.
- **Kolay Kurulum:**  
  - setup_data_dir.py ile gerekli klasörler otomatik oluşturulur.
  - requirements.txt ile tüm bağımlılıklar kolayca yüklenir.

### 5. Geliştirici Dostu Yaklaşım

- **SOLID Prensipleri:**  
  - Kod yapısı, tek sorumluluk, bağımlılıkların azaltılması ve genişletilebilirlik gibi SOLID prensiplerine uygun olarak tasarlanmıştır.
- **Kolay Genişletilebilirlik:**  
  - Yeni bir servis veya özellik eklemek için sadece ilgili servisi yazmak ve ana pencereye entegre etmek yeterlidir.
- **Açık Kaynak ve Dokümantasyon:**  
  - Kodun büyük kısmı açıklamalı ve kolay anlaşılır şekilde yazılmıştır.
  - README ve .env.example dosyaları ile yeni geliştiriciler için rehberlik sağlanır.

---

Kısacası:
Bu proje, modern yazılım geliştirme prensipleriyle hazırlanmış, modüler, güvenilir ve kullanıcı dostu bir kamera uygulamasıdır. Hem gerçek zamanlı görüntü işleme hem de kullanıcı arayüzü açısından güçlü bir temel sunar. Geliştiriciler için ise, kolayca anlaşılabilir ve genişletilebilir bir altyapı sağlar.

---

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
