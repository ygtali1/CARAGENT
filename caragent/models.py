from dataclasses import dataclass, asdict
import hashlib
import re
import unicodedata


def stable_id(*parts) -> str:
    return hashlib.sha256("\x00".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("Metin string olmalı.")
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    cleaned = []
    previous_text = None
    for line in lines:
        if not line:
            if cleaned and cleaned[-1]:
                cleaned.append("")
            previous_text = None
            continue
        # Extraction artifacts often repeat the same heading or line back-to-back.
        if line != previous_text:
            cleaned.append(line)
        previous_text = line
    return "\n".join(cleaned).strip()


@dataclass(frozen=True)
class Vehicle:
    model: str
    year: int
    market: str
    make: str = "Toyota"

    def __post_init__(self):
        if not all(isinstance(value, str) for value in (self.make, self.model, self.market)):
            raise TypeError("Marka, model ve pazar string olmalı.")
        if isinstance(self.year, bool) or not isinstance(self.year, int):
            raise TypeError("Model yılı integer olmalı.")
        make, model, market = (" ".join(value.split()) for value in
                               (self.make, self.model, self.market))
        if make.casefold() != "toyota":
            raise ValueError("Bu proje yalnızca Toyota verisi kabul eder.")
        if not model or not market or not 1960 <= self.year <= 2100:
            raise ValueError("Model, pazar ve geçerli model yılı gerekli.")
        object.__setattr__(self, "make", "Toyota")
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "market", market)

    @property
    def id(self):
        return stable_id("Toyota", self.model.casefold().strip(), self.year, self.market.casefold().strip())


@dataclass(frozen=True)
class Page:
    number: int
    text: str
    title: str = ""
    url: str = ""
    images: tuple[str, ...] = ()

    def __post_init__(self):
        if isinstance(self.number, bool) or not isinstance(self.number, int) or self.number < 1:
            raise ValueError("Sayfa numarası pozitif integer olmalı.")
        if not isinstance(self.text, str) or not normalize(self.text):
            raise ValueError("Sayfa metni boş olamaz.")
        if not isinstance(self.title, str) or not isinstance(self.url, str):
            raise TypeError("Sayfa başlığı ve URL string olmalı.")
        if not isinstance(self.images, (tuple, list)) or not all(
                isinstance(image, str) for image in self.images):
            raise TypeError("Görseller string listesi veya tuple olmalı.")
        object.__setattr__(self, "text", normalize(self.text))
        object.__setattr__(self, "title", " ".join(self.title.split()))
        object.__setattr__(self, "url", self.url.strip())
        object.__setattr__(self, "images", tuple(dict.fromkeys(image.strip() for image in self.images
                                                               if image.strip())))


@dataclass(frozen=True)
class Manual:
    key: str
    title: str
    vehicle: Vehicle
    language: str
    source: str
    pages: tuple[Page, ...]

    def __post_init__(self):
        if not all(isinstance(value, str) for value in
                   (self.key, self.title, self.language, self.source)):
            raise TypeError("Kılavuz metadatası string olmalı.")
        if not self.key.strip() or not self.title.strip() or not self.language.strip():
            raise ValueError("Kılavuz key, başlık ve dil alanları zorunludur.")
        if not isinstance(self.vehicle, Vehicle):
            raise TypeError("Kılavuz geçerli bir Vehicle içermeli.")
        if not isinstance(self.pages, (tuple, list)) or not self.pages or not all(
                isinstance(page, Page) for page in self.pages):
            raise ValueError("Kılavuz en az bir geçerli Page içermeli.")
        if len({page.number for page in self.pages}) != len(self.pages):
            raise ValueError("Kılavuz sayfa numaraları benzersiz olmalı.")
        object.__setattr__(self, "key", self.key.strip())
        object.__setattr__(self, "title", " ".join(self.title.split()))
        object.__setattr__(self, "language", self.language.strip().casefold())
        object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "pages", tuple(sorted(self.pages, key=lambda page: page.number)))

    @property
    def id(self):
        return stable_id(self.vehicle.id, self.key)

    @property
    def content_hash(self):
        return stable_id(self.title, self.language, self.source,
                         *[repr(asdict(p)) for p in self.pages])

    def content_hash_for(self, config: "ChunkingConfig") -> str:
        return stable_id(self.content_hash, config.signature)


@dataclass(frozen=True)
class ChunkingConfig:
    strategy: str = "character"
    size: int = 1000
    overlap: int = 150

    def __post_init__(self):
        minimum = {"character": 100, "token": 20, "paragraph": 1}
        if self.strategy not in minimum:
            raise ValueError("Chunklama yöntemi character, token veya paragraph olmalı.")
        if (isinstance(self.size, bool) or not isinstance(self.size, int)
                or self.size < minimum[self.strategy]):
            raise ValueError(
                f"{self.strategy} chunk boyutu en az {minimum[self.strategy]} olmalı."
            )
        if (isinstance(self.overlap, bool) or not isinstance(self.overlap, int)
                or self.overlap < 0 or self.overlap >= self.size):
            raise ValueError("Chunk overlap 0 veya daha büyük ve boyuttan küçük olmalı.")

    @property
    def signature(self) -> str:
        return f"structure-v3-{self.strategy}-{self.size}-{self.overlap}"


CHUNK_DEFAULTS = {
    "character": ChunkingConfig("character", 1000, 150),
    "token": ChunkingConfig("token", 250, 40),
    "paragraph": ChunkingConfig("paragraph", 5, 1),
}


def resolve_chunking(strategy="character", size=None, overlap=None) -> ChunkingConfig:
    default = CHUNK_DEFAULTS.get(strategy)
    if default is None:
        raise ValueError("Chunklama yöntemi character, token veya paragraph olmalı.")
    return ChunkingConfig(strategy, default.size if size is None else size,
                          default.overlap if overlap is None else overlap)


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    ordinal: int
    page_ordinal: int
    manual_id: str
    page_id: str
    page_number: int
    title: str
    source: str
    vehicle_id: str
    vehicle_model: str
    vehicle_year: int


def _looks_like_heading(block: str) -> bool:
    block = block.strip()
    letters = [character for character in block if character.isalpha()]
    return bool(block) and len(block) <= 100 and (
        block.startswith("#")
        or block.endswith(":")
        or (letters and all(character.isupper() for character in letters))
    )


def _preferred_end(text: str, start: int, size: int) -> int:
    limit = min(start + size, len(text))
    if limit == len(text):
        return limit
    minimum = start + max(size // 2, 1)
    for marker in ("\n\n", "\n"):
        boundaries = [match.end() for match in re.finditer(re.escape(marker), text[start:limit])
                      if start + match.start() >= minimum]
        if boundaries:
            boundary = start + boundaries[-1]
            preceding = text[start:boundary - len(marker)].rstrip().split(marker)[-1]
            if _looks_like_heading(preceding) and len(boundaries) > 1:
                return start + boundaries[-2]
            return boundary
    sentence_boundaries = [minimum + match.end()
                           for match in re.finditer(r"(?<!\d)[.!?](?:[\"')\]]+)?\s+",
                                                    text[minimum:limit])]
    if sentence_boundaries:
        return sentence_boundaries[-1]
    boundary = text.rfind(" ", minimum, limit)
    return boundary + 1 if boundary >= minimum else limit


def _overlap_start(text: str, end: int, overlap: int) -> int:
    if overlap == 0:
        return end
    start = max(0, end - overlap)
    if start == 0:
        return start
    # Begin on a word/line boundary while keeping no more than the requested overlap.
    boundary = re.search(r"\s+", text[start:end])
    return start + boundary.end() if boundary else start


def _window(items: list[str], size: int, overlap: int, joiner: str) -> list[str]:
    chunks, start = [], 0
    while start < len(items):
        piece = joiner.join(items[start:start + size]).strip()
        if piece:
            chunks.append(piece)
        if start + size >= len(items):
            break
        start += size - overlap
    return chunks


def split_text(text: str, size=1000, overlap=150, strategy="character") -> list[str]:
    config = ChunkingConfig(strategy, size, overlap)
    text = normalize(text)
    if not text:
        return []
    if config.strategy == "token":
        return _window(text.split(), config.size, config.overlap, " ")
    if config.strategy == "paragraph":
        paragraphs = [part.strip() for part in re.split(r"\n+", text) if part.strip()]
        return _window(paragraphs, config.size, config.overlap, "\n")
    chunks, start = [], 0
    while start < len(text):
        end = _preferred_end(text, start, config.size)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(text):
            break
        next_start = _overlap_start(text, end, config.overlap)
        start = next_start if next_start > start else end
    return chunks


def chunks_for_manual(manual: Manual, config: ChunkingConfig | None = None) -> tuple[Chunk, ...]:
    """Create deterministic, source-traceable chunks without crossing page boundaries."""
    config = config or ChunkingConfig()
    chunks = []
    ordinal = 0
    for page in manual.pages:
        page_id = stable_id(manual.id, page.number)
        for page_ordinal, text in enumerate(split_text(
                page.text, config.size, config.overlap, config.strategy)):
            chunks.append(Chunk(
                id=stable_id(page_id, page_ordinal, config.signature),
                text=text,
                ordinal=ordinal,
                page_ordinal=page_ordinal,
                manual_id=manual.id,
                page_id=page_id,
                page_number=page.number,
                title=page.title or manual.title,
                source=page.url or manual.source,
                vehicle_id=manual.vehicle.id,
                vehicle_model=manual.vehicle.model,
                vehicle_year=manual.vehicle.year,
            ))
            ordinal += 1
    return tuple(chunks)


# These are text mentions, never assertions of faults, compatibility or repair causality.
COMPONENTS = {
    "engine": ("engine", "motor"),
    "engine_oil": ("engine oil", "motor yağı", "motor yagi", "yağ", "oil pressure"),
    "brake": ("brake", "fren"),
    "battery": ("battery", "akü", "aku"),
    "tire": ("tire", "tyre", "lastik"),
    "coolant": ("coolant", "antifreeze", "soğutma", "sogutma"),
    "transmission": ("transmission", "şanzıman", "sanziman"),
    "airbag": ("airbag", "hava yastığı", "srs"),
}


def components(text: str) -> list[str]:
    text = text.casefold()
    return [key for key, aliases in COMPONENTS.items()
            if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text) for alias in aliases)]
