# CAR-6 — 2024 Toyota Corolla LE kullanıcı soru araştırması

## Sonuç

2024 Corolla LE için en çok tekrar eden soru kümeleri bakım aralığı ve motor yağı,
lastik basıncı/TPMS, telefon–multimedya bağlantısı, uzaktan çalıştırmanın donanıma bağlı
olması, sürüş destek uyarıları ve gerçek yakıt tüketimidir. Güvenlik etkisi nedeniyle uyarı
ışıkları, fren/lastik, geri çağırma ve kritik sıvı soruları kullanıcı hacminden bağımsız olarak
en yüksek önceliktedir.

Araştırmanın makinece okunabilir çıktısı
[`data/examples/corolla-2024-user-questions.json`](../data/examples/corolla-2024-user-questions.json)
dosyasındadır. Dosya 44 bağımsız soru ve ayrıca 12 bağlama bağımlı takip sorusu içerir.

## Yöntem ve sınırlar

Bu çalışma özel Google arama hacmi veya Toyota çağrı merkezi verisine erişmez. “En çok sorulan”
ifadesi şu sinyallerin birleşimi olarak kullanılmıştır:

1. 2024 Corolla/LE sahip topluluklarında aynı niyetin tekrarlanması,
2. Toyota'nın 2024 Corolla kılavuzunda ayrı işlem veya açıklama olarak yer alması,
3. sahiplik araştırmalarında bildirilen tekrar eden sorun alanları,
4. yanlış cevaplandığında güvenlik, yolda kalma veya hasar riski.

Bu nedenle sonuç bir **nitel önceliklendirme** çalışmasıdır; kesin soru adedi veya pazar payı
ölçümü değildir. Lemon veri setinin pazarı belirtilmediğinden cevap üretirken pazar, VIN,
motor, hibrit/gasoline ayrımı, gövde tipi ve opsiyon paketi doğrulanmalıdır.

## Önceliklendirilmiş kategoriler

| Sıra | Kategori | Öncelik | Beklenen sıklık | Gerekçe |
|---:|---|---|---|---|
| 1 | Bakım ve sıvılar | P0 | Çok yüksek | 5K/10K aralığı, yağ ve 30K bakım soruları tekrar ediyor |
| 2 | Lastikler ve frenler | P0 | Yüksek | PSI, TPMS ve yedek lastik donanım farkı sık karıştırılıyor |
| 3 | Uyarılar ve arıza belirtileri | P0 | Yüksek | Aciliyet ve güvenli kullanım kararı gerekiyor |
| 4 | Güvenlik ve geri çağırmalar | P0 | Orta | Daha az sıklıkta fakat en yüksek zarar potansiyeli |
| 5 | Multimedya ve telefon | P1 | Yüksek | Eşleşmeme, siyah ekran ve CarPlay/Android Auto tekrar ediyor |
| 6 | Anahtar ve uzaktan erişim | P1 | Yüksek | LE paketleri ve abonelik koşulları farklı |
| 7 | Sürüş desteği | P1 | Yüksek | PCS/LTA/DRCC davranışı ve sensör koşulları anlaşılmıyor |
| 8 | Yakıt ekonomisi ve aktarma | P1 | Orta | Düşük MPG, CVT davranışı ve soğuk kullanım öne çıkıyor |
| 9 | Donanım ve genel kullanım | P2 | Orta | Konfor ve aksesuar soruları daha düşük riskli |

P0 güvenlik/hasar/yolda kalma etkisini, P1 sık tekrarlanan kullanım ihtiyacını, P2 ise düşük
riskli kolaylık ve donanım bilgisini ifade eder.

## En güçlü kullanım senaryoları

### 1. Bakım karar desteği

Kullanıcı kilometreyi, süreyi ve kullanım koşulunu verir; sistem doğru kılavuz bölümünü bulur,
normal/ağır kullanım ayrımını belirtir ve işlem ile kontrolü birbirinden ayırır. “5.000 mi mi,
10.000 mi?” ve “30K paketinin hangileri gerekli?” ana örneklerdir.

### 2. Uyarı triyajı

Kullanıcı uyarı metnini veya belirtiyi aktarır. Sistem bunu bakım hatırlatıcısı, kısa sürede servis
gerektiren durum veya güvenli biçimde durmayı gerektiren durum olarak sınıflandırır; teşhis iddiası
yerine kılavuzdaki eylemi ve kaynağı gösterir.

### 3. Donanım ve varyant çözümleme

Uzaktan çalıştırma, Smart Key, yedek lastik, TPMS görünümü ve sürüş destek özelliklerinde yalnız
“2024 Corolla LE” yeterli değildir. Pazar, benzinli/hibrit, gövde, paket ve gerektiğinde VIN
istenmelidir.

### 4. Adım adım özellik kullanımı

CarPlay/Android Auto eşleştirme, DRCC takip mesafesi, LTA ayarı, ekran modu ve bakım sıfırlama
gibi sorular kısa ve sıralı prosedür ile yanıtlanmalıdır. Takip sorusu önceki sistem ve varyantı
korumalıdır.

### 5. Kaynaklı güvenlik ve geri çağırma

Geri çağırma uygunluğu yalnız model adına göre kesinleştirilmemeli; VIN kontrolüne yönlendirilmelidir.
Kritik uyarılarda cevap, kaynak kılavuz ve resmi kampanya kaydıyla sınırlandırılmalıdır.

## Tek soru ve takip sorusu davranışı

Bağımsız sorular araç/sistem niyetini kendi içinde taşır: “2024 Corolla LE lastikleri soğukken kaç
PSI olmalı?” gibi. Takip soruları ise önceki konuyu zamir veya eksik nesneyle sürdürür: “Peki sıcak
lastikte farklıysa hava indirmeli miyim?” gibi. Veri setindeki `parent_id`, takip sorusunun hangi
bağımsız soruya bağlı olduğunu gösterir.

RAG değerlendirmesinde bağımsız sorular doğrudan kullanılabilir. Takip soruları önce parent soru,
sonra takip sorusu olarak iki turlu test edilmelidir. Önceki model cevabı kaynak kabul edilmemeli;
takip turunda kaynaklar yeniden getirilmelidir.

## Model, yıl ve sistem değişkenleri

- **Benzinli/hibrit:** güç aktarma, sıvılar, yakıt ekonomisi ve yedek lastik alanını değiştirir.
- **LE paketleri:** fiziksel anahtar/Smart Key, push-button start ve Remote Connect değişebilir.
- **Pazar:** bağlı servisler, ölçü birimleri, mevzuat ve bakım kılavuzu farklı olabilir.
- **Gövde ve jant:** yedek lastik, lastik etiketi ve bazı donanımlar değişebilir.
- **Üretim/VIN:** geri çağırma ve kampanya uygunluğunu belirler.
- **Telefon/yazılım:** multimedya sorunlarının araç dışı değişkenleridir.
- **Sensör koşulları:** yağmur, kar, kir, kamera/radar hizası sürüş desteğini etkiler.

Bu alanlar `variant_sensitive=true` sorularda cevap öncesi netleştirme veya kaynak filtresi olarak
kullanılmalıdır.

## Graph modelleme çalışmasına aktarılacak sinyaller

CAR-6 graph tasarımı yapmaz. Sonraki çalışma için yalnız ihtiyaçları kaydeder:

- Soru niyeti (`intent`) ile araç sistemi (`system`) ayrı kavramlardır.
- Bir cevap; araç/yıl/pazar/paket koşulu, kılavuz kanıtı ve güvenlik seviyesi taşımalıdır.
- Uyarı, bakım eylemi, teknik değer ve parça aynı soruda birlikte gerekebilir.
- Takip sorusu parent niyetini ve araç bağlamını korumalıdır.
- VIN'e bağlı bilgi için graph sonucu kesin uygunluk iddiasında bulunmamalıdır.

## Kaynaklar

- [Toyota 2024 Corolla dijital kullanım ve multimedya kılavuzları](https://www.toyota.com/owners/warranty-owners-manuals/digital/corolla/2024/)
- [Toyota bakım planı](https://www.toyota.com/owners/maintenance-schedule)
- [Toyota kablosuz Apple CarPlay işlemi](https://www.toyota.com/owners/warranty-owners-manuals/digital/article/corolla/2024/om12s17u/zsj1683336213616/)
- [Toyota elektronik anahtar pili açıklaması](https://www.toyota.com/owners/warranty-owners-manuals/digital/article/corolla/2024/om02684u/ch06se030409/)
- [Toyota Road Sign Assist açıklaması](https://www.toyota.com/owners/warranty-owners-manuals/digital/article/corolla/2024/om02684u/ch04se050407/)
- [NHTSA/Toyota 2023–2024 Corolla direksiyon geri çağırma bildirimi](https://static.nhtsa.gov/odi/rcl/2024/RCMN-24V878-1714.pdf)
- [2024 Corolla LE bakım aralığı sahibi sorusu](https://www.reddit.com/r/COROLLA/comments/1cgju0c/)
- [2024 Corolla LE bakım mesajı ve yağ sorusu](https://www.reddit.com/r/COROLLA/comments/1eo1f9r/)
- [2024 Corolla LE Remote Connect/paket sorusu](https://www.reddit.com/r/COROLLA/comments/1dioqfc/)
- [2024 Corolla LE uzaktan çalıştırma donanımı sorusu](https://www.reddit.com/r/COROLLA/comments/1g5tv74/)
- [2024 Corolla LE yedek lastik sorusu](https://www.reddit.com/r/COROLLA/comments/18ct0i4/)
- [Consumer Reports 2024 Corolla sahip bildirimleri](https://www.consumerreports.org/cars/toyota/corolla/2024/reliability/)

Kaynaklardaki forum yanıtları teknik gerçek olarak değil, hangi soruların tekrarlandığını belirleyen
talep sinyali olarak kullanılmıştır. Teknik cevaplar resmi kılavuz, VIN ve güvenlik kaydıyla
doğrulanmalıdır.
