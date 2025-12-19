import json
import os
from pathlib import Path
from collections import defaultdict

# --- KONFIGURATION ---
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
SCHEMA_DIR = DATA_DIR / "schema"
OUTPUT_FILE = SCHEMA_DIR / "defaults.schema.json"

INPUT_FILES = {
    "enemies": DATA_DIR / "enemies.json",
    "towers": DATA_DIR / "towers.json",
    "cards": DATA_DIR / "cards.json"
}


def load_json(path):
    if not path.exists():
        print(f"⚠️ Warnung: {path.name} nicht gefunden.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Fehler beim Lesen von {path.name}: {e}")
            return []


def extract_ids(data):
    if isinstance(data, dict):
        return sorted(data.keys())
    elif isinstance(data, list):
        ids = []
        for item in data:
            val = item.get("id") or item.get("name")
            if val:
                ids.append(val)
        return sorted(ids)
    return []


def map_cards_to_towers(cards_data):
    mapping = defaultdict(list)
    items = []

    if isinstance(cards_data, dict):
        items = cards_data.items()
    elif isinstance(cards_data, list):
        for c in cards_data:
            identifier = c.get("id") or c.get("name") or "UNKNOWN"
            items.append((identifier, c))

    for card_identifier, props in items:
        if not isinstance(props, dict): continue

        tower_ref = props.get("tower") or props.get("tower_id")

        if tower_ref and card_identifier != "UNKNOWN":
            mapping[tower_ref].append(card_identifier)

    return mapping


def generate():
    print(f"🔄 Starte Schema-Generierung (Tier-Support)...")

    enemies_data = load_json(INPUT_FILES["enemies"])
    towers_data = load_json(INPUT_FILES["towers"])
    cards_data = load_json(INPUT_FILES["cards"])

    enemy_ids = extract_ids(enemies_data)
    tower_ids = extract_ids(towers_data)
    cards_by_tower = map_cards_to_towers(cards_data)

    print(f"   - {len(enemy_ids)} Enemies")
    print(f"   - {len(tower_ids)} Towers")

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "weekly_enemy_pool": {
                "type": "array",
                "items": {"type": "string", "enum": enemy_ids}
            },
            "available_towers": {
                "type": "array",
                "items": {"type": "string", "enum": tower_ids}
            },
            "weekly_card_setup": {
                "type": "object",
                "description": "Card configuration per tower organized by tiers.",
                "properties": {},
                "additionalProperties": False
            }
        },
        "additionalProperties": True
    }

    # HIER IST DIE WICHTIGE ÄNDERUNG:
    for t_id in tower_ids:
        valid_cards = sorted(cards_by_tower.get(t_id, []))

        if valid_cards:
            schema["properties"]["weekly_card_setup"]["properties"][t_id] = {
                "type": "object",
                "description": f"Tiers for {t_id}",
                # patternProperties erlaubt keys wie "tier_1", "tier_2", "tier_10"
                "patternProperties": {
                    "^tier_\\d+$": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": valid_cards
                        }
                    }
                },
                "additionalProperties": False
            }

    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print(f"✅ Schema gespeichert: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate()