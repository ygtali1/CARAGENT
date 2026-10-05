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
                         *[repr(asdict(p)) for p in self.pages], "chunker-v1-1000-150")


def split_text(text: str, size=1000, overlap=150) -> list[str]:
    if size < 100 or overlap < 0 or overlap >= size:
        raise ValueError("Parça boyutu en az 100; overlap boyuttan küçük olmalı.")
    text = normalize(text)
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(text):
            break
        start = end - overlap
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
