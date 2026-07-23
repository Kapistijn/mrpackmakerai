"""Single source of truth for intent categories used by the whole pipeline."""
from __future__ import annotations
from enum import StrEnum

class IntentCategory(StrEnum):
    REALISM = "realism"
    WORLD_GENERATION = "world_generation"
    MOBS = "mobs"
    SURVIVAL = "survival"
    TECHNOLOGY = "technology"
    MAGIC = "magic"
    HORROR = "horror"
    FOOD = "food"
    FARMING = "farming"
    WEATHER = "weather"
    PHYSICS = "physics"
    SOUND = "sound"
    LIGHTING = "lighting"
    SEASONS = "seasons"
    TEMPERATURE = "temperature"
    ANIMALS = "animals"
    IMMERSION = "immersion"
    ADVENTURE = "adventure"
    EXPLORATION = "exploration"
    PERFORMANCE = "performance"

TAXONOMY_SYNONYMS: dict[IntentCategory, tuple[str, ...]] = {
    IntentCategory.REALISM: ("realism", "realistic", "real life", "lifelike"),
    IntentCategory.WORLD_GENERATION: ("worldgen", "world generation", "terrain", "biome", "structure"),
    IntentCategory.MOBS: ("mob", "mobs", "monster", "creature", "zombie"),
    IntentCategory.SURVIVAL: ("survival", "hardcore", "overleven"),
    IntentCategory.TECHNOLOGY: ("technology", "tech", "machine", "automation", "energy"),
    IntentCategory.MAGIC: ("magic", "spell", "arcane", "wizard"),
    IntentCategory.HORROR: ("horror", "scary", "creepy", "psychological"),
    IntentCategory.FOOD: ("food", "hunger", "cooking", "diet"),
    IntentCategory.FARMING: ("farm", "farming", "crop", "agriculture"),
    IntentCategory.WEATHER: ("weather", "storm", "rain"),
    IntentCategory.PHYSICS: ("physics", "gravity", "movement"),
    IntentCategory.SOUND: ("sound", "audio", "ambient", "ambience"),
    IntentCategory.LIGHTING: ("lighting", "light", "shadow", "darkness"),
    IntentCategory.SEASONS: ("season", "seasons"),
    IntentCategory.TEMPERATURE: ("temperature", "thirst", "cold", "heat"),
    IntentCategory.ANIMALS: ("animal", "animals", "wildlife"),
    IntentCategory.IMMERSION: ("immers", "atmosphere"),
    IntentCategory.ADVENTURE: ("adventure", "dungeon", "quest", "boss"),
    IntentCategory.EXPLORATION: ("explore", "exploration"),
    IntentCategory.PERFORMANCE: ("performance", "optimization", "fps", "memory"),
}

REALISM_CATEGORIES = (
    IntentCategory.REALISM, IntentCategory.WEATHER, IntentCategory.SEASONS,
    IntentCategory.TEMPERATURE, IntentCategory.FOOD, IntentCategory.FARMING,
    IntentCategory.ANIMALS, IntentCategory.PHYSICS, IntentCategory.SOUND,
    IntentCategory.LIGHTING, IntentCategory.SURVIVAL, IntentCategory.WORLD_GENERATION,
    IntentCategory.IMMERSION,
)

def category_text(category: str | IntentCategory) -> str:
    return category.value if isinstance(category, IntentCategory) else str(category).strip().casefold()

def matches_category(text: str, category: str | IntentCategory) -> bool:
    value = category_text(category)
    try: synonyms = TAXONOMY_SYNONYMS[IntentCategory(value)]
    except ValueError: synonyms = (value.replace("_", " "),)
    normalized = (text or "").casefold()
    return any(term in normalized for term in synonyms)
