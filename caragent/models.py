from dataclasses import dataclass, asdict
import hashlib
import re
import unicodedata


def stable_id(*parts) -> str:
    return hashlib.sha256("\x00".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()).strip()


@dataclass(frozen=True)
class Vehicle:
    model: str
    year: int
    market: str
    make: str = "Toyota"

    def __post_init__(self):
        if self.make.casefold() != "toyota":
            raise ValueError("Bu proje yalnızca Toyota verisi kabul eder.")
        if not self.model.strip() or not self.market.strip() or not 1960 <= self.year <= 2100:
            raise ValueError("Model, pazar ve geçerli model yılı gerekli.")

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


@dataclass(frozen=True)
class Manual:
    key: str
    title: str
    vehicle: Vehicle
    language: str
    source: str
    pages: tuple[Page, ...]

    @property
    def id(self):
        return stable_id(self.vehicle.id, self.key)

    @property
    def content_hash(self):
        return stable_id(self.title, self.language, self.source,
                         *[repr(asdict(p)) for p in self.pages])


@dataclass(frozen=True)
class ChunkingConfig:
    strategy: str = "character"
    size: int = 1000
    overlap: int = 150

    def __post_init__(self):
        minimum = {"character": 100, "token": 20, "paragraph": 1}
        if self.strategy not in minimum:
            raise ValueError("Chunklama yöntemi character, token veya paragraph olmalı.")
        if self.size < minimum[self.strategy] or self.overlap < 0 or self.overlap >= self.size:
            raise ValueError(
                f"{self.strategy} chunk boyutu en az {minimum[self.strategy]}; "
                "overlap boyuttan küçük olmalı."
            )

    @property
    def signature(self) -> str:
        return f"chunker-v2-{self.strategy}-{self.size}-{self.overlap}"


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
        end = min(start + config.size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + config.size // 2, end)
            if boundary > start:
                end = boundary
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(text):
            break
        start = end - config.overlap
    return chunks


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
