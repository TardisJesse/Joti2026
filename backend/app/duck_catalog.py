"""The 20 physical ducks; public metadata excludes NFC serial identities."""
import json
from pathlib import Path

PACK_PATH = Path(__file__).parent / 'data/allart_joti_2026_walkable_v3.json'

def standard_pack():
    return json.loads(PACK_PATH.read_text(encoding='utf-8'))

def duck_catalog():
    return {point['duck_number']:point for point in standard_pack()['boards'][0]['objects'] if point['type']=='PHYSICAL_DUCK'}
