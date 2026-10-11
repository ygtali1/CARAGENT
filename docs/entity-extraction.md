# Entity ve relationship extraction

CAR-8, `Chunk` nesnelerinden Neo4j'den bağımsız `caragent-extraction-v1` JSON çıktısı üretir. Bu aşama graph'a node veya relationship yazmaz.

## Çalıştırma

Deterministik, çevrimdışı Türkçe/İngilizce kurallar:

```powershell
.\.venv\Scripts\python.exe main.py extract data/processed/toyota-corolla-le-2024.json `
  --mode rules `
  --output data/processed/entity-extraction.json
```

Mevcut Ollama altyapısı:

```powershell
.\.venv\Scripts\python.exe main.py extract data/processed/toyota-corolla-le-2024.json `
  --mode ollama `
  --model qwen2.5:3b `
  --output data/processed/entity-extraction.json
```

Chunk ayarları `--chunk-strategy`, `--chunk-size` ve `--chunk-overlap` ile aynı komuta verilebilir.

## Kontrollü şema

İzin verilen entity türleri: `component`, `system`, `maintenance_action`, `warning` ve `technical_value`.

İzin verilen relationship türleri: `applies_to`, `has_value`, `warns_about`, `part_of` ve `requires`.

Her entity araç modeli/yılı bağlamını ve `chunk_id`, `page_id`, sayfa numarası, kaynak URL ile birebir kaynak alıntısını taşır. Relationship yönü `source_entity_id → target_entity_id` alanlarıyla açıktır. Güveni `0.8` altındaki adaylar `needs_review` olur; açık ve tekil eşleşmeler `verified` olur.

LLM çıktısı izinli türler, endpoint'ler, confidence aralığı ve kaynakta gerçekten bulunan birebir alıntılar açısından doğrulanır. Kaynakta olmayan veya şema dışı adaylar graph'a aktarılabilecek çıktıya alınmaz ve `warnings` altında raporlanır. Bozuk JSON ya da Ollama hatası uygulamayı çökertmeden kontrollü uyarıya çevrilir. Çıktı model adı, extractor sürümü ve parametrelerini içerir.

## Normalizasyon ve duplicate kontrolü

Bilinen Türkçe/İngilizce teknik eş anlamlıları kontrollü bir sözlükle ortak kanonik ada bağlanır. Örneğin `motor yağı` ve `engine oil`, aynı araç bağlamında `engine oil` olur. Aynı entity farklı chunk'larda bulunduğunda tek kimlik altında birleştirilir ancak bütün kanıt kayıtları korunur. Sözlükte olmayan veya belirsiz eşleşmeler otomatik birleştirilmez.

## Değerlendirme

Sentetik ve insan etiketli fixture ile rapor üretmek için:

```powershell
.\.venv\Scripts\python.exe main.py extract `
  data/examples/extraction-evaluation-manifest.json `
  --output data/examples/extraction-evaluation-predicted.json

.\.venv\Scripts\python.exe main.py evaluate-extraction `
  data/examples/extraction-evaluation-predicted.json `
  data/examples/extraction-evaluation-gold.json
```

Mevcut fixture sonucu:

| Tür | Precision | Recall | F1 |
|---|---:|---:|---:|
| Entity | 1.0000 | 1.0000 | 1.0000 |
| Relationship | 1.0000 | 1.0000 | 1.0000 |
| Macro |  |  | 1.0000 |

Bu değer yalnızca 9 entity ve 6 relationship içeren sentetik regresyon fixture'ını ölçer; gerçek Lemon veri setindeki genel kalite iddiası değildir. Gerçek kalite karşılaştırması için aynı gold formatında insan etiketli daha geniş bir corpus kullanılmalıdır.

## Graph katmanı arayüzü

`ExtractionResult.graph_payload()` entity ve relationship satırlarını verir. `extract_chunks()` ayrıca tüm chunk sonuçlarını, araç bağlamında birleştirilmiş entity listesini, relationship listesini ve özet sayaçlarını üretir. Graph şeması kesinleştiğinde `graph.py` bu arayüzü tüketebilir; extraction kodunun Neo4j bağımlılığı yoktur.
