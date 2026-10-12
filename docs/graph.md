# Neo4j graph yönetimi

CARAGENT graph katmanı iki veri akışını birbirinden ayırır:

1. `ingest` araç, kılavuz, sayfa ve chunk kaynak zincirini yazar.
2. `ingest-extraction` CAR-8 çıktısındaki doğrulanmış entity ve relationship kayıtlarını bu
   kaynak zincirine bağlar.

Extraction kayıtları gelecekteki domain graph tasarımını kilitlememek için genel
`CaragentEntity` node'ları ve `CaragentExtractedRelation` relationship'leri olarak saklanır.
Asıl tür `type`/`kind` alanındadır. Yalnız extraction sözleşmesindeki izinli türler kabul edilir.

## Kullanım

Önce manifesti graph'a aktarın, sonra aynı chunk kimliklerini kullanan extraction dosyasını yazın:

```powershell
.\.venv\Scripts\python.exe main.py ingest data/processed/toyota-corolla-le-2024.json
.\.venv\Scripts\python.exe main.py ingest-extraction data/processed/entity-extraction.json
```

İkinci komut tüm payload'u önce doğrular ve tek transaction içinde yazar. Entity veya
relationship kimliği tekrar gelirse `MERGE` ile güncellenir; kopya oluşmaz. Kaynak chunk yoksa,
chunk başka araca aitse, endpoint eksikse veya aynı kimlik farklı endpoint/tür/araç için
kullanılmışsa transaction geri alınır.

Her entity `SUPPORTS` bağlantılarıyla kanıt chunk'larına bağlıdır. Kanıtta `page_id`,
`page_number`, kaynak URL ve alıntı korunur. Relationship kanıtı JSON olarak ilişki üzerinde
tutulur.

## Bağlantı ayarları

`.env` içinden aşağıdaki değerler yönetilebilir:

- `NEO4J_CONNECTION_TIMEOUT`
- `NEO4J_MAX_RETRY_TIME`
- `NEO4J_POOL_SIZE`
- `NEO4J_ACQUISITION_TIMEOUT`
- `NEO4J_CONNECTION_LIFETIME`

Bağlantı, şema, okuma ve yazma hataları CLI/API katmanına kontrollü `GraphStoreError` olarak
iletilir. `GraphStore` context manager olarak da kullanılabilir ve `close()` tekrar çağrıldığında
güvenlidir.

## Arama ve izolasyon

`GraphStore.search` bütün kullanıcı değerlerini Cypher parametresi olarak geçirir. Arama en az
bir araç, model/yıl veya kılavuz filtresi gerektirir; ayrıca sayfa filtresi uygulanabilir. Her
sonuç chunk, sayfa, kılavuz ve araç kimlikleriyle birlikte kaynak URL, sayfa numarası ve eşleşme
nedenini döndürür. Sonuç limiti 1–10 arasındadır.

Bu görev domain'e özel kesin graph şeması, vector index veya LLM davranışını değiştirmez.
