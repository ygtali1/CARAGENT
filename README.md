# CARAGENT — Toyota GraphRAG

Toyota kılavuzlarını okuyup Neo4j graph veritabanını otomatik oluşturur. Model ve yıl seçilerek sorulan sorular için ilgili kılavuz metnini, kaynak bağlantısını ve sayfayı gösterir. Yerel Ollama modeli açıldığında Türkçe yanıt üretir.

Başlangıç verisi **Lemon Manuals / Toyota Corolla LE / 2024 / Repair and Diagnosis** sayfalarıdır. İçe aktarma bütün Toyota modellerine açık, bu ilk veri seti sınırlıdır. Rust kullanılmaz: proje Python 3.12 + Neo4j + RAG/GraphRAG üzerine kuruludur.

## Hızlı başlangıç — Windows / PyCharm

1. Docker Desktop'ı açın.
2. PyCharm → Settings → Project → Python Interpreter alanında proje ortamını seçin: `C:\dev\CARAGENT\.venv\Scripts\python.exe`. Python sürümü 3.12 olmalı. `environment.yml` veya kurulum `.exe` dosyası interpreter değildir.
3. Proje terminalinde aşağıdaki komutları çalıştırın:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py setup --pages 12
.\.venv\Scripts\python.exe main.py enable-llm
.\.venv\Scripts\python.exe main.py serve
```

Sohbet ekranı: **http://127.0.0.1:8000**. Mesajlar alt alta korunur; takip soruları önceki konuşma ile birlikte işlenir. Kaynak bağlantıları ve kayıtlı metinler her cevabın altında açılır. Sohbet bu tarayıcıda saklanır; "Yeni sohbet" veya araç değişikliği konuşmayı sıfırlar. PyCharm'da `main.py` dosyasını parametresiz çalıştırmak da ekran sunucusunu başlatır. Çalışma dizini `C:\dev\CARAGENT`, interpreter `.venv\Scripts\python.exe` olmalı.

Alternatif kurulum: `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -Pages 12`. Bu betik mevcut venv'i kullanır; venv oluşturmaz.

Bağımlılık listesi proje kökündeki `requirements.txt` içindedir; paketler `.venv\Lib\site-packages` içine kurulur. Conda gerekli değildir.

Bu bilgisayarda test edilen paket sürümlerini birebir kurmak için `pip install -r requirements-lock.txt` kullanabilirsiniz. Bu kilit dosyası test paketlerini de içerir.

## Türkçe yanıt üreten yerel model

Sohbet için yerel model gerekir. Kurulumda henüz çalıştırmadıysanız modeli kurup etkinleştirin:

```powershell
.\.venv\Scripts\python.exe main.py enable-llm
.\.venv\Scripts\python.exe main.py serve
```

Bu komut projeye ait Ollama konteynerini başlatır, `qwen2.5:3b` modelini indirir ve `.env` içinde `ANSWER_MODE=ollama` ayarlar. İlk indirme Docker imajıyla birlikte birkaç GB'tır; model tek başına yaklaşık 1.9 GB'tır. Başka model: `main.py enable-llm --model <ollama-modeli>`. Uygulama açıksa durdurup yeniden başlatın. API anahtarı gerekmez. Model hazır değilse sohbet içinde durum açıklanır; kaynaklar ayrıca açılabilir.

## Neo4j graph'ını görmek

**http://127.0.0.1:7474** adresini açın. Kullanıcı `neo4j`, parola yerel `.env` dosyasında `NEO4J_PASSWORD` değeridir. Bağlantı `bolt://127.0.0.1:7687`.

```cypher
MATCH p=(v:CaragentVehicle)-[:HAS_MANUAL]->(:CaragentManual)
        -[:HAS_PAGE]->(:CaragentPage)-[:HAS_CHUNK]->(:CaragentChunk)
RETURN p LIMIT 50;
```

Parça adı bağlantıları:

```cypher
MATCH p=(c:CaragentChunk)-[:MENTIONS]->(t:CaragentComponent)
RETURN p LIMIT 50;
```

## Başka Toyota kılavuzları eklemek

Lemon'da bir modelin `Repair and Diagnosis` URL'sini kullanın. İstek ve sayfa sayısı sınırlıdır; önce küçük bir veri setiyle başlayın:

```powershell
.\.venv\Scripts\python.exe main.py crawl --url "https://lemon-manuals.la/Toyota/2024/Corolla%20LE/Repair%20and%20Diagnosis/" --pages 30 --requests 150 --output data/processed/corolla-2024.json
.\.venv\Scripts\python.exe main.py ingest data/processed/corolla-2024.json
```

Tarama `data/crawl-report.json` içinde başarılı sayfa sayısını, hataları ve kapsamın sınırlandırılıp sınırlandırılmadığını raporlar. Ham HTML `data/raw/lemon`, manifest `data/processed` içinde tutulur. Komutu yeniden çalıştırınca indirilen HTML önbelleği kullanılır. İçe aktarma değişmeyen belgeleri tekrar oluşturmaz. Varsayılan tarama bütün siteyi indirmez.

Yerel PDF, TXT, MD veya HTML dosyaları için dosyanın yanına manifest koyun:

```json
{
  "schema_version": 1,
  "manuals": [{
    "key": "toyota-corolla-2024-owner-us",
    "title": "Toyota Corolla 2024 Owner Manual",
    "vehicle": {"make": "Toyota", "model": "Corolla", "year": 2024, "market": "US/Canada"},
    "language": "en",
    "source": "https://www.toyota.com/owners/",
    "file": "corolla-2024.pdf"
  }]
}
```

Yukarıdaki dosya adı örnektir; gerçek PDF'yi siz sağlamalısınız. `file` yolu manifestin konumuna göredir. Sonra `main.py ingest <manifest-yolu>` çalıştırın. Metin içermeyen taranmış PDF için önce OCR gerekir. `data/examples/manifest.json` yalnız yazılım testinde kullanılan sentetik veridir; gerçek araç talimatı içermez, başlangıç kurulumunda yüklenmez.

## Komutlar ve API

```powershell
.\.venv\Scripts\python.exe main.py --help
.\.venv\Scripts\python.exe main.py stats
.\.venv\Scripts\python.exe main.py vehicles
.\.venv\Scripts\python.exe main.py ask "motor yağı seviyesi" --vehicle <vehicles-komutundaki-id>
```

API dokümanı: http://127.0.0.1:8000/docs

| Endpoint | İşlev |
|---|---|
| `GET /api/health` | Neo4j bağlantısı ve yanıt modu |
| `GET /api/vehicles` | İçe aktarılmış araçlar |
| `GET /api/stats` | Graph kayıt sayıları |
| `GET /api/graph/{vehicle_id}` | Araç, belge ve parça bağlantıları |
| `POST /api/ask` | `question`, `vehicle_id`, isteğe bağlı `limit` ve `history` ile sohbet cevabı |

`history`, geçmiş user/assistant mesaj çiftlerini içerir; en fazla 12 mesaj gönderilir. Sistem talimatları istemciden kabul edilmez. Sunucu yakın konuşma turlarını sınırlı bir bağlam bütçesiyle modele aktarır. "Peki bunu…" gibi takip sorularında önceki kullanıcı konusu aramaya eklenir; açıkça belirtilen yeni bir parça konusu ayrı aranır. Genel amaçlı dil modeli sorgu yeniden yazımı henüz kullanılmaz.

## Testler

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
# Gerçek Neo4j testi (Docker açık ve main.py init çalıştırılmış olmalı):
$env:CARAGENT_INTEGRATION="1"
.\.venv\Scripts\python.exe -m pytest -q
```

Testler HTML tablo çıkarımı, Toyota kapsamı, kimlikler, metin bölme, manifest doğrulama, modelin kullanılamaması, geçersiz atıflar ve API girdilerini kontrol eder. Entegrasyon testi gerçek graph üzerinde tekrar yüklemeyi, araç/yıl izolasyonunu, güncellemeyi ve başarısız transaction'ın geri alınmasını kontrol eder; yalnız kendisinin oluşturduğu test belgelerini temizler.

## Sorun giderme

- `CreateProcess error=193`: PyCharm interpreter olarak `.venv\Scripts\python.exe` seçili olmalı.
- `Python installation interrupted`: Python 3.12 zaten kuruluysa PyCharm'da **Select existing** ile interpreter seçin; **download and install** satırını kullanmayın.
- Neo4j hazır değil: `docker compose ps`, `docker compose logs neo4j` ve `.env` bağlantı/parolasını kontrol edin. Mevcut Docker veri alanındaki parola `.env` değişikliğiyle otomatik güncellenmez.
- Kaynak bulunamıyor: yalnız içe aktarılan belgeler aranır. Model/yıl seçimini kontrol edin; sınırlı Türkçe sözlüğün dışındaki terimler için İngilizce sorgu deneyin.
- Görsel içinde bilgi var: metin çıkarıcı diyagramları okumaz; kaynak bağlantısını açın.

Durdurmak: `docker compose --profile llm stop`. Yeniden başlatmak: `docker compose --profile llm up -d`, ardından `main.py serve`. Kalıcı graph ve model dosyaları Docker volume'lerinde korunur.

Mimari, graph şeması ve yöntemin sınırları için [docs/architecture.md](docs/architecture.md) dosyasına bakın.
