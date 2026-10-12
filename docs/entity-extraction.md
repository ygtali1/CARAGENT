# Entity ve relationship extraction

Extractor, CAR-6 soru araştırmasına göre zenginleştirilmiş `Chunk` nesnelerinden
`caragent-extraction-v2` JSON çıktısı üretir. Extraction aşaması Neo4j'ye yazmaz; graph katmanı
bu doğrulanmış sözleşmeyi typed node ve native relationship'lere dönüştürür.

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

İzin verilen entity türleri:

- `component`: fiziksel parça
- `system`: araç alt sistemi
- `fluid`: yağ, soğutma/fren/CVT sıvısı
- `maintenance_action`: kontrol, değişim, dolum, kalibrasyon gibi işlem
- `warning`: kaynakta açıkça yazan uyarı
- `symptom`: ikaz lambası, ses, titreşim, ağır direksiyon gibi belirti
- `technical_value`: basınç, tork, kapasite veya zaman/mesafe değeri
- `feature`: CarPlay, Smart Key, sürüş desteği gibi özellik
- `recall`: açık geri çağırma/kampanya kimliği

İzin verilen yönlü relationship türleri:

| Relationship | Kaynak → hedef |
|---|---|
| `applies_to` | bakım işlemi → parça/sıvı/sistem/özellik |
| `has_value` | parça/sıvı/sistem → teknik değer |
| `has_interval` | parça/sıvı/sistem → mesafe/zaman aralığı |
| `warns_about` | uyarı → parça/sıvı/sistem/özellik/belirti |
| `part_of` | parça → sistem |
| `requires` | bakım işlemi → teknik değer |
| `indicates` | belirti → parça/sistem |
| `resolved_by` | belirti → bakım işlemi |
| `affects` | geri çağırma → parça/sistem |

Her entity araç modeli/yılı, CAR-6 soru kategorileri, ilgili sistemler, P0–P2 önceliği ve
`chunk_id`, `page_id`, sayfa numarası, kaynak URL ile birebir kaynak alıntısını taşır.
Relationship yönü `source_entity_id → target_entity_id` alanlarıyla açıktır ve endpoint türleri
hem LLM doğrulamasında hem graph ingest sırasında kontrol edilir. Güveni `0.8` altındaki
adaylar `needs_review`; açık ve tekil eşleşmeler `verified` olur.

LLM çıktısı izinli türler, endpoint'ler, confidence aralığı ve kaynakta gerçekten bulunan birebir alıntılar açısından doğrulanır. Kaynakta olmayan veya şema dışı adaylar graph'a aktarılabilecek çıktıya alınmaz ve `warnings` altında raporlanır. Bozuk JSON ya da Ollama hatası uygulamayı çökertmeden kontrollü uyarıya çevrilir. Çıktı model adı, extractor sürümü ve parametrelerini içerir.

## Normalizasyon ve duplicate kontrolü

Bilinen Türkçe/İngilizce teknik eş anlamlıları kontrollü bir sözlükle ortak kanonik ada bağlanır.
Örneğin `motor yağı` ve `engine oil`, aynı araç bağlamında `fluid: engine oil` olur. Aynı entity
farklı chunk'larda bulunduğunda tek kimlik altında birleştirilir; bütün kanıtlar, soru kategorileri
ve sistem bağlamları korunur. Sözlükte olmayan veya belirsiz eşleşmeler otomatik birleştirilmez.

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

Bu değer yalnızca 9 entity ve 9 relationship içeren sentetik regresyon fixture'ını ölçer; gerçek
Lemon veri setindeki genel kalite iddiası değildir. Gerçek kalite karşılaştırması için aynı gold
formatında insan etiketli daha geniş bir corpus kullanılmalıdır.

## Graph katmanı arayüzü

`ExtractionResult.graph_payload()` typed entity ve relationship satırlarını verir.
`extract_chunks()` ayrıca taxonomy sürümünü, tüm chunk sonuçlarını, araç bağlamında birleştirilmiş
entity listesini, relationship listesini ve özet sayaçlarını üretir. `graph.py` bu sözleşmeyi
Neo4j'nin typed etiket ve ilişki yapılarına map eder; extraction kodunun Neo4j bağımlılığı yoktur.
