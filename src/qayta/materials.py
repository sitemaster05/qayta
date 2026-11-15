"""Material catalogue for Qayta.

This module is the single source of truth for every material the bot can classify.
All other modules (vision, bot, impact, places) import from here.

.. note::
    ``recyclable_uz`` is **general guidance** based on what collection points in
    Uzbek cities (Tashkent, Samarkand, Ohangaron) commonly accept. It is **not** a
    legal or regulatory classification. Availability varies by city and operator —
    always confirm with your local recycling point.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    """A single recyclable (or non-recyclable) material type.

    Attributes:
        key:          Canonical identifier, e.g. ``"PET_1"``.
        name_i18n:    i18n key for the localised display name, e.g. ``"mat.PET_1"``.
        recyclable_uz: ``True`` if commonly accepted by collection points in Uzbekistan.
                      General guidance only — see module docstring.
        tips:         1–3 i18n keys for preparation steps the user should follow.
        osm_tag:      OpenStreetMap ``recycling:*`` tag used when querying Overpass.
        avg_weight_g: Average item weight in grams, used by the impact counter.
    """

    key: str
    name_i18n: str
    recyclable_uz: bool
    tips: list[str]
    osm_tag: str
    avg_weight_g: float


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------
# Average weight sources (inline):
#   PET bottle:    ~25 g  — typical 0.5 L PET bottle tare weight
#   HDPE bottle:   ~50 g  — typical 1 L HDPE bottle
#   PP container:  ~30 g  — small PP yoghurt cup / food container
#   Glass bottle: ~250 g  — standard 0.5 L soda-lime glass bottle
#   A4 paper:       ~5 g  — single A4 sheet (80 g/m²)
#   Cardboard box: ~200 g — small e-commerce cardboard box
#   Aluminium can:  ~15 g — standard 330 mL beverage can
#   Steel can:      ~60 g — standard 400 g food tin
#   AA battery:     ~25 g — alkaline AA cell
#   Smartphone:    ~180 g — average mid-range smartphone
#   T-shirt:       ~200 g — average cotton t-shirt
#   Food scraps:   ~500 g — a representative portion of kitchen organic waste
#   Mixed waste:   ~300 g — generic mixed-waste bag estimate

CATALOGUE: dict[str, Material] = {
    "PET_1": Material(
        key="PET_1",
        name_i18n="mat.PET_1",
        recyclable_uz=True,
        tips=["tip.rinse", "tip.remove_cap", "tip.flatten"],
        osm_tag="recycling:plastic_bottles",
        avg_weight_g=25.0,  # typical 0.5 L PET bottle tare weight
    ),
    "HDPE_2": Material(
        key="HDPE_2",
        name_i18n="mat.HDPE_2",
        recyclable_uz=True,
        tips=["tip.rinse", "tip.remove_cap"],
        osm_tag="recycling:plastic",
        avg_weight_g=50.0,  # typical 1 L HDPE bottle
    ),
    "PP_5": Material(
        key="PP_5",
        name_i18n="mat.PP_5",
        recyclable_uz=True,
        tips=["tip.rinse", "tip.dry"],
        osm_tag="recycling:plastic",
        avg_weight_g=30.0,  # small PP yoghurt cup / food container
    ),
    "GLASS": Material(
        key="GLASS",
        name_i18n="mat.GLASS",
        recyclable_uz=True,
        tips=["tip.rinse", "tip.keep_whole"],
        osm_tag="recycling:glass",
        avg_weight_g=250.0,  # standard 0.5 L soda-lime glass bottle
    ),
    "PAPER": Material(
        key="PAPER",
        name_i18n="mat.PAPER",
        recyclable_uz=True,
        tips=["tip.dry", "tip.separate_pages", "tip.remove_staples"],
        osm_tag="recycling:paper",
        avg_weight_g=5.0,  # single A4 sheet (80 g/m²)
    ),
    "CARDBOARD": Material(
        key="CARDBOARD",
        name_i18n="mat.CARDBOARD",
        recyclable_uz=True,
        tips=["tip.flatten", "tip.dry"],
        osm_tag="recycling:cardboard",
        avg_weight_g=200.0,  # small e-commerce cardboard box
    ),
    "ALUMINIUM": Material(
        key="ALUMINIUM",
        name_i18n="mat.ALUMINIUM",
        recyclable_uz=True,
        tips=["tip.rinse", "tip.flatten"],
        osm_tag="recycling:aluminium",
        avg_weight_g=15.0,  # standard 330 mL beverage can
    ),
    "STEEL": Material(
        key="STEEL",
        name_i18n="mat.STEEL",
        recyclable_uz=True,
        tips=["tip.rinse", "tip.keep_whole"],
        osm_tag="recycling:scrap_metal",
        avg_weight_g=60.0,  # standard 400 g food tin
    ),
    "BATTERIES": Material(
        key="BATTERIES",
        name_i18n="mat.BATTERIES",
        recyclable_uz=True,
        tips=["tip.discharge", "tip.bag_separately"],
        osm_tag="recycling:batteries",
        avg_weight_g=25.0,  # alkaline AA cell
    ),
    "EWASTE": Material(
        key="EWASTE",
        name_i18n="mat.EWASTE",
        recyclable_uz=True,
        tips=["tip.remove_batteries", "tip.handle_safely"],
        osm_tag="recycling:electrical_appliances",
        avg_weight_g=180.0,  # average mid-range smartphone
    ),
    "TEXTILES": Material(
        key="TEXTILES",
        name_i18n="mat.TEXTILES",
        recyclable_uz=False,
        tips=["tip.dry", "tip.bag_separately"],
        osm_tag="recycling:clothes",
        avg_weight_g=200.0,  # average cotton t-shirt
    ),
    "ORGANIC": Material(
        key="ORGANIC",
        name_i18n="mat.ORGANIC",
        recyclable_uz=False,
        tips=["tip.bag_separately"],
        osm_tag="recycling:organic",
        avg_weight_g=500.0,  # representative portion of kitchen organic waste
    ),
    "MIXED": Material(
        key="MIXED",
        name_i18n="mat.MIXED",
        recyclable_uz=False,
        tips=["tip.no_preparation"],
        osm_tag="recycling:waste",
        avg_weight_g=300.0,  # generic mixed-waste bag estimate
    ),
}
