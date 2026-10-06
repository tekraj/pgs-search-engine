"""Static geographic data for the Geo API (provinces, districts, municipality seed)."""

import json
import os
from pathlib import Path

from geo.schemas import MunicipalityType

# NOTE: province/district codes (P1-P7, D01-D77) are assigned sequentially in
# province order to match the README range. Confirm they match the codes the
# search core indexes with; if not, only this table needs to change.

# (code, English name, Nepali name)
_PROVINCES: list[tuple[str, str, str]] = [
    ("P1", "Koshi Province", "कोशी प्रदेश"),
    ("P2", "Madhesh Province", "मधेश प्रदेश"),
    ("P3", "Bagmati Province", "बागमती प्रदेश"),
    ("P4", "Gandaki Province", "गण्डकी प्रदेश"),
    ("P5", "Lumbini Province", "लुम्बिनी प्रदेश"),
    ("P6", "Karnali Province", "कर्णाली प्रदेश"),
    ("P7", "Sudurpashchim Province", "सुदूरपश्चिम प्रदेश"),
]

# province code -> [(English name, Nepali name), ...]  (77 districts total)
_DISTRICTS: dict[str, list[tuple[str, str]]] = {
    "P1": [
        ("Taplejung", "ताप्लेजुङ"), ("Panchthar", "पाँचथर"), ("Ilam", "इलाम"),
        ("Jhapa", "झापा"), ("Morang", "मोरङ"), ("Sunsari", "सुनसरी"),
        ("Dhankuta", "धनकुटा"), ("Terhathum", "तेह्रथुम"),
        ("Sankhuwasabha", "संखुवासभा"), ("Bhojpur", "भोजपुर"),
        ("Khotang", "खोटाङ"), ("Solukhumbu", "सोलुखुम्बु"),
        ("Okhaldhunga", "ओखलढुङ्गा"), ("Udayapur", "उदयपुर"),
    ],
    "P2": [
        ("Saptari", "सप्तरी"), ("Siraha", "सिराहा"), ("Dhanusha", "धनुषा"),
        ("Mahottari", "महोत्तरी"), ("Sarlahi", "सर्लाही"),
        ("Rautahat", "रौतहट"), ("Bara", "बारा"), ("Parsa", "पर्सा"),
    ],
    "P3": [
        ("Sindhuli", "सिन्धुली"), ("Ramechhap", "रामेछाप"), ("Dolakha", "दोलखा"),
        ("Sindhupalchok", "सिन्धुपाल्चोक"), ("Kavrepalanchok", "काभ्रेपलाञ्चोक"),
        ("Lalitpur", "ललितपुर"), ("Bhaktapur", "भक्तपुर"),
        ("Kathmandu", "काठमाडौँ"), ("Nuwakot", "नुवाकोट"), ("Rasuwa", "रसुवा"),
        ("Dhading", "धादिङ"), ("Makwanpur", "मकवानपुर"), ("Chitwan", "चितवन"),
    ],
    "P4": [
        ("Gorkha", "गोरखा"), ("Lamjung", "लमजुङ"), ("Tanahun", "तनहुँ"),
        ("Syangja", "स्याङ्जा"), ("Kaski", "कास्की"), ("Manang", "मनाङ"),
        ("Mustang", "मुस्ताङ"), ("Myagdi", "म्याग्दी"), ("Parbat", "पर्वत"),
        ("Baglung", "बागलुङ"), ("Nawalpur", "नवलपुर"),
    ],
    "P5": [
        ("Parasi", "परासी"), ("Rupandehi", "रुपन्देही"),
        ("Kapilvastu", "कपिलवस्तु"), ("Palpa", "पाल्पा"),
        ("Arghakhanchi", "अर्घाखाँची"), ("Gulmi", "गुल्मी"),
        ("Pyuthan", "प्यूठान"), ("Rolpa", "रोल्पा"),
        ("Rukum East", "रुकुम पूर्व"), ("Dang", "दाङ"),
        ("Banke", "बाँके"), ("Bardiya", "बर्दिया"),
    ],
    "P6": [
        ("Rukum West", "रुकुम पश्चिम"), ("Salyan", "सल्यान"),
        ("Surkhet", "सुर्खेत"), ("Dailekh", "दैलेख"), ("Jajarkot", "जाजरकोट"),
        ("Dolpa", "डोल्पा"), ("Jumla", "जुम्ला"), ("Kalikot", "कालिकोट"),
        ("Mugu", "मुगु"), ("Humla", "हुम्ला"),
    ],
    "P7": [
        ("Bajura", "बाजुरा"), ("Bajhang", "बझाङ"), ("Achham", "अछाम"),
        ("Doti", "डोटी"), ("Kailali", "कैलाली"), ("Kanchanpur", "कञ्चनपुर"),
        ("Dadeldhura", "डडेलधुरा"), ("Baitadi", "बैतडी"), ("Darchula", "दार्चुला"),
    ],
}

# Municipality seed. Nepal has 753 local levels; only entries with a confirmed
# ID are listed here (Pokhara's ID comes from the API README). Load the rest
# from a JSON file - see _load_extra_municipalities().
# (municipality_id, name_en, name_ne, type, district name_en, ward_count)
_MUNICIPALITY_SEED: list[tuple[str, str, str, MunicipalityType, str, int | None]] = [
    ("MUN75340", "Pokhara", "पोखरा", MunicipalityType.METROPOLITAN, "Kaski", 33),
]


def _load_extra_municipalities() -> list[tuple[str, str, str, MunicipalityType, str, int | None]]:
    """Optionally load the full municipality list from a JSON file.

    Set GEO_MUNICIPALITIES_JSON to a path containing a list of objects:
      {"municipality_id": "MUN75340", "name_en": "Pokhara", "name_ne": "पोखरा",
       "type": "Metropolitan City", "district_en": "Kaski", "ward_count": 33}
    """
    path = os.getenv("GEO_MUNICIPALITIES_JSON")
    if not path or not Path(path).is_file():
        return []
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        (
            r["municipality_id"],
            r["name_en"],
            r["name_ne"],
            MunicipalityType(r["type"]),
            r["district_en"],
            r.get("ward_count"),
        )
        for r in rows
    ]
