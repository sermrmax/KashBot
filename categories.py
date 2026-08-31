CATEGORY_ALIASES = {
    "Еда": [
        "еда",
        "хавчик",
        "фастфуд",
        "бургер",
        "шаурма",
        "ресторан",
        "кофе",
    ],

    "Табак": [
        "табак",
        "сигареты",
        "сиги",
        "снюс",
        "курилка",
    ],

    "Транспорт": [
        "транспорт",
        "такси",
        "метро",
        "автобус",
        "бензин",
    ],
}


def normalize_category(category: str) -> str:
    category = category.lower().strip()

    for main_category, aliases in CATEGORY_ALIASES.items():
        if category in aliases:
            return main_category

    return category.capitalize()