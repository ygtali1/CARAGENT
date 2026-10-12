# CAR-5 ingest ve chunklama parametre raporu

## Sonuç ve önerilen varsayılanlar

Güvenli başlangıç profili; tek eşzamanlı istek, istekler arasında 1 saniye, 45 saniye timeout, iki retry, 1 saniyeden başlayan üstel backoff ve 24 saatlik HTML cache kullanır. Graph ingest için önerilen profil `character / 1000 / 150` değerleridir. Bu profil mevcut davranışı korur, yaklaşık %15 örtüşmeyle bağlam sürekliliği sağlar ve tokenizasyon bağımlılığı eklemez.

| Parametre | Varsayılan | Gerekçe |
|---|---:|---|
| Maksimum makale | 12 (`--all` ile sınırsız) | Küçük deneme için güvenli varsayılan; tam Corolla veri seti için kuyruk sonuna kadar tarama |
| Maksimum ziyaret | 80 (`--all` ile sınırsız) | Dizin sayfaları dâhil sınırlı deneme veya tam araç-kökü taraması |
| İstek aralığı | 1 sn | Kaynak sunucuya ölçülü yük; robots.txt daha yüksekse o uygulanır |
| Timeout | 45 sn | Büyük HTML yanıtlarına tolerans |
| Retry | 2 | Geçici bağlantı, HTTP 429 ve 5xx hataları için sınırlı tekrar |
| Backoff | 1 sn | Tekrarlar arasında 1 ve 2 saniyelik üstel bekleme |
| Cache TTL | 86400 sn | Bir günlük yeniden indirmeme süresi |
| Concurrency | 1 | En güvenli varsayılan; açıkça istenirse 1–16 arası artırılabilir |
| Chunk | character / 1000 / 150 | Bağımlılıksız, mevcut GraphRAG davranışıyla uyumlu |

`--cache-ttl 0` cache okumayı kapatır; `--refresh-cache` mevcut dosyaları sürelerine bakmadan yeniden indirir. Ağ isteği başarısız olduğunda var olan eski cache kullanılabilir ve bu olay raporda `stale_cache_used` olarak görünür. Tarama raporu süre, ağ isteği, retry, cache hit, hata oranı ve etkin ayarları kaydeder.

Tam Toyota Corolla LE 2024 parse işlemi için araç kökü varsayılan URL'dir ve `crawl --all` kullanılır. Bu akış yalnız HTML cache'i ve JSON manifesti üretir; Neo4j bağlantısı gerektirmez. `crawl.complete=true` ve boş hata listesi, keşfedilen kuyruğun eksiksiz tamamlandığını gösterir.

## Chunk profili karşılaştırması

Aynı sentetik içerik küçük, orta ve büyük kılavuz boyutlarında çoğaltılarak üç varsayılan profil karşılaştırıldı. Sorgular `engine oil level` ifadesini aradı. `recall@5` ve `MRR@5`, Neo4j yerine yalnız chunk sınırlarının etkisini tekrarlanabilir biçimde ölçen sözcüksel bir proxy'dir; gerçek veri seçimi sonrasında Neo4j retrieval testi de çalıştırılmalıdır.

| Profil | Chunk | Ortalama karakter | Tahmini örtüşme | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|---:|
| character / 1000 / 150 | 131 | 989.63 | %14.81 | 1.00 | 1.00 |
| token / 250 / 40 | 73 | 1792.92 | %15.62 | 1.00 | 1.00 |
| paragraph / 5 / 1 | 278 | 521.91 | %23.88 | 1.00 | 1.00 |

Toplam kaynak boyutu 110.445 karakterdir. Üç profil de sentetik beklenen ifadeyi ilk beş sonuçta buldu. Token profili daha az ve daha geniş parçalar üretti; paragraph profili en fazla parça ve en yüksek tekrar maliyetine sahip oldu. Bu nedenle gerçek kılavuzlarda ölçüm aksini göstermedikçe karakter profili dengeli varsayılan olarak seçildi.

## Tekrarlanabilir ölçüm

```powershell
.\.venv\Scripts\python.exe main.py benchmark-chunks data/examples/manifest.json `
  --queries data/examples/benchmark-queries.json `
  --output data/chunk-benchmark.json
```

Gerçek küçük, orta ve büyük manifestler aynı komutla ayrı ayrı ölçülebilir. Çıktı; chunk sayısı, ortalama boyut, tahmini örtüşme, recall@5 ve MRR@5 değerlerini JSON olarak saklar.

## Doğrulama kapsamı

Otomatik testler üç chunk stratejisinin overlap davranışını, geçersiz parametreleri, cache TTL/yenileme davranışını, 429/5xx retry bütçesini ve üç profil için retrieval proxy sonucunu kontrol eder. Gerçek Neo4j entegrasyon testi `CARAGENT_INTEGRATION=1` ile çalıştırıldığında ingest, tekrar ingest, replacement, araç izolasyonu ve retrieval akışını doğrular. Canlı Lemon taraması CI testlerinde yapılmaz; robots.txt ve dış servis durumu nedeniyle ağ testi bilinçli olarak operatör kontrollüdür.
