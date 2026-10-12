# Chunklama ve veri modelleri

CARAGENT, her kılavuzu `Vehicle → Manual → Page → Chunk` sırasıyla temsil eder. `Vehicle`, `Manual` ve `Page` oluşturulurken zorunlu alanlar doğrulanır, metin alanları normalize edilir ve sayfalar numaralarına göre deterministik olarak sıralanır. Boş sayfa, tekrar eden sayfa numarası, Toyota dışı marka veya geçersiz model yılı kontrollü bir hata üretir.

## Varsayılan ayarlar

Varsayılan chunk profili:

| Parametre | Değer |
|---|---:|
| Yöntem | `character` |
| Chunk boyutu | 1000 karakter |
| Overlap | 150 karakter |

Boyut ve overlap CLI üzerinden değiştirilebilir:

```powershell
.\.venv\Scripts\python.exe main.py ingest data/processed/toyota-lemon.json `
  --chunk-strategy character `
  --chunk-size 1000 `
  --chunk-overlap 150
```

`character`, `token` ve `paragraph` yöntemleri desteklenir. Minimum boyutlar sırasıyla 100 karakter, 20 token ve 1 paragraftır. `chunk-overlap` negatif olamaz ve chunk boyutundan küçük olmalıdır.

## Bölme davranışı

Algoritma hiçbir chunk'ı iki farklı sayfaya yaymaz. Varsayılan `character` yöntemi boyut sınırına yaklaşırken sırayla şu sınırları tercih eder:

1. Paragraf sonu
2. Satır sonu
3. Cümle sonu
4. Kelime sonu
5. Zorunlu karakter sınırı

Kısa büyük-harfli başlıklar, Markdown başlıkları ve iki nokta ile biten başlıklar mümkün olduğunda sonraki paragrafla birlikte tutulur. Numaralı işlem adımlarındaki `1.` gibi işaretler cümle sonu kabul edilmez. Arka arkaya tekrar eden aynı çıkarım satırları temizlenir; Türkçe ve İngilizce Unicode metinleri korunur.

## Kaynak izlenebilirliği

Her `Chunk` aşağıdaki alanları taşır:

- Deterministik chunk kimliği ve sıra numarası
- Kılavuz ve sayfa kimliği
- Sayfa numarası ve sayfa içi sıra
- Başlık ve kaynak URL
- Araç kimliği, modeli ve model yılı
- CAR-6 soru kategorileri (`question_categories`)
- İlgili araç alt sistemleri (`systems`)
- Soru önceliği (`P0`, `P1` veya `P2`)

Aynı girdi ve ayarlar aynı chunk metinlerini, sırasını, sınıflandırmasını ve kimliklerini üretir.
Chunk imzası `question-aware-v5` sürümünü içerir; böylece eski sınıflandırma ve kategorisiz chunk'lar yeni
extraction kanıtlarıyla yanlışlıkla eşleşmez. Ayar veya sınıflandırma sürümü değiştiğinde chunk
kimlikleri ve kılavuzun ingest içerik özeti de değişir.

## Soru odaklı zenginleştirme

CAR-6 araştırmasından gelen dokuz soru kümesi şunlardır: bakım/sıvılar, uyarılar/arıza
belirtileri, güvenlik/geri çağırmalar, lastik/fren, sürüş desteği, multimedya/telefon,
anahtar/uzaktan erişim, yakıt/aktarma ve genel sahiplik. Sınıflandırıcı başlık ve chunk
metnindeki açık anahtar sözcükleri kullanır. Bir chunk birden çok kategori ve sistem taşıyabilir.

Bu metadata retrieval önceliklendirmesi içindir; bir neden-sonuç, arıza teşhisi veya araç
uyumluluğu iddiası üretmez. Teknik iddialar yine kaynak alıntılı entity/relationship extraction
tarafından doğrulanır.

## Boyut karşılaştırması

| Profil | Örnek ayar | Etki |
|---|---|---|
| Küçük | `500 / 75` | Daha hassas eşleşme, daha fazla chunk ve indeks maliyeti |
| Dengeli | `1000 / 150` | Varsayılan; bağlam ve indeks maliyeti arasında denge |
| Büyük | `1600 / 200` | Daha geniş bağlam, daha az chunk; ilgisiz metin taşıma riski daha yüksek |

Kılavuz yapısı ve sorgu kalitesi ölçülmeden tek bir profil her veri seti için en iyi kabul edilmemelidir. Varsayılan profil mevcut ingest davranışını koruyan güvenli başlangıç noktasıdır.
