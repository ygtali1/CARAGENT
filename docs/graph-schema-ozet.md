# Graph Şeması — Kısa Özet

Bu dosya [graph-schema.md](graph-schema.md) dokümanının sade bir özetidir. Ayrıntılar, Cypher sorguları ve test listesi ana dokümanda.

## Problem ne?

CARAGENT, 2024 Corolla LE kılavuzlarından (Lemon arşivi, yaklaşık 87 bin sayfa) soru cevaplıyor. Ama bugün graf bir bilginin **hangi araca ve hangi döneme ait olduğunu** bilmiyor.

Örnek: motor yağı kapasitesi
- 08/2023 öncesi üretilen araçta **4,6 L**
- 08/2023 sonrası üretilen araçta **4,2 L**

Bugünkü sistem bu iki değeri ayırt edemiyor. Başka sorunlar da var:
- Arşivdeki işçilik süreleri ve recall kayıtları aslında **Hybrid LE**'ye ait. Sistem bunları LE'ye aitmiş gibi gösterebiliyor.
- Bazı sayfalar yalnızca belirli bir donanım için geçerli. Örneğin bir tork tablosu "4 pistonlu kaliper hariç" diyor ve sistem bunu dikkate almıyor.
- Aynı veri tekrar yüklenince bazı kayıtlar çoğalıyor ya da eskimiş bilgi grafta kalıyor.

## Çözüm: üç katman

| Katman | Ne tutar | Örnek |
|---|---|---|
| **1. Kaynak ve kanıt** | Hangi sayfada hangi cümle yazıyor | "107 N·m" → `pages/10780.html`, birebir alıntı |
| **2. Kapsam** | O sayfa hangi araç, hangi dönem ve hangi donanım için geçerli | `[03/2023 - 08/2023]`, "4-pot kaliper hariç", "Hybrid LE sayfası" |
| **3. Bilgi (domain)** | Parça, değer, arıza kodu, belirti, uyarı, recall ve bunlar arasındaki ilişkiler | P0171 → olası neden → kontrol adımı |

**Temel kural:** Graftaki her bilginin bir kanıtı (sayfa + alıntı) olur. Bilginin hangi araç ve dönem için geçerli olduğu da o kanıttan okunur.

## Yeni eklenenler (kısaca)

- **Kanıt (Evidence):** Her bilginin alıntısı, sayfa numarası ve kaynak türü:
  - OM: kullanım kılavuzu
  - R&D: onarım ve teşhis
  - LT: işçilik süreleri
  - RC: recall
- **Üretim tarihi aralığı:** `[MM/YYYY - MM/YYYY]` etiketleri gerçek tarihe çevrilir.
- **Koşul:** Bir sayfanın hangi araçlar için geçerli olduğunu gösterir. Örnekler:
  - EPB'li olmak
  - 4 pistonlu kaliper (hariç)
  - TMC ya da TMMMS fabrikası
  - Hybrid hariç
- **Varyant:** Bizim aracımız (LE, 2.0 benzinli) ve arşivde geçen diğer varyant (Hybrid LE).
- **Yeni bilgi türleri:**
  - arıza kodu (DTC, ör. P0171)
  - işçilik operasyonu
- **Mevcut bilgi türlerine eklenen alanlar:**
  - Teknik değerin birimi ve koşulu (ör. "filtre değişimiyle")
  - Uyarının önemi (hemen dur / servise git / bilgi) ve kime hitap ettiği (sürücü / teknisyen)
  - Belirtinin sesi, ne zaman olduğu ve nereden geldiği (gıcırtı, fren yaparken, ön taraf)

## Sistem nasıl davranacak?

1. **Bilgi araca uyuyorsa** doğrudan cevap verilir.
2. **Bilgi araca uymuyorsa** (ör. başka motor, başka dönem) cevaptan çıkarılır.
3. **Uyup uymadığı bilinmiyorsa** (ör. kullanıcı üretim tarihini bilmiyor) bütün seçenekler etiketiyle gösterilir. Seçenekler farklı sonuç veriyorsa kullanıcıya **tek bir soru** sorulur: "Kapı direğindeki etikette üretim tarihi ne?"
4. **Recall sorularında** asla "aracınız etkilenir" ya da "etkilenmez" denmez. Her zaman VIN ile sorgulama önerilir.
5. **"Sürebilir miyim?" gibi sorularda** arşivde kullanım kılavuzu (OM) olmadığı açıkça söylenir. Teknisyen bilgisi sürücü talimatı gibi sunulmaz.

## Örnek sorular

| Soru | Sistem ne yapar? |
|---|---|
| "08/2023'ten önce üretildiyse yağ kapasitesi farklı mı?" (L01) | İki dönemin değerini kaynağıyla gösterir. 08/2023'ün iki dönemde de yer aldığını (sınır ayı) belirtir |
| "P0171 ne demek, neye bakmalıyım?" (N13) | Kodun anlamını ve olası nedenleri "kesin değil" diyerek sırayla verir |
| "Kaliper braket cıvatası kaç Nm?" (N19) | 107 N·m der ve "4 pistonlu kaliper hariç" notunu ekler. Gerekirse kaliper tipini sorar |
| "Açık recall var mı?" (N07) | Yerel kayıtların Hybrid LE'ye ait olduğunu söyler ve VIN ile sorgulamayı önerir |
| "Arabadan gıcırtı geliyor" (BL01 / C15) | Önce güvenlik kontrolü yapar. Sonra adım adım daraltır: fren yaparken mi → ön taraftan mı → ön fren |

## Python'da ne değişecek?

| Dosya | Özetle |
|---|---|
| `models.py` | Tarih aralığı, koşul, varyant ve kullanıcı profili modelleri; VIN'den fabrika ve model yılı çıkarımı |
| `entity_extractor.py` | Arıza kodu, işçilik ve birimlerin tanınması; bugün tanınmayan `N*m` ve `liters` birimleri; belirti tablosunun sırası |
| `graph.py` | Yeni düğümleri yazma, tekrar yüklemede çoğalmayı önleme, eski bilgiyi temizleme, kapsam filtresi |
| `ingest.py` | Yerel arşivi okuma; sayfa üstündeki konum yolundan (breadcrumb) tarih ve kaynak türü bilgisini alma |
| `rag.py` | Uyuyor / uymuyor / bilinmiyor kararı, tek netleştirme sorusu, recall ve OM kuralları |

## Nasıl test edilecek?

- **Doğru yapı:** Bilgi türleri doğru, ilişki yönleri doğru, zorunlu alanlar dolu.
- **Kanıt:** Her bilginin kanıtı var ve alıntı sayfada birebir geçiyor.
- **Filtreler:** Tarih, donanım ve varyant filtreleri doğru sonucu veriyor (ör. 2023-06 → 4,6 L, 2023-09 → 4,2 L).
- **Tekrar yükleme:** Aynı veri iki kez yüklenince hiçbir kayıt çoğalmıyor.
- **Örnek sorular:** Yukarıdaki sorular beklenen cevabı veriyor.

## Bilinen eksikler

- Arşivde **kullanım kılavuzu (OM) yok**. Sürücüye yönelik uyarılar için ayrıca eklenmesi gerekiyor.
- LE için işçilik ve recall kaydı yok; yalnızca Hybrid LE kayıtları var.
- Donanım koşullarının tam listesi arşiv taranarak kesinleştirilecek.
- Vektör/embedding araması bu tasarıma dahil değil.
