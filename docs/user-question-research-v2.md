# CAR-6 (v2): Kullanıcı soru tipleri araştırması, tamamlayıcı rapor

> **Kapsam:** Toyota Corolla 2024 (referans trim: ABD Corolla LE) için kullanıcı soru tipleri.
> **İlişki:** Bu rapor [CAR-6 v1 raporunu](user-question-research.md) ve
> [`corolla-2024-user-questions.json`](../data/examples/corolla-2024-user-questions.json) veri setini
> **değiştirmez**, tamamlar. v1'deki Q01–Q44 ve F01–F12 burada tekrar edilmez, yalnızca ID ile anılır.
> **Bu rapor şunları içermez:** kod, graph şeması ya da veri modeli. Bölüm 4, sonraki modelleme
> çalışmasına *gereksinim* olarak aktarılacak bir girdidir.
> **v2.1 güncellemesi (2026-11-17):** N01–N44 soruları, yerel Lemon arşivinin gerçek içeriğiyle tek tek
> karşılaştırıldı (§0B, §2.5–§2.7, §3.5). Teknik uygulama önerileri Ek A'da, sayım ve ölçüm yöntemi
> Ek B'dedir. Kod ölçümleri commit `bdd4d31` üzerinde yeniden yapıldı (§2.4).

## Özet

### v2.1: yerel Lemon arşivi incelemesinin sonucu

N01–N44, yerel Lemon arşivinin içeriğiyle soru soru karşılaştırıldı (§2.5):

| Durum | Sayı | Sorular |
|---|---:|---|
| ✅ Seçili araç için içerik bulundu | 5 | N13, N15, N19, N20, N30 |
| ◐ Seçili araç için içerik kısmen bulundu | 19 | Arşiv teknik veya servis tarafını veriyor; sürücü eylemi, aralık ya da sıra gibi bir parça eksik |
| ⇄ İçerik yalnızca başka varyantta bulundu | 3 | N07, N23, N24 (soru LE kapsamında, ama içerik *Corolla Hybrid LE* için) |
| ⊘ Soru seçili aracın kapsamı dışında | 4 | N05, N27, N34, N43 (hibrite özgü; arşivde ne bulunduğu §2.5'te ayrıca belirtildi) |
| ✖ İncelenen dosyalarda bulunamadı | 13 | Çoğu kullanım kılavuzu (Owner Manual) veya pazar dokümanı gerektiriyor |

Toplam: 44 soru.

**Arşiv neyi destekliyor, neyi desteklemiyor:**

- **Güçlü destek:** DTC teşhisi, tork ve limit değerleri, sıvı spesifikasyonu, servis ve öğrenme prosedürleri.
- **Destek yok:** "Sürmeli miyim?" gibi sürücü kararları, bakım aralıkları, pazar karşılaştırmaları.

**Kritik bulgular:**

1. **Labor Times ve recall/TSB kayıtları Corolla LE için yok.** Arşiv bu içerikler için *Corolla Hybrid LE,
   1.8L Eng VIN C* varyantına yönlendiriyor.
2. **Arşiv, Corolla platformunun ortak kılavuzu.** Tam ağaçtaki benzersiz içerik metinlerinin yaklaşık
   %56'sında motor, gövde veya tarih etiketi açısından 2024 LE ile *çelişki tespit edilmedi*. Sayfa bazında
   bu oran yaklaşık %52'dir. Bu, söz konusu içeriğin LE'ye uygun olduğunun doğrulandığı anlamına gelmez;
   oran yol metnine dayalı bir sezgisel sınıflamadır (yöntem ve varsayımlar Ek B'de).
3. **Model yılı tek başına yeterli olmayabilir.** Üretim tarihi, motor, pazar ve donanım koşulları da
   doğrulanmalıdır. Örnek: arşivde M20A-FKS yağ sınıfı 03/2023 üretiminden itibaren 0W-16'dan 0W-8'e geçiyor;
   filtreli yağ kapasitesi ise 08/2023 üretiminden itibaren 4,6 L'den 4,2 L'ye iniyor. Bu değişiklik, sahip
   forumlarındaki "4,4 mü 4,9 qt mi?" tartışması için *olası* bir açıklamadır. Forumdaki araçların üretim
   tarihleri doğrulanmadığı için kesin açıklama değildir.

### v2 özeti

v1 araştırması sahiplerin en sık sorduğu kullanım kılavuzu (Owner Manual) sorularını iyi kapsıyor.
Ancak projenin asıl veri kaynağı olan Lemon Manuals *Repair and Diagnosis* ve *Labor Times* içeriğini,
pazar farklarını ve çok turlu konuşmaları neredeyse hiç kapsamıyor. Bu rapor:

- **44 yeni bağımsız soru (N01–N44)** ve **14 çok turlu takip zinciri (C01–C14, toplam 44 tur,
  bunların 30'u takip turu)** ekler.
- Model, yıl, donanım ve pazara göre cevabı değişen soruları ⚑ ile işaretler.
- Her soruyu ve takip turunu mevcut `question_plan` / `retrieval_question` koduna verip sonucu
  raporlar. Ölçümler kod değiştirilmeden yapıldı (§2.4).
- Sonraki graph ve retrieval ekibi için varlık/ilişki gereksinimlerini listeler.

**En kritik üç bulgu:**

1. **P0 güvenlik soruları düşük öncelikle sınıflanıyor.** Örnekler: yanıp sönen check engine,
   hararet, yakıt sızıntısı, hava yastığı, ABS/VSC, direksiyon ağırlaşması ve "geri çağırma" kelimesi
   çekimli kullanıldığında recall sorusu. Mevcut sınıflayıcı bunlara P2 (bir örnekte P1) veriyor.
   Kategori önceliği P0 olan 31 sorudan 15'inde planner daha düşük öncelik veriyor; bunların 7'si doğrudan
   can güvenliği sorusu (commit `bdd4d31`, §2.4).
2. **Tetikleyici kelime yoksa takip sorusunun bağlamı korunmuyor.** Bağlamın korunması beklenen 24
   takip turundan:
   - 3'ünde bağlam doğru korundu;
   - 2'sinde kök soru yerine önceki çözülmemiş takip soruya bağlandı;
   - 19'unda bağlam hiç taşınmadı ("Kışın?", "Arka?", "Hibritte?" gibi).

   Konu değişimi beklenen 3 turun üçü de doğru biçimde bağlamsız işlendi (§2.4).
3. **`evidence_guard` yalnızca tek bir senaryoyu koruyor** (direksiyon + 24V878000). Üstelik recall
   sorusu P2'ye düştüğünde bu guard da devreye girmiyor (zincir C08).

## Yöntem ve sınırlar

| Girdi | Ne için kullanıldı |
|---|---|
| v1 raporu, JSON veri seti, `tests/test_question_research.py` | Mevcut kapsamı belirlemek ve tekrarı önlemek |
| `caragent/models.py` (`QUESTION_TAXONOMY`, `QUESTION_SYSTEMS`, `QUESTION_INTENT_HINTS`, `COMPONENTS`) | Kategori ve öncelik referansı; sınıflayıcı ölçümü |
| `caragent/rag.py` (`question_plan`, `retrieval_question`, `_guarded_safety_answer`, `_source_context`) | Takip sorusu ve güvenlik guard davranışı |
| `caragent/entity_extractor.py`, `docs/graph.md` | Mevcut entity ve ilişki türleriyle çapraz referans |
| `caragent/ingest.py`, `docs/architecture.md`, `docs/project-guide.md` | Lemon kaynak yapısı, pazar belirsizliği |
| Toyota Owner Manual yapısı, NHTSA kayıtları | Gerçek senaryo türlerini çıkarmak |
| **v2.1:** Yerel Lemon arşivi (`data/external/lemon-corolla-2024/`, kullanıcının indirdiği çevrimdışı kopya) | Soruların kaynak dayanağı (§0B, §2.5) |
| **v2.1:** Erişilebilir kullanıcı kaynakları (forumlar, şikâyet siteleri, NHTSA) | Gerçek kullanıcı ihtiyacı sinyali (§2.6) |

**Sınırlar:**

- **v2'de** Lemon içeriğine erişilemediği için kaynak sütunları (R&D, LT) tasarım varsayımıydı. **v2.1'de**
  kaynak durumu yerel arşivin içeriğine göre belirlendi. Bölüm başlığı veya dosya adı tek başına kanıt
  sayılmadı; ilgili sayfaların metni okundu.
- **Örnekleme:** Arşivde 87.544 sayfa var ve hepsi tek tek okunmadı. Önce dizinler ve bağlantılar haritalandı.
  Ardından her soru için 2024 üretim aralığına uyan temsilî sayfalar okundu. Bu nedenle:
  - "İncelenen dosyalarda bulunamadı" ifadesi "kılavuzda yok" anlamına **gelmez**.
  - Görseldeki bilgi, görsel incelenmeden doğrulanmış sayılmadı.
- **Özgün URL'ler:** Sayfalarda özgün Lemon URL'si yok. Alt sayfa URL'leri tahminle üretilmedi; atıflar yerel
  dosya yolu ve bölüm yoluyla verildi.
- **Sıklık kanıtı:** Yerel kılavuz bir sorunun *cevaplanabilir* olduğunu destekler, *sık sorulduğunu*
  kanıtlamaz. Kullanıcı ihtiyacı ayrı kaynaklarla değerlendirildi (§2.6).
- **Teknik değerler:** N ve L soruları cevap içermez. §2.5'teki teknik değerler yerel arşivden yapılan
  alıntılardır ve yalnızca kaynak dayanağını göstermek içindir. Bunlar gerçek bir araç için bakım veya onarım
  tavsiyesi değildir; araç bazında üretim tarihi, motor, pazar ve donanım doğrulanmadan uygulanmamalıdır.
- **Tekrar üretilebilirlik:** Arşiv sayımları ve kod ölçümleri Ek B'deki yöntemle yeniden üretilmiştir.
  Kullanılan betikler bu görevin kapsamı gereği repoya eklenmedi; yöntem, sayıların yeniden elde
  edilebileceği ayrıntıda tarif edildi.
- Pazar tablosundaki (§2.3) ayrımlar **soru tasarımı içindir**. Kesin teknik bilgi değildir; cevap
  aşamasında pazar kılavuzu ve VIN ile doğrulanmalıdır.
- Öncelik ve sıklık nitel değerlendirmedir; arama hacmi verisine dayanmaz (v1 ile aynı sınır).

## 0. Mevcut durum ve boşluklar

| # | Alan | Mevcut durum | Boşluk |
|---|---|---|---|
| G1 | Kaynak türü | Q01–Q44 ağırlıklı olarak Owner Manual ve sahiplik soruları | Lemon'un asıl içeriği olan DTC teşhisi, tork ve kapasite, sökme-takma, işçilik süresi soruları yok |
| G2 | Pazar | JSON `market`: sabit "North America"; `project-guide.md` Lemon pazarının belirsiz olduğunu belirtiyor | US, Canada ve EU/TR arasındaki birim, yakıt, motor, regülasyon ve recall kanalı farkları soru düzeyinde yok |
| G3 | Takip soruları | F01–F12 tek turlu ve hepsi bağlamı koruyan türden; çözümleme regex tetikleyiciye (peki/bunu/onu/aynı…) veya `components()` eşleşmesine bağlı | Eliptik takip, konu değişimi, geri dönüş, varyant netleştirme ve yıl değişimi senaryoları tanımsız |
| G4 | Güvenlik guard'ı | `_guarded_safety_answer` yalnızca `P0` + `steering` + "24v878000" metni olduğunda çalışıyor | SRS, fren, yağ basıncı, hararet, yakıt sızıntısı ve hibrit sistem için çıkarımsal (extractive) guard yok |
| G5 | Varyant izolasyonu | Retrieval `vehicle_id` ile sınırlı; varyant uyumsuzluğu yalnızca "different variant/trim than selected" kalıbıyla yakalanıyor | Kullanıcının konuşmada verdiği pazar/motor bilgisi saklanmıyor; başka yıl sorusu seçili araç dışına çıkamıyor |
| G6 | Taksonomi tutarlılığı | JSON'da ~35 ince intent, kodda 6 route intent var; JSON system adları (`tires`, `tpms`, `drcc`) ile `QUESTION_SYSTEMS` adları (`tires_tpms`, `driver_assistance`) farklı; Q03 bakım kategorisinde ama P1 | İnce intent → route intent eşleme tablosu ve ortak sistem sözlüğü yok |
| G7 | Türkçe çekim | Alias eşleşmesi sınırlı bir ek listesiyle yapılıyor | "ışığı", "uyarıları", "geri çağırması", "ağırlaşırsa", "torku" gibi biçimler kaçıyor (§2.4) |

Not: v1'deki F02 ("Kaç litre gerekiyor ve filtre de aynı anda değişmeli mi?") tetikleyici kelime
içermiyor gibi görünse de "aynı" kelimesi sayesinde doğru çözülüyor. Ölçümle doğrulandı.

## 0B. Yerel Lemon arşivi envanteri (v2.1)

**Kaynak:** kullanıcının Lemon'dan indirip açtığı çevrimdışı arşiv. Klasör Git'e eklenmez ve yalnızca
`.git/info/exclude` ile hariç tutulur. Bu raporda `pages/N.html` biçimindeki yollar şu klasöre görelidir:
`data/external/lemon-corolla-2024/2024 Toyota Corolla LE/`

| Öğe | Bulgu |
|---|---|
| Dosyalar | 103.661 dosya; 87.548 HTML dosyasının 87.544'ü `pages/` altında. Dağılım: 87.544 HTML sayfa (`pages/`); 16.096 görsel (`images/`: 15.712 PNG, 220 SVG, 96 GIF, 68 JPEG); 14 SVG ikon; 7 kök dosya (`index.html`, `README.txt`, `about.html`, `404.html`, `external-car.html`, `script.js`, `style.css`). **PDF yok.** |
| Giriş sayfaları | `index.html` ve `pages/1.html` ("Toyota: 2024: Corolla LE", "retrieved in 2025"). Bağlantılar: `pages/2.html` (Repair and Diagnosis, bölünmüş ağaç), `pages/3.html` (tüm bağlantılar tek sayfada), `pages/4.html` (Labor Times). Zip indirme bağlantısı yerelde `404.html`'e gider. |
| Araç ve varyant beyanı | Giriş sayfası, kılavuzun *Corolla Nightshade, SE ve XSE 4D Sedan* ile aynı olduğunu söyler; "Labor Times", "Fluids" ve "Tire Fitment" sayfaları hariç olabilir. Motor: M20A-FKS, 2.0 L benzinli (`pages/467.html`). |
| Ağaç yapısı ve tekrarlar | Tam ağaçta (`pages/3.html`) 34.609 sayfa bağlantısı var. Bunlar 22.585 içerik, 8.765 dizin ve 3.259 kısa (≤200 karakter) sayfa olarak sınıflandı. Bölünmüş ağaç (`pages/2.html`) ve iç bağlantılar aynı metinlerin ikinci kopyasını içerir. Metin karması (hash) ile tekilleştirildiğinde: 87.544 sayfada 24.579 benzersiz gövde metni var; içerik sayfalarında 11.962 benzersiz metin var, bunların 11.847'si tam ağaçta. Tam ağaç dışındaki içerik metinlerinden yalnızca 115'i tam ağaçta yoktur. Aynı metin, iki ağaçta ve **farklı üretim tarihi aralıklarında** tekrar ettiği için içerik sayfası sayısı (22.585) benzersiz metin sayısının (11.847) yaklaşık iki katıdır. Yöntem Ek B'dedir. |
| Bölüm dağılımı (tam ağaç) | Engine Performance 12.364 · Accessories & Equipment 7.192 · Body & Frame 2.689 · Brakes 2.207 · General Information 1.648 · Restraints 1.557 · Engine Mechanical 1.197 · Transmission 986 · Suspension 973 · Electrical 910 · Maintenance 877 · HVAC 691 · Steering 480 · Drivelines & Axles 450 · Quick Lookups 206 · Hybrid/Electric Powertrain 181 |
| Repair and Diagnosis konumu | *Quick Lookups*: Common Specs (`pages/467.html`), DTC Index (`pages/468.html` ile başlar), Fluids (`pages/625.html`), Technical Bulletins (`pages/626–628.html`), Tire Fitment (`pages/629.html`). Teknik değerler: *Maintenance › Service Data / Torque Specifications*, üretim tarihi aralıklarına bölünmüş. |
| **Labor Times** | `pages/4.html`: "Labor times are only available for a different vehicle variant." İşçilik süreleri yalnızca *Corolla Hybrid LE, 1.8L Eng VIN C* için var (`pages/5.html` ağacı, 461 sayfa, her biri "different variant/trim" uyarılı). **Corolla LE için işçilik süresi yok.** |
| **Recall / Campaign / TSB** | `pages/626–628.html`: üçü de yalnızca *Corolla Hybrid LE, 1.8L Eng VIN C* için. Recall listesi (`pages/72986.html`): 24V548000 (Labels) ve 24V878000 (Steering). **Corolla LE için yerel recall kaydı yok.** |
| Başka varyanta ait içerik | 16.358 sayfa Lemon'un "different variant/trim than selected" uyarı kutusunu taşır (iki ağaçta 8.179'ar). Buna 462 hibrit Labor sayfası eklenir. Ayrıca `external-car.html`'e giden bağlantılar var (sayfa gövdesinde dize sayımıyla 6.700 sayfada toplam 46.744 bağlantı); bu sayfanın kendi metnine göre bunlar başka araca ait olduğu için arşive alınmamış içeriktir. |
| Ortak platform kılavuzu | Tam ağaç; motor ve gövde dışında, 2019–2025 üretim aralıklarını, hibrit (2ZR-FXE), GR Corolla (G16E-GTS), 2ZR-FAE ve hatchback içeriğini birlikte taşır. Yol metnine dayalı sezgisel sınıflama (Ek B): **benzersiz metin bazında** 11.847 metnin 6.626'sında (%55,9) 2024 LE ile motor, gövde veya tarih etiketi *çelişkisi tespit edilmedi*; 4.301'i yalnızca 2023'ten önce biten aralıklarda, 872'si başka motor veya gövdede, 48'i 2024'ü kapsamayan yıl etiketinde görünüyor. **Sayfa bazında** 22.585 içerik sayfasının 11.656'sında (%51,6) çelişki tespit edilmedi. "Çelişki tespit edilmedi", içeriğin LE'ye uygun olduğunun doğrulandığı anlamına **gelmez**. Ayrıca fabrika (TMC / TMMMS) ve donanım (EPB'li/EPB'siz, ekran tipi, "Type B" TPMS) ayrımları bu sınıflamaya dahil edilmedi. |
| Üretim tarihi | Bazı değerler üretim tarihi aralığına göre değişir. M20A-FKS yağ sınıfı 03/2023 aralığından itibaren 0W-16'dan 0W-8'e geçer (`pages/30721.html` → `pages/30740.html`). Filtreli yağ kapasitesi 08/2023 aralığından itibaren 4,6 L / 4,9 US qt'den 4,2 L / 4,4 US qt'ye iner (`pages/30742.html` → `pages/30761.html`). Bir aracın hangi aralığa girdiği, üretim tarihi doğrulanmadan belirlenemez. |
| Görseller | `images/` klasöründe 16.096 görsel var; sayfa başına görsel dağılımı bu raporda kullanılmadı. İncelenen örneklerde (TPMS kayıt sayfası `pages/34061.html`) görseller parça veya etiket konumunu gösteriyor; adımlar ve lejantlar metinde. Görselde kalan bilgi doğrulanmış sayılmadı. |
| Pazar | Arşivin README'si kapsamı "Almost all US & Canada" diye tanımlar. Birimler US ve metrik birlikte verilir. Bazı sayfalar Meksika'ya özeldir (`pages/30760.html`, farklı yağ sınıfları). İncelenen dosyalarda EU/TR'ye özgü içerik bulunamadı. |
| Özgün URL | Sayfalarda özgün Lemon URL'si veya canonical bağlantı yok; breadcrumb'lar yereldir. Proje crawler'ında tanımlı tek adres araç köküdür (`https://lemon-manuals.la/Toyota/2024/Corolla%20LE/`). |

---

## 1. Soru kategorileri

### 1.1 Ana kategoriler (değişmedi)

Sistem tutarlılığı için `QUESTION_TAXONOMY` içindeki 9 kategori ve öncelikleri **aynen korunur**:

| Kategori ID | Başlık | Öncelik |
|---|---|---|
| `maintenance` | Bakım ve sıvılar | P0 |
| `warnings` | Uyarılar ve arıza belirtileri | P0 |
| `safety_recalls` | Güvenlik ve geri çağırmalar | P0 |
| `tires_brakes` | Lastikler ve frenler | P0 |
| `driver_assistance` | Sürüş desteği | P1 |
| `multimedia` | Multimedya ve telefon | P1 |
| `keys_remote` | Anahtar ve uzaktan erişim | P1 |
| `efficiency_drivetrain` | Yakıt ekonomisi ve aktarma | P1 |
| `ownership` | Donanım ve genel kullanım | P2 |

### 1.2 Üç eksenli sınıflama

Bir soru tek bir etiketle yeterince anlatılamaz. Önerilen sınıflama üç bağımsız eksenden oluşur.
Mevcut kod bu eksenleri kısmen zaten taşıyor: kategori, `intent` ve `systems`.

| Eksen | Değerler | Kodda karşılığı |
|---|---|---|
| **Konu** (ne hakkında) | Yukarıdaki 9 kategori | `categories` |
| **Kullanım amacı** (ne istiyor) | `triage` (sürmeli miyim?), `diagnosis` (neden?), `specification` (değer/kapasite), `procedure` (nasıl yapılır), `interval` (ne zaman), `availability` (bende var mı?), `comparison` (varyant/pazar farkı), `labor_cost` (süre/maliyet), `recall_lookup` | `intent`: 6 route değeri (eşleme §4.4'te) |
| **Araç sistemi** (nerede) | `engine`, `lubrication`, `cooling`, `fuel`, `transmission`, `hybrid_system`, `charging`, `brakes`, `tires_tpms`, `steering`, `srs`, `driver_assistance`, `multimedia`, `keys_remote`, `body` | `systems`; `hybrid_system`, `fuel` ve `body` henüz yok |

### 1.3 Yeni alt kategoriler (ana kategorilere bağlı)

Yeni ana kategori açılmaz. Lemon ve pazar kaynaklı soru tipleri mevcut kategorilerin altına
**alt kategori** olarak eklenir:

| Alt kategori | Bağlı ana kategori | Kaynak türü | Örnek ID |
|---|---|---|---|
| Arıza kodu (DTC) teşhisi | `warnings` | Repair & Diagnosis | N13, N14 |
| Teknik değerler (tork, kapasite, limit) | `maintenance` / `tires_brakes` | Repair & Diagnosis | N15, N18–N20, N22 |
| Servis ve öğrenme prosedürleri | `maintenance` | Repair & Diagnosis | N25, N30 |
| İşçilik süresi (Labor Times) | Parçanın ana kategorisi | Labor Times | N23, N24 |
| Kritik uyarı triyajı | `warnings` / `safety_recalls` | Owner Manual | N01–N06, N09, N11 |
| Pazar ve varyant karşılaştırması | Konunun ana kategorisi | Owner Manual (çok pazar) | N31–N36 |

---

## 2. Örnek soru listesi

**Gösterimler:**

- **Kaynak:** OM = Owner Manual, R&D = Repair and Diagnosis, LT = Labor Times, RC = recall/kampanya kaydı.
- **⚑ (cevap değişkenliği):** M = model/güç aktarma (benzinli/hibrit, motor), Y = model yılı,
  D = donanım/paket/varyant, P = pazar (US/Canada vs EU/TR).
- **Planner:** Mevcut `question_plan` çıktısındaki öncelik. ✓ beklenen öncelikle aynı; ✗ daha düşük
  öncelik verdi; ↑ beklenenden yüksek verdi. Beklenen öncelik, kategorinin taksonomideki önceliğidir.

> **v2.1 notu:** Aşağıdaki "Kaynak" sütunu v2'deki *beklenen* kaynak türüdür. Gerçek kaynak durumu, yerel
> arşivle yapılan karşılaştırmaya göre §2.5'tedir. Araştırmanın önerdiği öncelik ise §3.5'tedir.

### 2.1 Bağımsız sorular (N01–N44)

#### A. Kritik uyarı ve acil durum triyajı

| ID | Soru | Kategori | Amaç | Sistem | Kaynak | ⚑ | Öncelik | Planner |
|---|---|---|---|---|---|---|---|---|
| N01 | Check engine ışığı yanıp sönüyorsa aracı hemen durdurmalı mıyım? | warnings | triage | engine | OM | — | P0 | P2 ✗ |
| N02 | Motor hararet göstergesi kırmızıya çıkarsa ne yapmalıyım? | warnings | triage | cooling | OM | M | P0 | P2 ✗ |
| N03 | Yağ basıncı uyarı ışığı yanarsa motoru kapatmalı mıyım? | warnings | triage | lubrication | OM | — | P0 | P0 ✓ |
| N04 | Fren uyarı ışığı yanıyor ve pedal boşa gidiyorsa araç kullanılabilir mi? | tires_brakes | triage | brakes | OM | — | P0 | P0 ✓ |
| N05 | Hibrit sistem uyarısı (Check Hybrid System) çıkarsa ne yapmalıyım? | warnings | triage | hybrid_system | OM | M | P0 | P0 ✓ |
| N06 | Yakıt kokusu alıyorsam ya da aracın altında sızıntı görürsem ne yapmalıyım? | warnings | triage | fuel | OM | — | P0 | P1 ✗ |
| N09 | ABS ve VSC uyarıları aynı anda yanarsa ne yapmalıyım? | warnings | triage | brakes | OM | — | P0 | P2 ✗ |
| N11 | Elektrikli direksiyon (EPS) aniden ağırlaşırsa güvenli şekilde nasıl durmalıyım? | safety_recalls | triage | steering | OM, RC | Y | P0 | P2 ✗ |
| N12 | Çarpışma öncesi sistem (PCS) gereksiz yere fren yaparsa ne yapmalıyım? | driver_assistance | triage | driver_assistance | OM | D, P | P1 | P0 ↑ |

#### B. Güvenlik ve geri çağırma

| ID | Soru | Kategori | Amaç | Sistem | Kaynak | ⚑ | Öncelik | Planner |
|---|---|---|---|---|---|---|---|---|
| N07 | 2024 Corolla için açık bir geri çağırma var mı ve Türkiye'de nasıl sorgulanır? | safety_recalls | recall_lookup | — | RC | Y, P | P0 | P2 ✗ |
| N08 | Yolcu hava yastığı kapalı (OFF) göstergesi yetişkin otururken yanıyorsa ne anlama gelir? | safety_recalls | diagnosis | srs | OM | D, P | P0 | P2 ✗ |
| N38 | eCall acil çağrı düğmesi ne işe yarar ve hangi pazarlarda bulunur? | safety_recalls | availability | body | OM | P | P0 | P2 ✗ |

#### C. Arıza kodu (DTC) ve teşhis (Repair & Diagnosis)

| ID | Soru | Kategori | Amaç | Sistem | Kaynak | ⚑ | Öncelik | Planner |
|---|---|---|---|---|---|---|---|---|
| N13 | P0171 arıza kodu ne anlama gelir ve hangi parçalar kontrol edilmelidir? | warnings | diagnosis | engine | R&D | M | P0 | P0 ✓ |
| N14 | P0420 katalizör verim koduyla araç kullanmak motora zarar verir mi? | warnings | triage | engine | R&D | M, P | P0 | P2 ✗ |

#### D. Teknik değerler: tork, kapasite, limit (Repair & Diagnosis)

| ID | Soru | Kategori | Amaç | Sistem | Kaynak | ⚑ | Öncelik | Planner |
|---|---|---|---|---|---|---|---|---|
| N10 | Fren hidroliği seviyesi MIN çizgisinin altındaysa yalnızca ekleme yapmak yeterli mi? | maintenance | diagnosis | brakes | OM, R&D | — | P0 | P0 ✓ |
| N15 | Motor yağı kapasitesi filtre değişimi dahil kaç litredir? | maintenance | specification | lubrication | OM, R&D | M, P | P0 | P0 ✓ |
| N16 | CVT şanzıman yağı kontrol prosedürü ve doğru sıcaklık aralığı nedir? | maintenance | procedure | transmission | R&D | M | P0 | P0 ✓ |
| N17 | Motor soğutma sıvısı hangi tipte olmalı ve ilk değişim kaç km'de yapılır? | maintenance | interval | cooling | OM | M, P | P0 | P0 ✓ |
| N18 | Bijon somunu sıkma torku kaç Nm'dir ve hangi sırayla sıkılır? | tires_brakes | specification | tires_tpms | OM, R&D | D | P0 | P2 ✗ |
| N19 | Fren kaliper braket cıvataları kaç Nm ile sıkılmalıdır? | tires_brakes | specification | brakes | R&D | M | P0 | P0 ✓ |
| N20 | Ön fren diskinin minimum kalınlık değeri nedir? | tires_brakes | specification | brakes | R&D | M, D | P0 | P0 ✓ |
| N21 | Buji değişim aralığı ve sıkma torku nedir? | maintenance | specification | engine | OM, R&D | M | P0 | P2 ✗ |
| N22 | Yağ boşaltma tapasının sıkma torku nedir ve conta değişimi gerekli mi? | maintenance | specification | lubrication | R&D | M | P0 | P0 ✓ |

#### E. Servis ve öğrenme prosedürleri

| ID | Soru | Kategori | Amaç | Sistem | Kaynak | ⚑ | Öncelik | Planner |
|---|---|---|---|---|---|---|---|---|
| N25 | Akü değişiminden sonra hangi sistemler yeniden öğretilmeli veya sıfırlanmalı? | maintenance | procedure | charging | R&D | M, D | P0 | P2 ✗ |
| N26 | 12V akü bittiğinde takviye kabloları hangi sırayla bağlanır? | ownership | procedure | charging | OM | M | P2 | P2 ✓ |
| N27 | Hibrit Corolla'da 12V akü nerede bulunur ve takviye noktası neresidir? | ownership | availability | charging | OM | M | P2 | P2 ✓ |
| N28 | Lastik değiştirildikten sonra TPMS sensör kimlikleri yeniden kaydedilmeli mi? | tires_brakes | procedure | tires_tpms | OM, R&D | D, P | P0 | P0 ✓ |
| N29 | Kabin hava filtresi nasıl değiştirilir? | maintenance | procedure | body | OM | — | P0 | P2 ✗ |
| N30 | Gaz kelebeği temizliğinden sonra rölanti öğrenme prosedürü nedir? | maintenance | procedure | engine | R&D | M | P0 | P2 ✗ |

#### F. İşçilik süresi (Labor Times)

| ID | Soru | Kategori | Amaç | Sistem | Kaynak | ⚑ | Öncelik | Planner |
|---|---|---|---|---|---|---|---|---|
| N23 | Ön fren balatası değişimi için standart işçilik süresi kaç saattir? | tires_brakes | labor_cost | brakes | LT | M | P0 | P0 ✓ |
| N24 | Su pompası değişimi kaç saat işçilik gerektirir? | maintenance | labor_cost | cooling | LT | M | P0 | P2 ✗ |

#### G. Model, yıl ve pazar karşılaştırması

| ID | Soru | Kategori | Amaç | Sistem | Kaynak | ⚑ | Öncelik | Planner |
|---|---|---|---|---|---|---|---|---|
| N31 | Türkiye'deki 1.5 benzinli Corolla ile ABD'deki 2.0 LE aynı bakım planını mı kullanır? | maintenance | comparison | engine | OM (çok pazar) | M, P | P0 | P0 ✓ |
| N32 | Avrupa'da 95 oktan, ABD'de 87 oktan önerilmesi aynı yakıt anlamına mı gelir? | efficiency_drivetrain | comparison | fuel | OM (çok pazar) | P | P1 | P1 ✓ |
| N33 | 2023 ile 2024 Corolla arasında multimedya sisteminde fark var mı? | multimedia | comparison | multimedia | OM (çok yıl) | Y, D | P1 | P2 ✗ |
| N34 | AWD hibrit Corolla LE'de bakım kalemleri önden çekişliden farklı mı? | maintenance | comparison | transmission | OM | M, D | P0 | P0 ✓ |
| N35 | Kanada'da satılan Corolla'nın kılavuzundaki km ve kPa değerleri ABD kılavuzuyla aynı mı? | ownership | comparison | — | OM (çok pazar) | P | P2 | P2 ✓ |
| N36 | Hız sınırı uyarısı (ISA) Avrupa'daki Corolla'da neden sürekli bip sesi çıkarıyor? | driver_assistance | diagnosis | driver_assistance | OM | P, Y | P1 | P0 ↑ |

#### H. Genel kullanım, konfor ve donanım

| ID | Soru | Kategori | Amaç | Sistem | Kaynak | ⚑ | Öncelik | Planner |
|---|---|---|---|---|---|---|---|---|
| N37 | Toyota uygulamasıyla klima uzaktan açılabilir mi? | keys_remote | availability | keys_remote | OM | D, P | P1 | P1 ✓ |
| N39 | Ön cam silecek lastiği nasıl değiştirilir ve hangi ölçü kullanılır? | ownership | procedure | body | OM | Y | P2 | P2 ✓ |
| N40 | Gösterge panelinde yakıt tüketimi birimi L/100 km olarak nasıl değiştirilir? | ownership | procedure | multimedia | OM | P, D | P2 | P1 ↑ |
| N41 | Bagaj kapağı dışarıdan açılmazsa içeriden acil açma kolu var mı? | ownership | availability | body | OM | P | P2 | P2 ✓ |
| N42 | Kış lastiği takarken hangi jant ve lastik ölçüsü seçenekleri uygundur? | tires_brakes | specification | tires_tpms | OM | D, P | P0 | P0 ✓ |
| N43 | Hibrit modelde EV modu ne zaman devreye girer? | efficiency_drivetrain | procedure | hybrid_system | OM | M | P1 | P2 ✗ |
| N44 | Koltuk ısıtma veya direksiyon ısıtma LE donanımında var mı? | ownership | availability | body | OM | D, P | P2 | P2 ✓ |

**Dağılım:** 44 soru; 31 P0, 6 P1, 7 P2. Bunların 37'si ⚑ işaretli, yani cevabı varyanta bağlı.
P0 ağırlığı bilinçlidir: v1 kapsamı P1/P2 kullanım sorularında zaten güçlü.

### 2.2 Takip soruları: çok turlu zincirler (C01–C14)

**Zincir türleri:**

- **BK:** bağlam koruma.
- **EL:** tetikleyici kelimesi olmayan eliptik takip ("Kışın?").
- **KD:** konu değişimi.
- **GD:** önceki konuya geri dönüş.
- **VN:** kullanıcının varyant/pazar bilgisini sonradan vermesi.
- **YD:** yıl veya model değişimi.
- **P0↑:** normal sorudan güvenlik sorusuna yükselme.

**"Mevcut" sütunu:** her turun mevcut `retrieval_question` / `question_plan` çıktısı.
**⟲** önceki soruyla birleştirildi, **∅** bağlamsız arandı; öncelik planner çıktısıdır.

| Zincir | Tür | Tur | Kullanıcı mesajı | Beklenen davranış | Mevcut |
|---|---|---|---|---|---|
| **C01** | EL, BK | 1 | 2024 Corolla LE motor yağı kapasitesi filtre dahil kaç litre? | maintenance / specification, P0 | ∅ P0 ✓ |
| | | 2 | Filtreyi değiştirmezsem? | Motor yağı bağlamını koru; kapasite farkını sor | ∅ P2 ✗ |
| | | 3 | Boşaltma tapası kaç Nm ile sıkılmalı? | Aynı motor/varyant, R&D tork değeri | ∅ P2 ✗ |
| **C02** | EL, zincir kırılması | 1 | Lastik basıncı soğukken kaç PSI olmalı? | tires / specification, P0 | ∅ P0 ✓ |
| | | 2 | Kışın? | Kök soruya bağlan: kış koşulunda basınç | ∅ P2 ✗ |
| | | 3 | Peki stepnede de aynı değer mi? | Kök soruya (lastik basıncı) bağlan; stepne donanımı ⚑D | ⟲ "Kışın?" sorusuna bağlandı, kök kayboldu ✗ |
| **C03** | EL, LT | 1 | Fren balatası değişimi için işçilik süresi ne kadar? | brakes / labor_cost | ∅ P0 (intent: general_information) |
| | | 2 | Ne kadar? | Kök soruya bağlan | ⟲ P0 ✓ |
| | | 3 | Ön ve arka için ayrı mı? | Kök soruya bağlan; ön/arka işçilik ayrımı | ∅ P2 ✗ |
| **C04** | BK, P0↑ | 1 | P0171 arıza kodu ne anlama geliyor? | warnings / diagnosis, P0 | ∅ P0 ✓ |
| | | 2 | Bunu nasıl kontrol ederim? | DTC bağlamında R&D teşhis adımları | ⟲ P0 ✓ |
| | | 3 | Check engine ışığı yanıp sönüyor, sürebilir miyim? | P0 triage; P0171 bağlamı korunmalı, sürüş kararı öne alınmalı | ∅ P2 ✗ |
| **C05** | KD, GD | 1 | CarPlay nasıl bağlanır? | multimedia / procedure, P1 | ∅ P1 ✓ |
| | | 2 | Tamam. Bu arada yağ değişimi kaç km'de bir? | Konu değişimi: CarPlay bağlamı **taşınmamalı** | ∅ P0 ✓ (doğru davranış) |
| | | 3 | Telefonum yine de bağlanmazsa? | CarPlay konusuna geri dön | ∅ P2, kategori yok ✗ |
| **C06** | VN | 1 | Uzaktan çalıştırma bende var mı? | availability; varyant netleştirme sorusu sorulmalı | ∅ P1 ✓ |
| | | 2 | Aracım Türkiye'de satılmış 1.5 benzinli. | Pazar = TR, motor = 1.5 bilgisi konuşma durumuna yazılmalı | ∅ (bilgi saklanmıyor) ✗ |
| | | 3 | O zaman uygulamadan klimayı açabilir miyim? | TR pazarı uygulama kapsamıyla cevapla | ∅ P2 ✗ |
| **C07** | YD, EL | 1 | 2024 Corolla bakım aralığı nedir? | maintenance / interval, P0 | ∅ P0 ✓ |
| | | 2 | 2020 modelde de aynı mı? | Seçili araç (2024) dışı yıl: araç değiştirme veya netleştirme önerilmeli | ⟲ P0, ancak arama 2024 `vehicle_id` ile sınırlı ✗ |
| | | 3 | Hibritte? | Bakım aralığı + hibrit varyantı ⚑M | ∅ P2 ✗ |
| **C08** | BK, P0↑, RC | 1 | Direksiyondan tık sesi geliyor. | warnings / steering, P0 | ∅ P0 ✓ |
| | | 2 | Sadece park ederken oluyor. | Belirti bağlamını koru | ∅ P2 ✗ |
| | | 3 | Direksiyon geri çağırması bununla ilgili olabilir mi? | safety_recalls, P0; evidence_guard tetiklenmeli | ∅ P2; guard P0 şartı yüzünden **çalışmaz** ✗ |
| | | 4 | VIN'imi nereden bulurum? | Recall bağlamında VIN konumu | ∅ P2 ✗ |
| **C09** | EL, P0↑ | 1 | Soğutma sıvısı seviyesi ne sıklıkla kontrol edilmeli? | maintenance / interval, P0 | ∅ P0 ✓ |
| | | 2 | Hangi tip kullanılmalı? | Soğutma sıvısı tipi; motor ⚑M | ∅ P2 ✗ |
| | | 3 | Göstergede sıcaklık kırmızıya çıktı, ne yapmalıyım? | P0 hararet triyajı | ∅ P2 ✗ |
| **C10** | KD, EL, GD | 1 | Motor yağı hangi viskozitede olmalı? | maintenance / specification, P0 | ∅ P0 ✓ |
| | | 2 | Silecek lastiği nasıl değiştirilir? | Konu değişimi | ∅ P2 ✓ |
| | | 3 | Arka? | Silecek bağlamı; sedanda arka silecek yok ⚑D | ∅ P2 ✗ |
| | | 4 | İlk konuya dönersek, kaç litre gerekiyordu? | Tur 1'e (motor yağı) geri dön | ∅ P2, kategori yok ✗ |
| **C11** | VN, EL | 1 | Akü nasıl takviye yapılır? | procedure, charging | ∅ P2 ✓ |
| | | 2 | Kabloları hangi sırayla bağlamalıyım? | Takviye bağlamını koru | ∅ P2 ✗ (bağlamsız) |
| | | 3 | Hibritte 12V akü nerede? | Varyant değişimi: hibrit konumu ⚑M | ∅ P2 ✓ |
| **C12** | BK, P0 kalıcılığı | 1 | Hava yastığı uyarı ışığı yanıyor. | safety / srs, P0 | ∅ P0 ✓ |
| | | 2 | Yolcu koltuğunda çocuk varken sorun olur mu? | P0 bağlamı korunmalı (SRS + çocuk koltuğu) | ∅ P2 ✗ |
| | | 3 | Servise gidene kadar ne yapmalıyım? | P0 kanıtıyla sınırlı cevap | ∅ P2 ✗ |
| **C13** | EL, zincir kırılması, pazar | 1 | Şerit takip yardımı nasıl açılır? | driver_assistance / procedure, P1 | ∅ P1 ✓ |
| | | 2 | Yağmurda neden kapanıyor? | LTA bağlamı + sensör koşulları | ∅ P2 ✗ |
| | | 3 | Avrupa'daki Corolla'da da aynı mı çalışıyor? | LTA + pazar karşılaştırması ⚑P | ⟲ yalnızca tur 2'ye bağlandı, LTA kayboldu ✗ |
| **C14** | EL, KD | 1 | Bijon somunu sıkma torku kaç? | tires_brakes / specification, P0 | ∅ P2 ✗ |
| | | 2 | Sırası? | Sıkma sırası | ∅ P2 ✗ |
| | | 3 | Lastik değişince TPMS sıfırlanmalı mı? | Konu değişimi (aynı kategori) | ∅ P0 ✓ |

**Özet:** 44 turun 30'u takip turu. Takip turları beklenen davranışa göre ayrı değerlendirildi
(ölçüm ayrıntısı §2.4):

| Beklenen davranış | Tur | Sonuç |
|---|---:|---|
| Bağlam korunmalı | 24 | 3 doğru (C03-2, C04-2, C07-2) · 2 yanlış köke bağlandı (C02-3, C13-3) · 19 bağlam taşınmadı |
| Konu değişimi (bağlam taşınmamalı) | 3 | 3 doğru (C05-2, C10-2, C14-3) · yanlış bağlam taşıma yok |
| Bağımsız da cevaplanabilir | 2 | C09-3, C11-3 bağlamsız işlendi (kabul edilebilir) |
| Kullanıcı bilgi veriyor (pazar/motor) | 1 | C06-2: bilgi bir konuşma durumuna yazılmıyor; bu fonksiyonlarla ölçülemez |

C07-2 doğru birleşti, ancak retrieval seçili aracın `vehicle_id` değeriyle sınırlı olduğu için 2020 modeli
kaynağına ulaşılamaz.

### 2.3 Pazara ve varyanta göre değişen kritik sorular

Aşağıdaki boyutlar, aynı sorunun farklı pazarlarda **farklı doğru cevabı** olmasına yol açar.
Değerler soru tasarımı içindir; cevapta ilgili pazar kılavuzundan doğrulanmalıdır.

| Boyut | US | Canada | EU / TR | Etkilenen sorular |
|---|---|---|---|---|
| Trim adlandırması | LE, SE, XSE vb. | Benzer, pakete göre değişir | Farklı trim adları; "LE" kullanılmaz | Tüm D işaretli sorular, Q33, Q36, Q41 |
| Benzinli motor | 2.0 L | 2.0 L | 1.5 L benzinli seçenekler (TR üretimi sedan) | N15, N17, N21, N31 |
| Hibrit | 1.8 L hibrit, FWD/AWD | Benzer | 1.8 L / 2.0 L hibrit (pazara göre) | N05, N27, N34, N43, C07, C11 |
| Birimler | mil, psi, qt, °F | km, kPa, L, °C | km, bar/kPa, L, °C | N35, N40, Q01, Q18 |
| Yakıt oktanı | AKI (ör. 87) | AKI | RON (ör. 95); ölçek farklı | N32, Q40 |
| Bakım planı | Toyota US planı (mil tabanlı) | Kanada planı | Toyota Europe/TR planı (km ve yıl) | N31, Q01, Q04 |
| Recall kanalı | NHTSA (VIN sorgu) | Transport Canada | Ulusal kurumlar ve Toyota yetkili servisi; TR'de distribütör | N07, Q14, Q15 |
| Regülasyon donanımı | — | — | eCall; GSR2 kapsamında hız sınırı uyarısı (ISA) | N36, N38 |
| Bağlı servisler | Toyota app, Remote Connect | Bölgesel karşılığı | Pazara özel uygulama ve hizmetler | N37, Q33, Q34 |
| TPMS | Doğrudan TPMS yaygın | Benzer | Pazar ve donanıma göre değişir | N28, Q11, Q19 |

**Cevap kuralı:** ⚑P işaretli bir soruda pazar bilinmiyorsa sistem önce pazarı sormalı ya da
cevabı kaynağın pazarıyla açıkça etiketlemelidir. Örnek: "Bu değer ABD kılavuzuna aittir."

### 2.4 Mevcut sınıflayıcı ölçümü

**Ölçülen kod:** commit `bdd4d31c7899c018e39227d296805cecd7c52da9` (main ile aynı). `caragent/` altında
yerel değişiklik yokken ölçüldü. Ölçüm 2026-11-17'de bu commit üzerinde yeniden yapıldı. v2'nin ilk
taslağındaki ölçümlerin ham kayıtları saklanmadığı için bu tablo yalnızca yeniden ölçümün sonuçlarını
gösterir. Yeniden ölçüm §2.1'deki 44 planner değerinin tamamını aynen üretti.

**Yöntem:**

- **Girdiler:** Soru ve tur metinleri bu belgenin §2.1 ve §2.2 tablolarından otomatik okundu; tablodaki
  metinle birebir aynıdır.
- **Bağımsız sorular:** `caragent.rag.question_plan(soru)` konuşma geçmişi olmadan çağrıldı. Ölçülen alanlar:
  `priority`, `intent`, `categories`, `systems`. Beklenen öncelik, §2.1'deki kategorinin `QUESTION_TAXONOMY`
  önceliğidir.
- **Takip zincirleri:** k. tur için `retrieval_question(tur_k, geçmiş)` ve `question_plan(tur_k, geçmiş)`
  çağrıldı. `geçmiş`, önceki her tur için `{"role":"user","content":tur_i}` ve
  `{"role":"assistant","content":"."}` çiftlerinden oluşur. Fonksiyon yalnızca `user` mesajlarını okur;
  asistan içeriği sonucu etkilemez.
- **Bağlam birleştirmenin tespiti:** Çıktı, girdi sorusundan farklıysa önceki turlardan hangisinin kök
  alındığı `"\nTakip sorusu: "` ayırıcısının solundaki metinden belirlendi.
- **Beklenen davranış:** Her takip turu için araştırmacı tarafından önceden etiketlendi (bağlam korunmalı +
  beklenen kök tur / konu değişimi / bağımsız cevaplanabilir / bilgi beyanı). Etiketler ve sonuçlar §2.2
  özet tablosundadır.

| Ölçüm | Sonuç |
|---|---|
| Kategori önceliği (taksonomi) P0 olan soru | 31 |
| Bunlardan planner'ın P0'ın altında sınıfladığı | **15** (N01, N02, N06, N07, N08, N09, N11, N14, N18, N21, N24, N25, N29, N30, N38) |
| Bunlardan doğrudan can güvenliği sorusu olanlar | **7** (N01, N02, N06, N07, N08, N09, N11) |
| Kategori önceliği P1 olup planner'ın P2 verdiği | 2 (N33, N43) |
| Beklenen kategorinin planner çıktısında bulunmadığı soru | 25 / 44 |
| Bağlam korunması beklenen takip turları (24) | 3 doğru · 2 yanlış kök · 19 bağlam taşınmadı |
| Konu değişimi beklenen takip turları (3) | 3 doğru · 0 yanlış bağlam taşıma |

Bu ölçüm yalnızca bu iki fonksiyonun davranışını gösterir. Takip sorularında uçtan uca (retrieval ve LLM
cevabı dahil) başarıyı ölçmez.

**Gözlenen kök nedenler:**

- Türkçe çekim ve ünsüz yumuşaması: "ışık" ile "ışığı", "uyarı" ile "uyarıları", "geri çağır" ile
  "geri çağırması", "ağırlaşma" ile "ağırlaşırsa", "tork" ile "torku".
- Taksonomi alias'larında eksik terimler: hararet, sızıntı, yakıt kokusu, bijon, buji, işçilik,
  ABS, VSC, hava yastığı (yalnızca `QUESTION_SYSTEMS` içinde var, kategoride yok), akü
  (kategori alias'ı yok), DTC kalıbı (P0420).
- Planner, sistem eşleşmesini (ör. `srs`, `steering`) önceliğe yansıtmıyor. Sistem bulunsa bile
  kategori bulunamazsa öncelik P2 kalıyor (N08, N11).
- Takip çözümlemesi, parça adı içeren ya da tetikleyici kelime içermeyen en son kullanıcı mesajını kök
  kabul ediyor (`retrieval_question`). Bu yüzden "Kışın?" gibi çözülmemiş eliptik turlar kök yerine geçiyor.

Bu ölçüm bir hata raporu değil, sonraki çalışma için bir **gereksinim kanıtıdır**. Kod değişikliği bu
görevin kapsamı dışındadır.

### 2.5 N01–N44: yerel Lemon arşiviyle karşılaştırma (v2.1)

**Durum işaretleri:**

- ✅ **Seçili araç için içerik bulundu:** sorunun sorduğu bilgi, 2024 LE ile çelişmeyen aralıktaki bir sayfanın
  metninde var. Bu, arşiv içeriğinin bulunduğunu gösterir; gerçek bir araç için doğruluk garantisi değildir.
- ◐ **Seçili araç için içerik kısmen bulundu:** ilgili teknik veya servis içeriği var, ancak sorunun bir
  parçası (sürücü eylemi, aralık, sıra) incelenen sayfalarda yok.
- ⇄ **İçerik yalnızca başka varyantta bulundu:** soru Corolla LE kapsamında, ancak ilgili içerik yalnızca başka
  bir varyant (ör. *Corolla Hybrid LE*) için var; LE'ye uygulanamaz.
- ⊘ **Soru seçili aracın kapsamı dışında:** soru, benzinli LE'de bulunmayan bir sisteme (hibrit) özgü. Arşivde
  ilgili bir şey bulunup bulunmadığı ayrıca belirtilir. Kapsam dışı olmak, sorunun riskini düşürmez (§3.5).
- ✖ **İncelenen dosyalarda bulunamadı:** bu, kılavuzda olmadığı anlamına gelmez.

**Diğer notlar:**

- "Farklı kaynak" ibaresi, sorunun doğası gereği başka bir belge gerektirdiğini gösterir (Owner Manual,
  bakım planı, pazar kılavuzu, VIN sorgusu).
- **Özgün URL:** hiçbir satırda belirlenemedi (§0B).
- **Yollar:** `pages/` ile başlayan yollar §0B'deki klasöre görelidir.
- **Bölüm kısaltmaları:** *R&D* = Repair and Diagnosis (Single Page), *QL* = Quick Lookups,
  *MSS* = Maintenance › Procedures › Maintenance - Service Specifications.

| ID | Durum | Yerel kaynakta bulunan | Sayfa ve bölüm | Araç / varyant koşulu |
|---|---|---|---|---|
| N01 | ◐ | "The MIL flashes when a catalyst-damaging misfire is detected." Sürücünün durup durmayacağına dair talimat yok; **farklı kaynak: Owner Manual** | `pages/17740.html`: R&D › Engine Performance › Engine Control System (M20A-FKS) › DTC P0300-00 … › Description | M20A-FKS; üretim [03/2023 - 09/2024]. Eşdeğerleri: `17730` [11/2022 - 03/2023], `17750` [09/2024 - ] |
| N02 | ✖ | Hararette sürücü eylemi bulunamadı. Yalnızca teknik içerik var: soğutma sıvısı sıcaklık sensörü DTC'si, gösterge arızası | `pages/16873.html`: DTC P0115-11 [03/2023 - 09/2024]; `pages/4729.html` (12.3" gösterge) | M20A-FKS; gösterge tipine bağlı. **Farklı kaynak: Owner Manual** |
| N03 | ◐ | Yağ basıncı değeri (1000 rpm'de 80 kPa veya üstü) ve uyarı devresi (sesli ikaz, mesaj) var; sürücü eylemi yok | `pages/467.html`: QL › Common Specs (M20A-FKS); `pages/4899.html`: Engine Oil Pressure Switch Circuit [09/2022 - 11/2022] | M20A-FKS. 2024 aralığındaki devre sayfası bu incelemede bulunamadı |
| N04 | ◐ | "Brake Warning Light Remains ON" teşhis prosedürü var (teknisyen için); sürücü eylemi yok | `pages/12006.html`: Brakes › Electronically Controlled Brake System (Except HEV) (W/ Electric Parking Brake) › … [11/2022 - ] | Benzinli **ve EPB'li**; EPB'siz araç için ayrı ağaç var |
| N05 | ⊘ | Soru hibrite özgü. Tam metin aramasında "check hybrid system / hybrid system warning" ifadesi 6 sayfada bulundu; altısı da "Different variant/trim" uyarılı hibrit servis önlemi (Precaution) sayfaları. Sürücü eylemi bulunamadı | `pages/38193.html`: … › External Pages › Different variant/trim › Hybrid Battery System (Li-Ion) › Precaution [09/2022 - ] | Benzinli LE kapsamı dışında; içerik yalnızca başka varyant sayfalarında |
| N06 | ✖ | Yakıt kokusu veya sızıntıda sürücü eylemi bulunamadı. Yalnızca servis sonrası "Inspect for fuel leaks" adımları var | `pages/14628.html`: Engine Mechanical › Fuel System (M20A-FKS) › Precaution [03/2019 - 06/2021] | Bulunan sayfa 2024 aralığında değil. **Farklı kaynak: Owner Manual** |
| N07 | ⇄ | Recall listesi yalnızca Hybrid LE için: 24V548000, 24V878000. TR'de sorgulama kanalı arşivde yok | `pages/627.html` → `pages/72986.html`: QL › Technical Bulletins › Safety Recalls | Hybrid LE 1.8L VIN C. **Farklı kaynak: VIN sorgusu, distribütör** |
| N08 | ◐ | Yolcu oturan sınıflandırma sistemi (OCS) DTC'leri ve sensör arızaları var; "OFF" göstergesinin kullanıcıya anlamı bulunamadı | `pages/597–598.html`: QL › DTC Index › OCCUPANT CLASSIFICATION SYSTEM (TMC / TMMMS Made) (2023-25); `pages/32044.html` | **Üretim fabrikasına bağlı** (TMC / TMMMS, VIN ile belirlenir) |
| N09 | ◐ | "ABS Warning Light Remains ON" ve "Slip Indicator Light Remains ON" teşhis prosedürleri var; sürücü eylemi yok | `pages/11994.html`, `pages/12030.html`: Brakes › … (W/ Electric Parking Brake) [11/2022 - ] | Benzinli, EPB'li |
| N10 | ◐ | Hidrolik tipi var (DOT 3 / DOT 4); "seviye düşükse ekleme yeterli mi?" cevabı yok | `pages/30750.html`: MSS › Service Data [08/2023 - 09/2024] › Brake Fluid (For Gasoline Model); `pages/625.html` | Benzinli (G16E-GTS hariç) |
| N11 | ◐ | "Heavy Steering Feel (EPS Warning Light (Yellow))" teşhis prosedürü var; güvenli durma talimatı yok | `pages/32718.html`: Steering › Power Steering System (Except HEV) › POWER STEERING SYSTEM (for Gasoline Model) [11/2022 - ] | Benzinli |
| N12 | ✖ | Yalnızca PCS DTC dizini var; gereksiz frenleme belirtisi veya kullanıcı rehberi bulunamadı | `pages/479.html`: QL › DTC Index › PRE-COLLISION SYSTEM (for TMMMS Made) | Fabrika ayrımı var. **Farklı kaynak: Owner Manual** |
| N13 | ✅ | P0171 açıklaması (yakıt düzeltmesi, fuel trim) ve teşhis prosedürü var | `pages/17295.html` (Description), `pages/17303.html` (Procedure): R&D › Engine Control System (M20A-FKS) › DTC P0171-00 … [03/2023 - 09/2024] | M20A-FKS. **2024 model yılı için üç tarih aralığı var**: [11/2022 - 03/2023], [03/2023 - 09/2024], [09/2024 - ] |
| N14 | ◐ | P0420 izleme açıklaması ve teşhis akışı var (önce diğer DTC'ler, sonra freeze frame); "motora zarar verir mi?" cevabı yok | `pages/18451.html`, `pages/18459.html`: DTC P0420-00 … [11/2022 - ] | M20A-FKS |
| N15 | ✅ | Filtreli boşalt-doldur 4,2 L (4,4 US qt), filtresiz 3,9 L. Fluids sayfasında 4.40 qt / 4.16 L ve 0W-8 notu var | `pages/30761.html`: MSS › Service Data [08/2023 - 09/2024] › M20A-FKS Engine Oil Standard Capacity; `pages/625.html`: QL › Fluids | **Üretim tarihine bağlı:** 08/2023 öncesi üretimde 4,6 L / 4,9 US qt (`pages/30742.html`) |
| N16 | ◐ | CVT sıvısı değişim prosedürü ve sıvı sıcaklığı ayarlama adımlarına atıf var; sıcaklık değeri incelenen sayfada bulunamadı. Sıvı tipi: TOYOTA Genuine CVTF FE | `pages/30384.html`: Maintenance › K120/K121 CVT Fluid › Replacement [03/2023 - 09/2024] › Procedure; `pages/625.html` | K120/K121 CVT |
| N17 | ◐ | Tip (TOYOTA SLLC) ve kapasite var: CVT için tam kapalı (fully sealed) tipte 6,2 L, diğer tipte 6,4 L. İlk değişim aralığı bulunamadı | `pages/30753.html`: MSS › Service Data [08/2023 - 09/2024] › M20A-FKS Coolant; `pages/625.html` | **Soğutma sistemi tipine bağlı.** Aralık için **farklı kaynak: bakım planı** |
| N18 | ◐ | Tork 103 N·m (76 ft·lbf) üç ayrı sayfada var; sıkma sırası bulunamadı | `pages/467.html` (Common Specs), `pages/629.html` (Tire Fitment), `pages/30926.html`: MSS › Torque Specifications [03/2023 - 09/2024] › Tire And Wheel | 4D Sedan, FWD |
| N19 | ✅ | Sorulan braket cıvatası ("Front disc brake cylinder mounting x Steering knuckle"): 107 N·m (79 ft·lbf). Aynı tablodaki 34,3 N·m değeri **başka bir cıvataya** aittir (kaliper gövdesi × braket) ve bu sorunun cevabı değildir | `pages/10780.html`: Brakes › Brake System (Front) (Service Specifications) › Torque Specifications [09/2022 - ] › Front Brake (Except 4-Pot Caliper) | 4 pistonlu kaliper hariç; LE'nin kaliper tipi doğrulanmalı |
| N20 | ✅ | Ön disk kalınlığı standart 22,0 mm, minimum 19,0 mm; balata minimum 1,0 mm; disk salgısı en fazla 0,05 mm | `pages/10770.html`: Brakes › Brake System (Front) (Service Specifications) › Service Data [09/2022 - ] › Front Brake (Except 4-Pot Caliper) | 4 pistonlu kaliper hariç |
| N21 | ◐ | Buji torku 20 N·m, tipi DENSO FC20HR-Q8; değişim aralığı bulunamadı | `pages/30921.html`: MSS › Torque Specifications [03/2023 - 09/2024] › M20A-FKS Spark Plug; `pages/467.html` | M20A-FKS. Aralık için **farklı kaynak: bakım planı** |
| N22 | ◐ | Karter tapası 40 N·m, yağ filtresi 17,5 N·m; conta değişimi ifadesi incelenmedi | `pages/30946.html`: MSS › Torque Specifications [03/2023 - 09/2024] › M20A-FKS Oil And Oil Filter | M20A-FKS |
| N23 | ⇄ | Ön balata işçiliği 1,2 saat ("Gas/Electric, Front, Both Sides"), ancak **yalnızca Hybrid LE** için | `pages/202.html`: Labor Times › Other Variant › Brakes › Brake Shoes &/Or Pads › Remove & Replace | Hybrid LE 1.8L VIN C; LE için işçilik süresi yok |
| N24 | ⇄ | Su pompası işçiliği 7,4 saat ve kapsamına motor ile şanzımanın sökülüp takılması dahil; **yalnızca Hybrid LE** için. Benzinli LE'ye aktarılamaz | `pages/262.html`: Labor Times › Other Variant › Water Pump › Remove & Replace | Hybrid LE 1.8L VIN C |
| N25 | ◐ | Akü bağlantısı kesilince otomatik öğrenen sistemler listeleniyor: benzinlide ön kamera (15 km/h ve üstünde 1 s düz sürüş), kapı kilidi. Manuel başlatma listesi incelenmedi | `pages/29107.html`: General Information › OEM General Information › Setup › Automatic Learning Chart [11/2022 - ]; `pages/29105.html` | Benzinli, GR olmayan model |
| N26 | ✖ | Takviye (jump start) bağlantı sırası bulunamadı; yalnızca HEV için ECU yapılandırmasında booster terminali geçiyor | `pages/29113.html` (HEV ECU configuration) | **Farklı kaynak: Owner Manual** |
| N27 | ⊘ | Soru hibrite özgü. Tam metin aramasında yardımcı akü (auxiliary battery) konumunu bildiren bir ifade bulunamadı | — | Benzinli LE kapsamı dışında; içerik incelenen dosyalarda bulunamadı |
| N28 | ◐ | Verici kimliği (transmitter ID) kaydı Techstream ile yapılıyor; kimlik lastik takılmadan önce not edilmeli. "Yalnızca lastik değişince kayıt gerekir mi?" doğrudan yazmıyor. Görseller kimlik etiketinin konumunu gösteriyor (incelendi) | `pages/34061.html`: Suspension › Tire Pressure Warning System (Except HEV, Type B) › Registration [03/2023 - ] › Procedure; `pages/34062.html` | Benzinli, **TPMS "Type B"** (LE'nin tipi doğrulanmalı) |
| N29 | ✖ | Yalnızca araçtan bağımsız genel "Cabin Air Filter" açıklaması var; Corolla prosedürü bulunamadı | `pages/27946.html`: General Information › Routine Inspection Reference Guide | Genel (araca özgü değil) |
| N30 | ✅ | Gaz kelebeği temizliğinden sonra *Learning Value Reset* ve *Idle Learning* gerekli | `pages/21693.html`: Engine Control System (M20A-FKS) › SFI System › Initialization [11/2022 - ] | M20A-FKS |
| N31 | ✖ | Arşivde M15A (TR 1.5) motoru ve bakım planı yok | — | **Farklı kaynak: TR kılavuzu ve bakım planı** |
| N32 | ✖ | Oktan bilgisi Fluids sayfasında yok. Ancak arşiv pazara göre yağ sınıfının değiştiğini gösteriyor (Meksika için 0W-16, 0W-20…10W-30) | `pages/625.html`; `pages/30760.html`: MSS › M20A-FKS Standard Oil Grade (For MEXICO) | Pazar farkı arşivde kısmen görünür. **Farklı kaynak: pazar kılavuzları** |
| N33 | ◐ | Ses ve multimedya sistemleri ekran tipine göre ayrılıyor (8" tek düğmeli / 10.5", knobless radyo…); yıl karşılaştırması yok | `pages/483–486.html`: QL › DTC Index › Audio / Video DTCS | **Ekran donanımına bağlı** |
| N34 | ⊘ | Soru AWD hibrite özgü. Ortak kılavuzda yalnızca GF1A transfer yağı servis verisi görüldü; AWD ile FWD bakım kalemlerinin karşılaştırması bulunamadı | `pages/30767.html`: MSS › Service Data [08/2023 - 09/2024] › GF1A Transfer Oil | Benzinli FWD LE kapsamı dışında |
| N35 | ✖ | Kanada kılavuzu yok. Arşiv değerleri zaten hem US hem metrik birimle veriyor | — | **Farklı kaynak: Kanada Owner Manual** |
| N36 | ✖ | AB'ye özgü ISA yok; yalnızca Road Sign Assist DTC'si var | `pages/480.html`: QL › DTC Index › ROAD SIGN ASSIST SYSTEM | US/Canada içerik. **Farklı kaynak: EU kılavuzu** |
| N37 | ✖ | Uygulama üzerinden uzaktan klima bulunamadı | — | **Farklı kaynak: bağlı servis dokümanı** |
| N38 | ◐ | Safety Connect ve manuel SOS düğmesi var (US karşılığı); eCall yok | `pages/3948.html`: Accessories & Equipment › Cellular Communication System › Manual (SOS) Switch [09/2022 - 11/2022] | US/Canada. Bulunan sayfa [09/2022 - 11/2022] aralığında; 2024 aralığı incelenmedi. eCall için **farklı kaynak** |
| N39 | ✖ | Yalnızca genel "Wiper Blades" açıklaması var; ölçü ve prosedür bulunamadı | `pages/27952.html` | Genel |
| N40 | ✖ | Gösterge birim ayarı bulunamadı | — | **Farklı kaynak: Owner Manual** |
| N41 | ✖ | Bagaj içi acil açma kolu bulunamadı | — | **Farklı kaynak: Owner Manual** |
| N42 | ◐ | LE için tek lastik ölçüsü: 205/55R16 91H; basınç ön 35 / arka 33 psi, jant 7J, 5×100 mm. Kış lastiği alternatifi yok | `pages/629.html`: QL › Tire Fitment | FWD 4D Sedan. Giriş sayfasına göre Tire Fitment varyanta göre değişebilir |
| N43 | ⊘ | Soru hibrite özgü. Ortak kılavuzda hibrit model için EV modu anahtarı muayenesi gibi teknisyen içerikleri var; EV modunun ne zaman devreye girdiğine dair sürücü açıklaması incelenen dosyalarda bulunamadı | `pages/30150.html`: Hybrid/Electric Powertrain › Hybrid Battery Control System › Combination Switch › Inspection [01/2019 - ] | Benzinli LE kapsamı dışında |
| N44 | ◐ | Koltuk ısıtma sistemi sayfaları var; LE'de bulunup bulunmadığı ortak kılavuzdan belirlenemez | `pages/7033.html`: Accessories & Equipment › Seats › Seat Heater System › Precaution [09/2022 - ] | **Donanıma bağlı.** Kesin cevap için VIN veya donanım listesi gerekir |

**Karşılaştırmanın özeti:**

- **Arşivin güçlü olduğu alanlar:**
  - teknik değerler (N15, N18–N22; N19 ve N20 tam, diğerleri kısmen)
  - teşhis (N13, N14)
  - servis ve öğrenme prosedürleri (N25, N28, N30)
- **Arşivin yetersiz kaldığı alanlar:**
  - sürücü kararları (N01–N04, N06, N09, N11)
  - bakım aralıkları (N17, N21)
  - pazar karşılaştırmaları (N31–N37)
  - işçilik ve recall (yalnızca başka varyantta: N07, N23, N24)
- **Kapsam dışı sorular (N05, N27, N34, N43):** benzinli LE için "uygulanmaz" cevabı gerektirir. Hibrit
  araç seçildiğinde ayrıca değerlendirilmelidir.

### 2.6 Soruların kökeni ve kullanıcı ihtiyacı sinyali (v2.1)

**Köken:**

| Köken | Sorular | Açıklama |
|---|---|---|
| Gerçek kullanıcı sorusundan uyarlandı | v1 Q01–Q44 (v1 kaynakları) | Bu raporda yeni bir soru bu sınıfa alınmadı |
| İncelenen kılavuz içeriğinden türetildi | **L01–L12** (§2.7) | Yerel arşivde okunan sayfalardan |
| Araştırmacı tarafından tasarlandı | **N01–N44** | v2'de kod boşluklarından, taksonomiden ve senaryo ihtiyacından tasarlandı. Kullanıcı kaynağından alınmadı |

**Kullanıcı ihtiyacı sinyali:** N sorularının bir kısmı için, *sonradan* erişilebilir kullanıcı kaynaklarında
benzer talep arandı. Bu sinyaller sorunun kökenini değiştirmez; yalnızca gerçek ihtiyaca işaret eder.

| İlgili soru | Bulunan sinyal | Güç |
|---|---|---|
| N15, L01 | Bob Is The Oil Guy forumunda 2024 Corolla 2.0 sahipleri yağ kapasitesini tartışıyor: kılavuzda 4,4 qt mi, 2023'te 4,9 qt mi? Arşivdeki 08/2023 üretim aralığı değişimi *olası* bir açıklamadır; forumdaki araçların üretim tarihleri doğrulanmadı | Güçlü: aynı model ve yıl |
| L02 | 2023–2024 Corolla sahipleri 0W-8 / 0W-16 değişimini soruyor (Bob Is The Oil Guy) | Güçlü |
| N08, N04 bağlamı | CarComplaints'te 2023 ve 2024 Corolla hava yastığı ve SRS şikâyetleri; NHTSA 23V480 (2023 Corolla spiral kablo, SRS lambası) | Orta: aynı model, sorun türü yakın |
| N13 | P0171 "System too lean" başlığı (Toyota Owners Club, eski model yılı Corolla) | Zayıf: farklı yıl ve motor |
| N14 | P0420 için doğrudan bir konu bağlantısı bulunamadı; yalnızca arama özetlerinde eski model yılı sahip anlatımları görüldü | Kanıt yok (bağlantı doğrulanamadı) |
| N28 | Sensör değişimi sonrası TPMS kimlik kaydı sorunu (2CarPros, 2011 Corolla; yanlış kaydedilen kimlik yüzünden lamba sönmüyor) | Zayıf: farklı yıl |
| N18 | Corolla bijon torku soru-cevapları ve 2023 Corolla'da "yeniden tork" sorusu (Toyota Owners Club) | Orta |
| N31 | Donanımhaber'de 2023 Corolla 1.5 sahipleri serviste kullanılan yağ sınıfını tartışıyor (5W-30 mu, 0W-20 mi?) | Orta: TR pazarı, farklı motor |
| Yeni sinyal | Şikâyetvar: TR Corolla 1.5'te EPB uyarı lambası ve soğutma sıvısı uyarısı şikâyetleri | Orta; v2 setinde karşılığı yok, sonraki turda soru adayı |

Sinyal bulunamayan N soruları için bu, sorunun sorulmadığı anlamına gelmez. Arama yalnızca standart web
aramasıyla ve sınırlı sayıda yapıldı.

### 2.7 Kılavuz içeriğinden türetilen sorular (L01–L12, v2.1)

Aşağıdaki sorular incelenen sayfalardan türetildi ve her biri o sayfayla ✅ doğrulandı. Sorudaki bilgi kaynak
sayfadadır; cevap değeri burada tekrar edilmez, yalnızca kanıt yeri gösterilir.

| ID | Soru | Kategori | Sayfa ve bölüm | Koşul |
|---|---|---|---|---|
| L01 | Aracım 08/2023'ten önce üretildiyse motor yağı kapasitesi farklı mı? | maintenance | `pages/30742.html` ve `pages/30761.html`: MSS › Service Data › M20A-FKS Engine Oil Standard Capacity | Üretim tarihi |
| L02 | 0W-8 bulamazsam 0W-16 kullanabilir miyim, sonra ne yapmalıyım? | maintenance | `pages/625.html`: QL › Fluids (Engine Oil notu) | 2.0L |
| L03 | Benim pazarımda hangi motor yağı sınıfları geçerli? | maintenance | `pages/30759.html` ve `pages/30760.html` (For MEXICO) | Pazar |
| L04 | Ön fren balatası en az kaç mm olmalı? | tires_brakes | `pages/10770.html`: Front Brake (Except 4-Pot Caliper) | Kaliper tipi |
| L05 | CVT'ye başka bir şanzıman yağı konursa ne olur? | maintenance | `pages/625.html`: QL › Fluids (Automatic Transmission Fluid notu) | 2.0L, CVT |
| L06 | Klima gazı tipi ve miktarı nedir? | ownership | `pages/625.html`: QL › Fluids (Air Cond Refrigerant) | 2.0L |
| L07 | Yakıt deposu kaç litre? | ownership | `pages/625.html`: QL › Fluids (Fuel Tank) | 2.0L |
| L08 | Akü söküldükten sonra ön kamera sistemi neden çalışmıyor ve nasıl düzelir? | driver_assistance | `pages/29107.html`: Automatic Learning Chart [11/2022 - ] | Benzinli, GR olmayan |
| L09 | Kontak açılınca SRS lambasının birkaç saniye yanıp sonra sönmesi normal mi? | safety_recalls | `pages/32014.html`: SRS Warning Light Remains ON [11/2022 - ] › Description | 2023–25 SRS |
| L10 | Kontak açılınca check engine lambasının yanıp motor çalışınca sönmesi normal mi? | warnings | `pages/16091.html`: MIL Circuit [11/2022 - 03/2023] › Description | M20A-FKS |
| L11 | Lastikleri değiştirirken TPMS sensör kimliğini neden önceden not etmeliyim? | tires_brakes | `pages/34061.html`: Registration [03/2023 - ] › Procedure | Type B TPMS |
| L12 | Radyatör kapağının açılma basıncı ne olmalı? | maintenance | `pages/467.html`: QL › Common Specs (M20A-FKS) | M20A-FKS; teknisyen sorusu |

---

## 3. Önceliklendirme raporu (P0–P2)

Bu bölümde üç farklı öncelik kavramı **ayrı** tutulur:

| Kavram | Kaynağı | Bölüm |
|---|---|---|
| **Kategori önceliği** | `QUESTION_TAXONOMY` içindeki kategori önceliği (mevcut kod) | §3.1–§3.3 |
| **Planner çıktısı** | `question_plan` fonksiyonunun belirli bir soruya verdiği öncelik (ölçüm) | §2.1, §2.4 |
| **Araştırma önerisi** | Kullanıcı riski ve ihtiyacına göre önerilen öncelik | §3.5 |

§3.4, öncelikten bağımsız olarak güvenlik açısından ek cevap kontrolü gerektirebilecek senaryoları listeler.
Kapsam bilgisi (soru seçili araca uygulanabilir mi?) önceliklerden ayrı değerlendirilir (§2.5, §3.5).

### 3.1 Kategori önceliği (mevcut taksonomi)

Sistem tutarlılığı için kategori önceliği olarak `QUESTION_TAXONOMY` değerleri olduğu gibi raporlanır.

| Öncelik | Kriter | Kategoriler | Yanlış cevabın etkisi |
|---|---|---|---|
| **P0** | Can güvenliği, geri çağırma, kritik arıza uyarısı **veya** hasarı önleyen bakım ve teknik değer | maintenance, warnings, safety_recalls, tires_brakes | Kaza, yolda kalma, motor/fren hasarı |
| **P1** | Sık tekrarlanan kullanım, bağlantı, sürüş desteği ve aktarma davranışı | driver_assistance, multimedia, keys_remote, efficiency_drivetrain | Yanlış kullanım, gereksiz servis, memnuniyetsizlik |
| **P2** | Konfor, donanım ve bilgi amaçlı sorular | ownership | Düşük; bilgi eksikliği |

### 3.2 Not: kategori önceliği P0 olan sorulardaki risk farkı

Kod taksonomisi "Bakım ve sıvılar" kategorisini P0 sayar; §3.1 bunu olduğu gibi raporlar. Ancak kategori
önceliği P0 olan sorular farklı risk türleri içerir:

- **P0-a (can güvenliği ağırlıklı):** recall, kritik uyarı, SRS, fren, direksiyon, hararet, yakıt sızıntısı.
  Hatanın olası bedeli kaza veya yaralanmadır. Bu sorularda kaynak zorunluluğu, kesin teşhis iddiasından
  kaçınma ve açık güvenlik eylemi öne çıkar (§3.4).
- **P0-b (mekanik hasar ağırlıklı):** yağ ve soğutma sıvısı, kapasite, bakım aralığı. Bu sorularda kesin
  değer, birim ve varyant/üretim tarihi doğrulaması öne çıkar.

Bu iki grup kesin sınırlarla ayrılmaz. Bazı teknik değerler doğrudan güvenliği etkileyebilir: bijon,
fren kaliperi ve braket torku, fren diski ve balata limitleri bunlara örnektir. Bu tür değerler için ek cevap
kontrolü gerekip gerekmediği soru bazında değerlendirilmelidir; bu raporda genel bir "gerekmez" kuralı
konulmaz. Bu ayrım **yeni bir öncelik seviyesi değildir**; taksonomi değişikliği bu görevin kapsamı dışındadır.

### 3.3 Kategori bazında gerekçe (v1 ve v2 birlikte)

| Kategori | Kategori önceliği | Ağırlıklı risk türü | Gerekçe | v1 soruları | v2 soruları |
|---|---|---|---|---:|---:|
| Uyarılar ve arıza belirtileri | P0 | a | Sürüş kararı içerir ("sürmeli miyim?"); belirti ile kesin teşhis karıştırılmamalı | 5 | 8 |
| Güvenlik ve geri çağırmalar | P0 | a | Etki olasılığı düşük ama zarar potansiyeli en yüksek; VIN'e bağlı | 4 | 4 |
| Lastikler ve frenler | P0 | a ve b | Fren arızası, bijon ve fren torku (a); lastik basıncı ve ölçüsü (b) | 5 | 7 |
| Bakım ve sıvılar | P0 | b (bazıları a) | En sık soru grubu; yanlış değer motor/şanzıman hasarına yol açabilir; fren hidroliği gibi kalemler güvenliği etkiler | 8 | 12 |
| Sürüş desteği | P1 | — | Sık sorulur; sensör koşulları ve pazar regülasyonu belirleyici | 5 | 2 |
| Multimedya ve telefon | P1 | — | Sık sorulur; risk düşük, yıl ve yazılım farkı yüksek | 5 | 1 |
| Anahtar ve uzaktan erişim | P1 | — | Paket ve pazar farkı en yüksek kategori | 4 | 1 |
| Yakıt ekonomisi ve aktarma | P1 | — | Normal çalışma ile arızanın ayrılması gerekiyor | 4 | 2 |
| Donanım ve genel kullanım | P2 | — | Düşük risk, bilgi amaçlı | 4 | 7 |

### 3.4 Güvenlik açısından ek cevap kontrolü gerektirebilecek senaryolar

Mevcut `evidence_guard` yalnızca direksiyon recall'ını kapsıyor. Aşağıdaki senaryolarda aynı ilkenin
(serbest üretim yerine kaynaktan çıkarımsal cevap, açık güvenlik eylemi, kesin teşhis iddiası yok)
değerlendirilmesi önerilir. Liste kapsayıcı değildir; güvenliği etkileyen teknik değerler (§3.2) de
değerlendirmeye alınmalıdır. Hibrit sistem uyarısı yalnızca hibrit araç seçildiğinde geçerlidir.

| Senaryo | Tetikleyici sistem / belirti | Örnek |
|---|---|---|
| SRS / hava yastığı uyarısı | `srs` | N08, C12 |
| Fren uyarısı, boşa giden pedal, ABS/VSC | `brakes` | N04, N09 |
| Yağ basıncı | `lubrication` | N03 |
| Hararet | `cooling` | N02, C09-3 |
| Yanıp sönen check engine | `engine` + "yanıp sönüyor" | N01, C04-3 |
| Yakıt kokusu veya sızıntı | `fuel` | N06 |
| Hibrit sistem uyarısı (yalnızca hibrit araçta) | `hybrid_system` | N05 |
| Güvenliği etkileyen teknik değer | bijon, fren kaliperi/braket torku, fren limitleri | N18, N19, N20 |
| Direksiyon kaybı veya recall | `steering` + recall (mevcut) | N11, C08 |

### 3.5 Araştırmanın önerdiği öncelik ve koddaki öncelik (v2.1)

Bu bölüm **araştırma önerisini** verir. Kategori önceliği (§3.1) ve planner çıktısı (§2.4) karşılaştırma
için yanında gösterilir. Araştırma önceliği, sorunun **kendi aracında** sorulduğu varsayımıyla yalnızca
riski ve ihtiyacı değerlendirir. Sorunun seçili araca (benzinli 2024 LE) uygulanıp uygulanmadığı ayrı
sütunda verilir. Kapsam dışı olmak riski düşürmez.

**Araştırma önceliği kriterleri:**

- **P0:** Yanlış cevabın kaza, yaralanma, yangın veya tekerlek/fren kaybına yol açabilmesi. Sürücünün
  "sürmeye devam etmeli miyim?" kararı da P0'dır.
- **P1:** Mekanik hasar, maliyet veya yanlış servis riski; sık ihtiyaç duyulan bakım ve teşhis bilgisi.
- **P2:** Konfor, bilgi veya maliyet tahmini.

| Grup | Sorular | Kategori önceliği | Planner çıktısı | **Araştırma önerisi** | Benzinli LE kapsamı | Gerekçe |
|---|---|---|---|---|---|---|
| Sürücü güvenlik kararı | N01, N02, N03, N04, N06, N08, N09, N11 | P0 | N03, N04: P0; N06: P1; diğerleri: P2 | **P0** | Kapsamda | Hayati risk; planner'ın düşük vermesi en kritik açık |
| Güvenliği etkileyen teknik değer | N10, N18, N19, N20 | P0 | N18: P2; diğerleri: P0 | **P0** | Kapsamda | Fren veya tekerlek kaybı riski |
| Sürüş desteği güvenliği | N12 | P1 | P0 | **P0** | Kapsamda | Beklenmeyen frenleme bir güvenlik olayıdır |
| Recall | N07 | P0 | P2 | **P0** | Kapsamda (yerel içerik yalnızca başka varyantta) | Cevap VIN yönlendirmesi olmalı |
| Hibrit sistem uyarısı | N05 | P0 | P0 | **P0** | **Kapsam dışı** | Hibrit sürücü için hayati olabilir; benzinli LE'de cevap "uygulanmaz" ve varyant netleştirmesi olmalı |
| Teşhis ve hasar önleyici bakım | N13, N14, N15, N16, N17, N21, N22, N25, N28, N30 | P0 | N13, N15, N16, N17, N22, N28: P0; diğerleri: P2 | **P1** | Kapsamda | Ağırlıklı risk mekanik hasar. Belirtiyle birlikte sorulursa (ör. yanıp sönen MIL) P0'a yükselebilir |
| Yol kenarı ve güvenlik amaçlı kullanım | N26, N41 | P2 | P2 | **P1** | Kapsamda | Yanlış takviye bağlantısı ve bagajda mahsur kalma riski |
| Pazar ve varyant karşılaştırması | N31, N32, N36, N38, N42 | N31, N38, N42: P0; N32, N36: P1 | N31, N42: P0; N32: P1; N36: P0; N38: P2 | **P1** | Kapsamda | Yanlış pazar bilgisi yanlış yakıt, yağ veya lastik seçimine götürebilir |
| Hibrit 12V akü konumu | N27 | P2 | P2 | **P1** | **Kapsam dışı** | Takviye sırasında yanlış bağlantı riski (hibrit araçta) |
| Maliyet ve işçilik | N23, N24 | P0 | N23: P0; N24: P2 | **P2** | Kapsamda (yerel içerik yalnızca başka varyantta) | Bilgi amaçlı |
| Konfor ve bilgi | N29, N33, N35, N37, N39, N40, N44 | karışık | karışık | **P2** | Kapsamda | Düşük risk |
| Hibrit bilgi ve bakım | N34, N43 | N34: P0; N43: P1 | N34: P0; N43: P2 | **P2** | **Kapsam dışı** | Düşük doğrudan risk |

**Kategori önceliğinden ayrışan araştırma önerileri:**

- *Bakım ve sıvılar* kategorisindeki soruların çoğu araştırma önerisinde P1'dir; güvenliği etkileyen
  değerler (N10) P0'da kalır.
- *Sürüş desteği* kategorisindeki N12 araştırma önerisinde P0'dır.
- Bu farklar taksonomi değişikliği önerisi **değildir**; kod taksonomisi korunur. Fark, sonraki ekibin
  değerlendirmesi için kayıt altına alınmıştır.

---

## 4. Temel kullanım senaryoları ve graph modelleme girdisi

> Bu bölüm graph tasarımı **değildir**. Sorulardan çıkan gereksinimleri, mevcut entity türleriyle
> (`entity_extractor.py`: component, system, maintenance_action, warning, technical_value, feature,
> symptom, fluid, recall) karşılaştırarak listeler.

### 4.1 Kullanım senaryoları

| # | Senaryo | Tetikleyici | Gereken kanıt | Cevap kuralı | Örnek |
|---|---|---|---|---|---|
| S1 | **Kritik uyarı triyajı** | P0-a uyarı veya belirti | Owner Manual uyarı bölümü, recall kaydı | Önce güvenlik eylemi ("güvenli yerde durun"), sonra kaynak; teşhis iddiası yok | N01–N06, C12 |
| S2 | **DTC teşhisi** | Arıza kodu kalıbı (P0xxx) | R&D DTC tablosu ve teşhis adımları | Olası nedenler "kesin değil" ibaresiyle; triyaj gerekiyorsa S1'e geçiş | N13, N14, C04 |
| S3 | **Teknik değer sorgusu** | specification + parça | R&D spec tablosu | Değer + birim + koşul + varyant; varyant belirsizse sor | N15, N18–N22 |
| S4 | **İşçilik ve servis planlama** | labor_cost | Labor Times kaydı | Standart süre + kapsam (ön/arka, ek işlem); fiyat uydurmama | N23, N24, C03 |
| S5 | **Bakım karar desteği** | interval | Bakım planı (pazara özel) | Aralık + birim + normal/ağır kullanım + pazar etiketi | N17, N31, C07 |
| S6 | **Varyant/pazar çözümleme** | ⚑ işaretli soru, bilinmeyen varyant | Çok pazarlı kılavuz kapsamı | Netleştirme sorusu veya cevabı kaynak pazarıyla etiketleme | N31–N36, C06 |
| S7 | **Recall sorgulama** | recall_lookup | Recall kaydı + VIN | Uygunluğu kesinleştirmeme; pazara göre VIN sorgu kanalı | N07, C08 |
| S8 | **Çok turlu konuşma** | Eliptik takip, konu değişimi | Konuşma durumu | Kök soru ve varyant korunur; konu değişiminde bağlam bırakılır | C01–C14 |

### 4.2 Varlık gereksinimleri

| Gereksinim | Neden gerekli (soru kanıtı) | Mevcut karşılığı | Boşluk |
|---|---|---|---|
| **Araç varyant koşulu** (model, yıl, motor, güç aktarma, trim/paket, pazar) | ⚑ işaretli 37 soru; C06, C07, C11 | `Vehicle` + `vehicle_id`; varyant uyumsuzluğu yalnızca metin kalıbıyla yakalanıyor | Kanıt ve değerin hangi varyanta uygulandığı yapısal olarak tutulmuyor |
| **Pazar** | N31–N38, §2.3 | Kaynak metadatasında `market` var | Pazar karşılaştırması ve netleştirme için sorgulanabilir değil |
| **DTC (arıza kodu)** | N13, N14, C04 | Yok (`warning` ile `symptom` arasında dağılmış) | Kod, açıklama, olası neden, teşhis adımı ilişkisi |
| **Teknik değer: birim ve koşul** | N15–N22 | `technical_value` | Birim, koşul (soğuk/sıcak, filtreli/filtresiz) ve varyant koşulu açık alan değil |
| **İşçilik operasyonu** | N23, N24, C03 | Yok | Operasyon, standart süre, kapsam ve **hangi varyanta ait olduğu**. Yerel arşivde işçilik yalnızca Hybrid LE için var (§0B) |
| **Üretim tarihi aralığı** (v2.1) | N13, N15, N17, L01 | Kaynak metinde `[MM/YYYY - MM/YYYY]` olarak var; model yılı ile aynı şey değil | Değerin hangi üretim aralığında geçerli olduğu; aynı model yılında birden fazla aralık olabilir |
| **Donanım ve fabrika koşulu** (v2.1) | N04, N08, N09, N28, N33, N44 | Yok | EPB'li/EPB'siz, TMC/TMMMS üretimi, TPMS tipi, ekran tipi gibi VIN'e bağlı koşullar |
| **Uyarı önem seviyesi ve eylem** | N01–N09, §3.4 | `warning` ile `warns_about` | Önem seviyesi (dur / servise git / bilgi) ve önerilen eylem yok |
| **Recall: VIN kapsamı ve pazar** | N07, N11, C08 | `recall` ile `affects` | Pazar, kapsanan üretim aralığı, "VIN ile doğrula" bayrağı |
| **Prosedür adımları** | N25, N28–N30 | `maintenance_action` | Sıralı adım ve ön koşul (ör. motor sıcaklığı) |

### 4.3 İlişki gereksinimleri

| İlişki ihtiyacı | Örnek soru | Mevcut ilişki |
|---|---|---|
| Değer → geçerli olduğu varyant/pazar | N15, N31 | Yok (`APPLIES_TO_VEHICLE` yalnızca araç düzeyinde) |
| DTC → olası neden (bileşen) → teşhis adımı | N13, C04 | Kısmen: `indicates`, `resolved_by` (belirti için) |
| Uyarı → önem seviyesi → eylem | N01–N06 | Kısmen: `warns_about` |
| Recall → bileşen → belirti | C08 (tık sesi → direksiyon → 24V878000) | `affects` var; belirti bağlantısı yok |
| Operasyon → işçilik süresi → parça | N23, N24 | Yok |
| Bakım işlemi → aralık → kullanım koşulu (normal/ağır) | N17, Q01, F01 | `has_interval`; koşul yok |

### 4.4 Retrieval pipeline girdileri

Teknik uygulama önerileri Ek A'dadır.

---

## Ek A: Teknik uygulama önerileri (kısa)

> Bu ek, sonraki ekip için kayıttır. Bu görevde kod değişikliği yapılmadı.

1. **İnce intent → route intent eşlemesi.** JSON'daki ince intent'ler ve bu rapordaki amaç ekseni,
   koddaki 6 route intent'e eşlenmeli. Örnekler:
   - `warning_triage` ve `triage` → `troubleshooting` (P0-a ise guard adayı)
   - `labor_cost` → yeni route ya da `specification`
   - `comparison` → varyant netleştirme akışı
2. **Ortak sistem sözlüğü.** JSON `system` değerleri ile `QUESTION_SYSTEMS` anahtarları tek bir
   sözlükte birleşmeli (`tires`/`tpms` → `tires_tpms`, `drcc`/`lta`/`pcs` → `driver_assistance`).
   `hybrid_system`, `fuel` ve `body` eklenmeli.
3. **Öncelik kuralı.** Sistem eşleşmesi önceliğe yansımalı: `srs`, `steering`, `brakes`, `fuel`
   ve `cooling` sistemleri kategori bulunamasa bile en az P0 sayılmalı (N08, N11).
4. **Konuşma durumu (slot).** Bağlamı yalnızca metin birleştirmeyle değil, durumla taşımak gerekir:
   aktif konu, kök soru, araç varyantı (pazar, motor) ve P0 bayrağı. P0 bayrağı, konu değişene
   kadar korunmalıdır (C12).
5. **Kök soru seçimi.** Eliptik takip, önceki çözülmemiş takibe değil **kök soruya** bağlanmalı
   (C02, C13).
6. **Kapsam dışı araç veya yıl.** Seçili aracın dışında bir yıl/model sorulursa sessizce yanlış
   kaynakla cevap verilmemeli; araç değiştirme veya netleştirme önerilmeli (C07).
7. **Değerlendirme seti.** N01–N44, gelecekte sınıflayıcı regresyon testi için aday veridir.
   Beklenen kategori ve öncelik bu raporda verilmiştir. C01–C14 ise çok turlu RAG değerlendirmesi
   için adaydır; v1'de önerildiği gibi her turda kaynaklar yeniden getirilmelidir.
8. **(v2.1) Varyant ve tarih filtresi.** Lemon sayfaları ortak platform kılavuzudur. Retrieval şu
   sayfaları LE cevabından ayırmalı:
   - "different variant/trim than selected" uyarılı sayfalar,
   - başka motor kodları (G16E-GTS, 2ZR-FXE, 2ZR-FAE),
   - aracın üretim tarihini kapsamayan `[MM/YYYY - MM/YYYY]` aralıkları.

   Mevcut `_source_context` yalnızca ilk maddeyi yakalıyor.
9. **(v2.1) Kaynak türü yönlendirmesi.** Sürücü eylemi soruları ("sürmeli miyim?") için Repair and
   Diagnosis yeterli değildir (§2.5). Owner Manual kaynağı yoksa cevap bunu açıkça belirtmeli; teknisyen
   prosedürünü sürücü talimatı gibi sunmamalı.
10. **(v2.1) Tekrarlı içerik.** Yerel arşivde bölünmüş ağaç ve tek sayfa ağacı büyük ölçüde aynı metinleri
    içerir. Ayrıca aynı metin farklı üretim tarihi aralıklarında tekrar eder (§0B, Ek B). Proje crawler'ı
    `Repair and Diagnosis (Single Page)` yolunu dışlar. İndekslemede metin bazlı tekilleştirme yapılırken
    sayfanın tarih aralığı ve varyant koşulu kaybedilmemelidir.

---

## Ek B: Sayım ve ölçüm yöntemi

Sayılar 2026-11-17'de aşağıdaki yöntemle üretildi. Betikler repoya eklenmedi; aynı adımlarla yeniden
üretilebilir.

**B.1 Dosya ve sayfa envanteri**

- **Dosya sayıları:** arşiv kökünün altındaki tüm dosyalar uzantıya göre sayıldı.
  - Toplam 103.661 dosya: `.html` 87.548 (87.544'ü `pages/` altında), `.png` 15.712, `.svg` 234
    (220'si `images/`, 14'ü `icons/`), `.gif` 96, `.jpeg` 68, `.js` 1, `.css` 1, `.txt` 1.
- **Sayfa ağaçları:**
  - Tam ağaç `pages/3.html` içindeki iç içe `<ul>/<li>` listesinden çıkarıldı. Liste kapanmayan `<li>`
    etiketleri içerdiği için ayrıştırma yığın tabanlı yapıldı.
  - Sonuç: 34.609 benzersiz sayfa bağlantısı.
  - Labor ağacı aynı yöntemle `pages/5.html`'den çıkarıldı: 461 sayfa.
- **Sayfa sınıfı:** her sayfa için `<div class="main">` gövdesi alındı; `<script>` ve `<button>` öğeleri
  çıkarıldı, etiketler silindi, boşluklar normalize edildi. Sınıflar:
  - *başka varyant:* gövde Lemon'un `other-warning` uyarı kutusunu içeriyor.
  - *dizin:* gövdede `<ul>` var ve metin 3.000 karakterden kısa.
  - *içerik:* yukarıdakiler değil ve metin 200 karakterden uzun.
  - *kısa:* kalanlar.
- **Tam ağaç dağılımı:** 22.585 içerik + 8.765 dizin + 3.259 kısa = 34.609.
- **Önceki taslakla fark:** v2.1'in ilk taslağındaki "25.854 içerik sayfası" sayısı, içerik ve kısa
  sayfaları birlikte saymış ve butonları çıkarmayan bir normalizasyon kullanmıştı (22.708 + 3.146).
  Bu taslakta yerini yukarıdaki sınıflama aldı.

**B.2 Tekrarların ayıklanması**

- Her sayfanın normalize gövde metninin SHA-256 karması alındı. Breadcrumb başlıkta olduğu için metne
  dahil değildir.
- Sonuçlar:
  - 87.544 sayfada 24.579 benzersiz metin.
  - İçerik sınıfında 11.962 benzersiz metin.
  - Tam ağaçtaki içerik sayfalarında 11.847 benzersiz metin.
  - Tam ağaç dışındaki içerik metinlerinden 115'i tam ağaçta yok.
- **Sınır:** Karma birebir metin eşitliğini yakalar. Küçük farklarla tekrar eden sayfalar ayrı sayılır.

**B.3 Uygunluk sezgisi (%55,9 ve %51,6)**

- **Kapsam:** yalnızca tam ağaçtaki içerik sayfaları.
- **Etiketleme:** her sayfa yol metnine (breadcrumb yolu) göre etiketlendi:
  1. *başka motor/gövde:* yol G16E, GR Model, 2ZR-FXE, HV Model, Hybrid, 2ZR-FAE veya Hatchback içeriyor ve
     M20A içermiyor.
  2. *tarih 2023 öncesi biter:* yoldaki tüm `[AA/YYYY - AA/YYYY]` aralıklarının bitiş yılı < 2023.
  3. *yıl etiketi 2024'ü kapsamaz:* "EARLY 2023", "LATE 2020", "(2019-22)", "(2020-22)".
  4. *çelişki tespit edilmedi:* kalanlar.
- **Sayfa bazında:** 22.585 sayfanın 11.656'sı (%51,6) *çelişki tespit edilmedi* etiketini aldı; 9.493'ü
  tarih, 1.340'ı motor/gövde, 96'sı yıl etiketi nedeniyle elendi.
- **Benzersiz metin bazında:** bir metin, göründüğü yollardan *herhangi birinde* çelişki tespit
  edilmediyse "çelişki tespit edilmedi" sayıldı. Sonuç: 11.847 metnin 6.626'sı (%55,9).
- **Varsayımlar ve sınırlar:**
  - 2024 model yılı LE'nin üretiminin 2023'ten önce başlamadığı varsayıldı. Bu, araştırmada
    doğrulanmadı.
  - 2023 içinde biten aralıklar (ör. [11/2022 - 03/2023]) da "çelişki tespit edilmedi" sayıldı; bu oranı
    yükseltebilir.
  - Fabrika (TMC/TMMMS) ve donanım (EPB, ekran tipi, TPMS tipi) koşulları kontrol edilmedi.
  - Bu nedenle oran, uygunluğun doğrulandığını göstermez; yalnızca yol metninde açık çelişki
    bulunmadığını gösterir.

**B.4 Diğer sayımlar**

- **Başka varyant sayfaları:** `other-warning` sınıfıyla sayıldı (iki ağaçta 8.179'ar ve Labor ağacında 461;
  ayrıca iç bağlantıyla erişilen 1 Labor sayfası).
- **`external-car.html` bağlantıları:** sayfa gövdesinde bu dizenin geçiş sayısıyla sayıldı.
- **Tam metin aramaları** (N05, N27, N43, MIL yanıp sönmesi, hararet, yakıt sızıntısı): normalize gövde
  metni üzerinde düzenli ifadeyle yapıldı. Doğruluğu, mevcut olduğu bilinen bir kontrol terimiyle
  ("catalyst system efficiency") test edildi. İlk denemede kabuk (shell) tabanlı bir arama hatalı biçimde
  sıfır sonuç verdi; sonuçlar Python ile yeniden üretildi.

**B.5 Kod ölçümü**

Yöntem, girdiler ve commit §2.4'tedir. Beklenen davranış etiketleri §2.2 özet tablosundadır.

---

## Kaynaklar

- [CAR-6 v1 raporu](user-question-research.md) ve [soru veri seti](../data/examples/corolla-2024-user-questions.json)
- [Graph katmanı](graph.md), [entity extraction](entity-extraction.md), [mimari](architecture.md), [proje rehberi](project-guide.md)
- Kod: `caragent/models.py` (taksonomi ve sınıflayıcı), `caragent/rag.py` (takip sorusu ve evidence_guard),
  `caragent/entity_extractor.py` (entity ve ilişki türleri)
- [Toyota 2024 Corolla dijital kılavuzları (US)](https://www.toyota.com/owners/warranty-owners-manuals/digital/corolla/2024/)
- [Toyota bakım planı (US)](https://www.toyota.com/owners/maintenance-schedule)
- [NHTSA recall sorgulama](https://www.nhtsa.gov/recalls)
- [NHTSA/Toyota 2023–2024 Corolla direksiyon geri çağırma bildirimi](https://static.nhtsa.gov/odi/rcl/2024/RCMN-24V878-1714.pdf)
- [Transport Canada recall veritabanı](https://tc.canada.ca/en/road-transportation/defects-recalls-vehicles-tires-child-car-seats)
- [AB Genel Güvenlik Yönetmeliği (EU) 2019/2144 (GSR2)](https://eur-lex.europa.eu/eli/reg/2019/2144/oj)
- **Yerel Lemon arşivi (v2.1):** `data/external/lemon-corolla-2024/2024 Toyota Corolla LE/`. Kullanıcının
  indirdiği çevrimdışı kopyadır; Git'te yoktur. Atıflar §2.5 ve §2.7'de sayfa yolu ve bölüm yoluyla
  verilmiştir. Özgün alt sayfa URL'leri arşivde bulunmadığı için verilmedi.

**Kullanıcı ihtiyacı sinyali (v2.1, §2.6).** Bu kaynaklar teknik doğruluk için değil, talep sinyali için
kullanıldı:

- [2024 Toyota Corolla 2.0 engine oil capacity? (Bob Is The Oil Guy)](https://bobistheoilguy.com/forums/threads/2024-toyota-corolla-2-0-engine-oil-capacity.389133/)
- [New 2023 Corolla and 0W-8 oil (Bob Is The Oil Guy)](https://bobistheoilguy.com/forums/threads/new-2023-corolla-and-0w-8-oil.369592/page-2)
- [2024 Corolla hava yastığı şikâyetleri (CarComplaints)](https://carcomplaints.com/Toyota/Corolla/2024/seat_belts_air_bags/air_bags.shtml)
- [2023 Corolla hava yastığı şikâyetleri (CarComplaints)](https://carcomplaints.com/Toyota/Corolla/2023/seat_belts_air_bags/air_bags.shtml)
- [NHTSA 23V480 recall bildirimi](https://static.nhtsa.gov/odi/rcl/2023/RCMN-23V480-2200.pdf)
- [P0171 System to lean bank 1 (Toyota Owners Club, eski model yılı Corolla)](https://toyotaownersclub.com/forums/topic/9206-p0171-system-to-lean-bank-1/page/2)
- [Retorquing wheel lug nuts on a brand new vehicle (Toyota Owners Club)](https://us.toyotaownersclub.com/forums/topic/13842-retorquing-wheel-lug-nuts-on-a-brand-new-vehicle/)
- [Tire pressure sensor sorusu (2CarPros)](https://2carpros.com/questions/tire-pressure-sensor-id2-and-1d4-location--1701439)
- [2023 1.5 MDS Corolla motor yağı (Donanımhaber)](https://forum.donanimhaber.com/2023-1-5-mds-corolla-motor-yagi--159293684)
- [Corolla 1.5 EPB uyarı lambası şikâyeti (Şikâyetvar)](https://www.sikayetvar.com/en/toyota-us/toyota-corolla-15-dream-x-pack-multidrive-s-epb-error-light-on)
- [Corolla 1.5 soğutma sıvısı uyarısı şikâyeti (Şikâyetvar)](https://www.sikayetvar.com/en/toyota-us/toyota-corolla-15-flame-x-coolant-warning-and-warranty-problem)
