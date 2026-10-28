# RampaRandevu — Akıllı Depo Saha ve Rampa Yönetim Sistemi (YMS)
### Next-Gen Yard & Dock Appointment Management System

Türkiye lojistik merkezlerinde (Gebze, Hadımköy, Dilovası vb.) ambar ve fabrika kapılarındaki plansız tır yığılmasını, bekleme cezalarını (*demurrage*) ve rampa kaosunu ortadan kaldıran; **15 dakikalık kuantum dinamik slotlama**, **sıfır-indirme (Zero-App) şoför deneyimi**, **güneş modu destekli nizamiye tableti** ve [DocuLog](file:///root/LojistikGirisimleri/doculog) ile **yolda evrak ön-ayrıştırma** sağlayan kurumsal B2B saha yönetim platformu.

---

## 🚀 3 Temel Operasyonel Modül

1. **🖥️ Rampa Amiri Kokpiti (1440p / 4K Gantt Çizelgesi):**
   - 15 dakikalık kuantum dinamik slotlar üzerinde akan yatay rampa çizelgesi (Gantt Matrix).
   - Anlık kırmızı "Now Line" göstergesi.
   - Durum bazlı renk kodlaması: Planlı (Mavi), Tır Parkında (Sarı), Yanaşıyor (Mor), Rampada Boşaltılıyor (Yeşil), Tamamlandı (Gri).
   - **Tır Parkı (Buffer Yard) Çekmecesi:** Kapıdan giren araçları tek tıkla rampa seçerek şoförün cebine SMS/WhatsApp ile çağırma.
   - **DocuLog Mal Kabul Doğrulama:** Gemini 3.8 Flash Vision ile okunmuş irsaliye kalemlerini tek ekranda inceleme, sağlam/hasarlı ayrıştırma ve SAP 101/103 mal girişi mühürleme.

2. **🛡️ Nizamiye Kapı Tableti (Rugged Field Mode):**
   - Güneş altında okunabilir **2500+ Lux Yüksek Kontrast Modu**.
   - İş eldiveniyle basılabilir devasa **72px butonlar**.
   - Hızlı plaka tamamlama (34, 41, 06, 35) veya QR kod sorgulama.
   - Tek tıkla **"Aracı Saha Parkına Al (Gate-In)"** ve **"Bariyeri Aç (Gate-Out)"**.
   - **Denetimli Plaka Değişimi (Override with Audit):** Taşeron arızasında trafiği kilitlemeden fotoğraflı ve gerekçeli kontrollü kabul.

3. **📱 Şoför Mobil Web Ekranı (Zero-App / <100 KB):**
   - Şoföre mobil uygulama indirtmeden SMS/WhatsApp tek kullanımlık bağlantısıyla açılan ultra hafif arayüz.
   - 2-3 metre mesafeden (araç torpidosundan) okunabilen **72pt devasa tipografi** (`RAMPA 02` veya `SIRA: 2`).
   - Rampa hazır olduğunda tek elle basılan 80px yeşil `[RAMPAYA YANAŞTIM]` butonu.
   - Tesis içi 2D yönlendirme krokisi (Nizamiye -> Tır Parkı -> Rampa).
   - Tek tıkla çok dilli arayüz (TR / EN) ve WhatsApp hızlı aksiyon butonları (`[⏱️ 30 Dk Gecikiyorum]`, `[📍 Tır Navigasyonu]`).

---

## ⚡ Matematiksel Kuantum Slotlama Formülü

Sabit 30 dakikalık ezbere slotlama reddedilmiş, heyetimizce onaylanan dinamik kuantum modeli uygulanmıştır:
$$T_{slot} = T_{docking} + (N_{pallets} \times T_{handling}) + T_{inspection} + T_{buffer}$$

* $T_{docking}$ (Yanaşma ve körükleme): 10 dk
* $T_{handling}$ (Elleçleme hızı): Standart palet için 1.2 dk/palet; Dökme yük için 2.5 dk/palet
* $T_{inspection}$ (Kalite kontrol): Kuru yük için 5 dk; Soğuk zincir (frigo derece ölçümü) için 15 dk
* $T_{buffer}$ (Tolerans): 5 dk
* **Kuantum Yuvarlama:** Toplam süre 15'in bir sonraki katına yukarı yuvarlanır (Örn: 33 palet tır = 60 dk, 12 palet = 45 dk).

---

## 🔗 DocuLog & ERP Sinerjisi

| Bileşen | RampaRandevu Rolü | DocuLog & ERP Entegrasyonu |
| :--- | :--- | :--- |
| **Ön-Ayrıştırma** | Randevu anında irsaliye yüklenir | Gemini 3.8 Flash Vision ile araç yoldayken OCR + PO mutabakatı |
| **Rampa Boşaltma** | Amir fiili sayımı yapar | Sağ panelde DocuLog irsaliye satırları anında eşlenir |
| **Kısmi Mal Kabul** | Hasarlı koli/çuval tespiti | SAP `101 (Sağlam Giriş)` ve SAP `103 (Bloke Giriş)` ayrımı |
| **Mevzuat** | Sefer tamamlandığında çıkış | Ulaştırma Bakanlığı U-ETDS bildirim kapanışı |

---

## 🛠️ Hızlı Başlangıç ve Çalıştırma

### 1. Linux / macOS:
```bash
cd /root/LojistikGirisimleri/ramparandevu
./run_ramparandevu.sh
```

### 2. Windows:
`run_workstation.bat` dosyasına çift tıklayın.

### 3. Konsoldan Manuel Başlatma:
```bash
cd /root/LojistikGirisimleri/ramparandevu/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Tarayıcınızda açın:
* **Tek Ekran Full-Stack Arayüz:** [http://127.0.0.1:8080](http://127.0.0.1:8080)
* **API Swagger Dokümantasyonu:** [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
* **Canlı WebSocket:** `ws://127.0.0.1:8080/ws`

### 4. Testleri Çalıştırma:
```bash
cd /root/LojistikGirisimleri/ramparandevu/backend
PYTHONPATH=. pytest tests/
```
