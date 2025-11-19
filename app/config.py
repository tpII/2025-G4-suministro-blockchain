# app/config.py

WINE_CATEGORIES = {
    "Tintos ligeros": {"examples": ["Pinot Noir", "Gamay", "Beaujolais"], "temp_min": 10, "temp_max": 18},
    "Tintos con cuerpo": {"examples": ["Cabernet Sauvignon", "Syrah", "Malbec"], "temp_min": 12, "temp_max": 20},
    "Tintos con crianza": {"examples": ["Rioja Reserva", "Bordeaux", "Nebbiolo"], "temp_min": 12, "temp_max": 20},
    "Blancos jóvenes": {"examples": ["Sauvignon Blanc", "Verdejo", "Albariño"], "temp_min": 8, "temp_max": 12},
    "Blancos con crianza": {"examples": ["Chardonnay barricado", "Viognier"], "temp_min": 10, "temp_max": 14},
    "Rosados ligeros": {"examples": ["Rosado de Garnacha", "Provence Rosé"], "temp_min": 8, "temp_max": 12},
    "Espumosos": {"examples": ["Champagne", "Cava", "Prosecco"], "temp_min": 6, "temp_max": 12},
    "Dulces/licorosos": {"examples": ["Oporto", "Moscatel", "Sauternes"], "temp_min": 10, "temp_max": 14},
}

WINE_VARIETALS = {
    "Pinot Noir": {"category": "Tintos ligeros", "temp_min": 10, "temp_max": 18},
    "Gamay": {"category": "Tintos ligeros", "temp_min": 10, "temp_max": 18},
    "Beaujolais": {"category": "Tintos ligeros", "temp_min": 10, "temp_max": 18},
    "Cabernet Sauvignon": {"category": "Tintos con cuerpo", "temp_min": 12, "temp_max": 20},
    "Syrah": {"category": "Tintos con cuerpo", "temp_min": 12, "temp_max": 20},
    "Malbec": {"category": "Tintos con cuerpo", "temp_min": 12, "temp_max": 20},
    "Rioja Reserva": {"category": "Tintos con crianza", "temp_min": 12, "temp_max": 20},
    "Bordeaux": {"category": "Tintos con crianza", "temp_min": 12, "temp_max": 20},
    "Nebbiolo": {"category": "Tintos con crianza", "temp_min": 12, "temp_max": 20},
    "Sauvignon Blanc": {"category": "Blancos jóvenes", "temp_min": 8, "temp_max": 12},
    "Verdejo": {"category": "Blancos jóvenes", "temp_min": 8, "temp_max": 12},
    "Albariño": {"category": "Blancos jóvenes", "temp_min": 8, "temp_max": 12},
    "Chardonnay barricado": {"category": "Blancos con crianza", "temp_min": 10, "temp_max": 14},
    "Viognier": {"category": "Blancos con crianza", "temp_min": 10, "temp_max": 14},
    "Rosado de Garnacha": {"category": "Rosados ligeros", "temp_min": 8, "temp_max": 12},
    "Provence Rosé": {"category": "Rosados ligeros", "temp_min": 8, "temp_max": 12},
    "Champagne": {"category": "Espumosos", "temp_min": 6, "temp_max": 12},
    "Cava": {"category": "Espumosos", "temp_min": 6, "temp_max": 12},
    "Prosecco": {"category": "Espumosos", "temp_min": 6, "temp_max": 12},
    "Oporto": {"category": "Dulces/licorosos", "temp_min": 10, "temp_max": 14},
    "Moscatel": {"category": "Dulces/licorosos", "temp_min": 10, "temp_max": 14},
    "Sauternes": {"category": "Dulces/licorosos", "temp_min": 10, "temp_max": 14},
}