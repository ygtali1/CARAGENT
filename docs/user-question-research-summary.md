# CAR-6 Özet Raporu: Kullanıcılar Araçları Hakkında Neler Soruyor?

> **Araç:** 2024 Toyota Corolla LE (2.0 L benzinli, ABD pazarı referans alınmıştır)
> **Ayrıntılar:** Bu belge, [teknik araştırma raporunun](user-question-research-v2.md) sade bir özetidir.
> Sayımlar, yöntemler ve kaynak sayfası atıfları teknik rapordadır.

## 1. Araştırmanın amacı

Bu araştırmanın amacı, bir araç asistanına kullanıcıların neler sorabileceğini ortaya çıkarmaktır.
Araştırma üç soruya cevap arar:

- Hangi sorular güvenlik veya maliyet açısından daha önemlidir?
- Bir soruya doğru cevap verebilmek için aracın hangi bilgilerinin bilinmesi gerekir?
- Elimizdeki kaynaklar bu soruların hangilerini destekler?

Araştırma kod veya veri modeli geliştirmez. Sonraki aşamada sistemi tasarlayacak ekibe, kullanıcı
ihtiyaçlarını gösteren bir girdi hazırlar.

## 2. Soru kategorileri ve örnek sorular

Aşağıdaki sorular üç farklı yoldan geldi. Her sorunun sonunda kökeni belirtilmiştir:

- *[kullanıcı]* İlk CAR-6 çalışmasındaki kullanıcı ihtiyacı örneklerinden seçildi; her soru için ayrı
  forum kaydı doğrulanmadı.
- *[senaryo]* Araştırmacı tarafından, eksik kalan durumları test etmek için tasarlandı. Bu sorular
  gerçek kullanıcılardan toplanmadı.
- *[kılavuz]* İncelenen teknik servis kılavuzunun içeriğinden türetildi.

Bu liste, "en sık sorulan sorular" listesi değildir. Soruların ne sıklıkla sorulduğu ölçülmedi.

### 2.1 Uyarı ışıkları ve acil durumlar

Sürücünün o anda "aracı kullanmaya devam etmeli miyim?" kararını vermesi gereken durumlar.

1. Motor arıza lambası (check engine) yanarsa aracı kullanmaya devam edebilir miyim? *[kullanıcı]*
2. Motor arıza lambası yanıp sönüyorsa aracı hemen durdurmalı mıyım? *[senaryo]*
3. Motor hararet yaparsa, yani sıcaklık göstergesi kırmızıya çıkarsa ne yapmalıyım? *[senaryo]*
4. Yağ basıncı uyarı ışığı yanarsa motoru kapatmalı mıyım? *[senaryo]*
5. Fren uyarı ışığı yanıyor ve pedal boşa gidiyorsa araç kullanılabilir mi? *[senaryo]*
6. Hava yastığı uyarı ışığı yanıyorsa araç kullanılmalı mı? *[kullanıcı]*
7. Direksiyon aniden ağırlaşırsa güvenli şekilde ne yapmalıyım? *[kullanıcı]*
8. Yakıt kokusu alıyorsam ya da aracın altında sızıntı görürsem ne yapmalıyım? *[senaryo]*

### 2.2 Bakım ve sıvılar

Periyodik bakım, motor yağı ve diğer sıvılarla ilgili sorular.

1. Bakım 5.000 milde mi, 10.000 milde mi yapılmalı? *[kullanıcı]*
2. Aracımda hangi motor yağı kullanılmalı, ne zaman değiştirilmeli? *[kullanıcı]*
3. Yağ filtresi değişimi dahil motor kaç litre yağ alır? *[senaryo]*
4. Önerilen yağı bulamazsam başka bir yağ kullanabilir miyim, sonra ne yapmalıyım? *[kılavuz]*
5. Aynı model yıldaki araçlarda üretim tarihine göre motor yağı miktarı değişebilir mi? *[kılavuz]*
6. Şanzıman yağı ne zaman kontrol edilmeli veya değiştirilmeli? Bu araçta CVT, yani sürekli değişken
   şanzıman kullanılıyor. *[kullanıcı]*
7. Fren hidroliği ve motor soğutma sıvısı ne zaman kontrol edilmeli? *[kullanıcı]*
8. Bakım gerekli uyarısı yağ değişiminden sonra nasıl sıfırlanır? *[kullanıcı]*

### 2.3 Lastikler ve frenler

1. Lastik basıncı soğukken kaç olmalı? *[kullanıcı]*
2. Lastik basıncı uyarısı neden yanıyor, uyarı sönmüyorsa ne kontrol etmeliyim? *[kullanıcı]*
3. Aracımda yedek lastik mi var, yoksa lastik tamir kiti mi? *[kullanıcı]*
4. Tekerlek bijonları ne kadar sıkılmalı ve hangi sırayla sıkılmalı? *[senaryo]*
5. Lastikleri değiştirince lastik basıncı sensörlerinin araca yeniden tanıtılması gerekir mi? *[senaryo]*
6. Ön fren diskinin en az kalınlık değeri nedir? *[senaryo]*

### 2.4 Arıza kodları ve servis işlemleri

Arıza kodu, aracın bilgisayarının bir sorunu kaydettiğinde verdiği koddur (örneğin "P0171"). Bu sorular
çoğunlukla servis veya teknik bilgisi olan kullanıcılardan gelir.

1. P0171 arıza kodu ne anlama gelir, hangi parçalar kontrol edilmelidir? *[senaryo]*
2. P0420 arıza koduyla araç kullanmak motora zarar verir mi? *[senaryo]*
3. Akü değiştirildikten sonra hangi sistemlerin yeniden ayarlanması gerekir? *[senaryo]*
4. Gaz kelebeği temizlendikten sonra motorun rölantiyi yeniden öğrenmesi gerekir mi? *[senaryo]*
5. Ön fren balatası değişimi standart olarak kaç saat işçilik gerektirir? *[senaryo]*

### 2.5 Güvenlik ve geri çağırmalar

Geri çağırma (recall), üreticinin bir güvenlik sorunu nedeniyle belirli araçları ücretsiz onarıma
çağırmasıdır.

1. Aracımda açık bir geri çağırma olup olmadığını şasi numarasıyla (VIN) nasıl kontrol ederim? *[kullanıcı]*
2. Corolla için duyurulan direksiyon geri çağırması benim aracıma uygulanıyor mu? *[kullanıcı]*
3. Türkiye'de geri çağırma bilgisi nasıl sorgulanır? *[senaryo]*

### 2.6 Sürüş destek sistemleri

Çarpışma önleme, şerit takip ve radarlı hız sabitleyici gibi sürücüye yardım eden sistemler.

1. Çarpışma önleme sistemi veya şerit takip "kullanılamıyor" mesajı neden çıkar? *[kullanıcı]*
2. Radarlı hız sabitleyici nasıl ayarlanır, öndeki araçla takip mesafesi nasıl değiştirilir? *[kullanıcı]*
3. Çarpışma önleme sistemi gereksiz yere fren yaparsa ne yapmalıyım? *[senaryo]*

### 2.7 Multimedya, anahtar ve uzaktan erişim

1. Kablosuz Apple CarPlay araca nasıl bağlanır? *[kullanıcı]*
2. Telefon bağlanmıyor veya ekran kararıyorsa sistemi nasıl yeniden başlatabilirim? *[kullanıcı]*
3. Benim aracımda uzaktan çalıştırma özelliği var mı? *[kullanıcı]*
4. Anahtar kumandasının pili nasıl değiştirilir? *[kullanıcı]*

### 2.8 Pazar ve donanım farkları

Aynı model farklı ülkelerde farklı motor, donanım ve kurallarla satılabilir.

1. Türkiye'deki 1.5 benzinli Corolla ile ABD'deki 2.0 Corolla aynı bakım planını mı kullanır? *[senaryo]*
2. Avrupa'da 95 oktan, ABD'de 87 oktan önerilmesi aynı yakıt anlamına mı gelir? *[senaryo]*
3. Benim aracımın donanımında koltuk ısıtma var mı? *[senaryo]*

### 2.9 Yakıt tüketimi ve sürüş

1. Şehir içinde yakıt tüketimi beklenenden yüksekse neleri kontrol etmeliyim? *[kullanıcı]*
2. Hızlanırken motorun sabit yüksek devirde kalması normal mi? *[kullanıcı]*

## 3. Hangi sorulara önce odaklanmalıyız?

Bu sıralama, yanlış bir cevabın kullanıcıya verebileceği zarara göre yapıldı. Soruların ne sıklıkla
sorulduğu ölçülmediği için sıralama soru sıklığına **dayanmaz**. Mevcut sistemin kendi önceliklendirmesi
bazı sorularda bu öneriden farklıdır; ayrıntısı teknik raporda yer alır.

| Grup | Örnek konular | Neden önce? |
|---|---|---|
| **1. Güvenlik açısından kritik** | Uyarı ışıklarında "araç kullanılabilir mi?" kararı; fren, direksiyon ve hava yastığı uyarıları; hararet; yakıt sızıntısı; geri çağırmalar; bijon ve fren parçalarının sıkma değerleri; çarpışma önleme sisteminin beklenmedik frenlemesi | Yanlış cevap kazaya, yaralanmaya veya yangına yol açabilir |
| **2. Bakım ve günlük kullanım açısından önemli** | Motor yağı türü ve miktarı, şanzıman ve soğutma sıvısı, arıza kodlarının anlamı, akü veya lastik değişiminden sonra yapılacak ayarlar, ülkeye göre yakıt ve yağ farkı | Yanlış cevap motor veya şanzıman hasarına, gereksiz masrafa ya da yanlış servise yol açabilir |
| **3. Konfor ve bilgi amaçlı** | Multimedya ve telefon bağlantısı, koltuk ısıtma gibi donanımlar, ekran ayarları, işçilik süreleri | Yanlış cevabın zararı düşüktür; yine de kullanıcı memnuniyeti için önemlidir |

**Not:** Bir sorunun bu araç için geçerli olup olmaması ile ne kadar riskli olduğu ayrı konulardır.
Örneğin hibrit sistem uyarısı benzinli Corolla LE'de bulunmaz. Ancak hibrit araç kullanan biri için
güvenlik açısından kritiktir. Sistem bu durumda soruyu önemsiz saymamalı; sorunun bu araç için geçerli
olmadığını açıkça söylemelidir.

## 4. Takip sorusu örnekleri

Kullanıcılar çoğu zaman tek soru sormaz. Kısa takip sorularıyla konuşmayı sürdürür. Aşağıdaki örnekler
teknik rapordaki tasarlanmış konuşma senaryolarından seçildi. Sistem cevapları yazılmamıştır; yalnızca
beklenen davranış gösterilmiştir.

**Örnek 1: Bağlamı sürdürme**

| Kullanıcı | Beklenen davranış |
|---|---|
| Lastik basıncı soğukken kaç olmalı? | Lastik basıncı sorusu olarak anlaşılmalı |
| Kışın? | Hâlâ lastik basıncından söz edildiği anlaşılmalı |
| Peki stepnede de aynı değer mi? | Konu yine lastik basıncı; önceki "Kışın?" sorusu değil, ilk soru esas alınmalı |

**Örnek 2: Bağlamı sürdürme ve güvenlik sorusuna geçiş**

| Kullanıcı | Beklenen davranış |
|---|---|
| P0171 arıza kodu ne anlama geliyor? | Arıza kodu sorusu olarak anlaşılmalı |
| Bunu nasıl kontrol ederim? | "Bunu" ifadesinin arıza kodunu kastettiği anlaşılmalı |
| Motor arıza lambası yanıp sönüyor, sürebilir miyim? | Soru artık güvenlik sorusu; önce aracın kullanılıp kullanılamayacağı ele alınmalı, önceki arıza kodu bilgisi de hatırlanmalı |

**Örnek 3: Konu değiştirme ve önceki konuya dönme**

| Kullanıcı | Beklenen davranış |
|---|---|
| CarPlay nasıl bağlanır? | Telefon bağlantısı sorusu |
| Tamam. Bu arada yağ değişimi kaç km'de bir? | Yeni konu; CarPlay bilgisi bu soruya taşınmamalı |
| Telefonum yine de bağlanmazsa? | Kullanıcı ilk konuya döndü; telefon bağlantısı sorusu olarak anlaşılmalı |

**Örnek 4: Araç bilgisini sonradan belirtme**

| Kullanıcı | Beklenen davranış |
|---|---|
| Uzaktan çalıştırma bende var mı? | Donanıma bağlı bir soru; araç bilgisi eksikse sorulmalı |
| Aracım Türkiye'de satılmış, 1.5 benzinli. | Bu bilgi konuşma boyunca hatırlanmalı |
| O zaman uygulamadan klimayı açabilir miyim? | Türkiye ve 1.5 benzinli araç bilgisi korunmalı; uygun kaynak yoksa bu eksiklik açıklanmalı |

**Örnek 5: Başka bir model yılına geçiş**

| Kullanıcı | Beklenen davranış |
|---|---|
| 2024 Corolla bakım aralığı nedir? | Bakım aralığı sorusu |
| 2020 modelde de aynı mı? | Kullanıcı başka bir model yılını soruyor; seçili araç 2024 olduğu için bu fark açıkça belirtilmeli, gerekirse araç seçimi değiştirilmeli |
| Hibritte? | Konu hâlâ bakım aralığı; hibrit modelin farklı olabileceği belirtilmeli |

## 5. Doğru cevap için hangi araç bilgileri gerekir?

Aynı soru, farklı araçlar için farklı doğru cevaplara sahip olabilir. Aşağıdaki bilgilerin **hepsi her
soruda istenmez**. Örneğin CarPlay bağlantısı için motor bilgisi gerekmez. Yağ miktarı içinse motor ve
üretim tarihi önemli olabilir.

| Araç bilgisi | Ne zaman gerekir? | Örnek |
|---|---|---|
| Model ve model yılı | Hemen her soruda başlangıç noktasıdır | 2024 Corolla ile 2020 Corolla'nın bakım bilgileri farklı olabilir |
| Motor ve güç aktarma (benzinli/hibrit) | Yağ, sıvı, arıza kodu ve bakım sorularında | Benzinli ve hibrit Corolla farklı sistemler kullanır |
| Pazar (satıldığı ülke) | Bakım planı, yakıt, birimler ve bağlı servislerde | Türkiye'deki ve ABD'deki Corolla farklı motorlarla satılır |
| Donanım ve paket | Özelliğin araçta olup olmadığını soran sorularda | Uzaktan çalıştırma, koltuk ısıtma, park freni tipi |
| Üretim tarihi | Gerektiğinde, aynı model yılında değer değiştiğinde | İncelenen kılavuzda motor yağı türü ve miktarı üretim tarihine göre değişiyor |
| Şasi numarası (VIN) | Geri çağırma ve kesin donanım sorularında | Geri çağırmanın araca uygulanıp uygulanmadığı VIN ile anlaşılır |

## 6. Mevcut kaynak hangi soruları destekliyor?

Araştırmada temel kaynak olarak, projenin kullandığı Lemon Manuals sitesinden indirilen 2024 Corolla LE
teknik servis kılavuzunun yerel kopyası incelendi. Bu kılavuzun hepsi okunmadı; her soru için ilgili
bölümlerden örnek sayfalar okundu.

| Soru türü | Durum |
|---|---|
| Arıza kodlarının anlamı ve teşhis adımları; sıkma değerleri ve parça limitleri; sıvı türleri ve miktarları; servis ve ayar işlemleri | **Teknik servis kılavuzu destekliyor.** Ancak cevap yine aracın üretim tarihi, motoru ve donanımıyla doğrulanmalıdır |
| "Aracı kullanmaya devam etmeli miyim?" gibi sürücü kararları; bakım aralıkları; akü takviyesi, ekran ayarları gibi günlük kullanım; Türkiye ve Avrupa pazarına özel bilgiler | **İncelenen içerikte bulunamadı.** Bu sorular için kullanım kılavuzu, bakım planı veya ilgili ülkenin belgeleri gerekir |
| İşçilik süreleri ve geri çağırma kayıtları | **Kılavuzda yalnızca başka bir varyant (Corolla Hybrid LE) için var.** Bu bilgiler benzinli Corolla LE için kullanılamaz |
| Hibrit sisteme özgü sorular | **Benzinli Corolla LE için geçerli değil.** Hibrit araç seçildiğinde ayrıca ele alınmalıdır |

**Önemli ayrım:** "İncelenen içerikte bulunamadı" ifadesi, bilginin hiçbir kaynakta olmadığı anlamına
gelmez. Yalnızca incelenen kılavuz sayfalarında bulunmadığını gösterir.

## 7. Araştırmadan çıkan temel ihtiyaçlar

1. **Güvenlik sorularında kullanıcı önce bir karar bekliyor.** "Aracı kullanabilir miyim?" sorusu teknik
   teşhisten önce gelir. Teknik servis kılavuzu bu kararı tek başına karşılamaz.
2. **Doğru cevap aracın kimliğine bağlıdır.** Model yılı tek başına yeterli olmayabilir. Gerektiğinde
   motor, pazar, donanım ve üretim tarihi bilinmeli; bilinmiyorsa kullanıcıya sorulmalı ya da cevabın
   hangi araç için geçerli olduğu belirtilmelidir.
3. **Kullanıcılar kısa takip sorularıyla konuşur.** Sistem önceki konuyu ve kullanıcının verdiği araç
   bilgisini hatırlamalı, konu değiştiğinde ise eski konuyu yeni soruya taşımamalıdır.
4. **Başka araca ait bilgi, seçili araç bilgisi gibi sunulmamalıdır.** Bu özellikle geri çağırma ve
   işçilik bilgilerinde önemlidir. Geri çağırmalarda kesin sonuç için kullanıcı şasi numarası (VIN)
   sorgusuna yönlendirilmelidir.
5. **Türkiye'deki kullanıcılar için kaynak eksik.** İncelenen kılavuz ABD/Kanada odaklı. Türkiye'de satılan
   Corolla'nın motoru, bakım planı ve yakıt bilgisi için ayrı kaynak gerekir.

## 8. Kaynaklar

- [CAR-6 teknik araştırma raporu (v2)](user-question-research-v2.md): yöntem, sayımlar, kaynak sayfası
  atıfları ve tüm soru listesi
- [İlk CAR-6 araştırma raporu (v1)](user-question-research.md): kullanıcı kaynaklı sorular
- Lemon Manuals, 2024 Toyota Corolla LE teknik servis kılavuzu: araştırma için indirilen yerel kopya;
  projeye eklenmedi
- [Toyota 2024 Corolla kullanım kılavuzları (ABD)](https://www.toyota.com/owners/warranty-owners-manuals/digital/corolla/2024/)
- [Toyota bakım planı (ABD)](https://www.toyota.com/owners/maintenance-schedule)
- [NHTSA geri çağırma sorgulama](https://www.nhtsa.gov/recalls)
- Kullanıcı ihtiyacına örnek forum ve şikâyet kaynakları:
  - [2024 Corolla motor yağı kapasitesi tartışması (Bob Is The Oil Guy)](https://bobistheoilguy.com/forums/threads/2024-toyota-corolla-2-0-engine-oil-capacity.389133/)
  - [2024 Corolla hava yastığı şikâyetleri (CarComplaints)](https://carcomplaints.com/Toyota/Corolla/2024/seat_belts_air_bags/air_bags.shtml)
  - [2023 Corolla 1.5 motor yağı tartışması (Donanımhaber)](https://forum.donanimhaber.com/2023-1-5-mds-corolla-motor-yagi--159293684)
