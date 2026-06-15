import re
from dataclasses import dataclass, field

GUTENBERG_START = re.compile(
    r"\*\*\*\s*START OF (THE PROJECT )?GUTENBERG EBOOK.*?\*\*\*", re.IGNORECASE
)
GUTENBERG_END = re.compile(
    r"\*\*\*\s*END OF (THE PROJECT )?GUTENBERG EBOOK.*?\*\*\*", re.IGNORECASE
)

CHAPTER_HEADING = re.compile(
    r"^(chapter|section|part|lesson|article)\s+(\d+|[ivxlcdm]+)\b", re.IGNORECASE
)

NON_RECIPE_HEADINGS = re.compile(
    r"^(preface|introduction|contents|index|appendix|menu|menus|"
    r"breakfast|dinner|supper|lunch|luncheon|"
    r"household|hints|suggestions|notes)",
    re.IGNORECASE,
)

COOKING_VERBS = re.compile(
    r"\b(take|add|stir|mix|beat|boil|bake|roast|fry|broil|"
    r"grill|steam|simmer|chop|slice|dice|mince|season|serve|"
    r"strain|melt|cream|blend|knead|roll|pour|spread|sprinkle|"
    r"cover|cook|heat|warm|brown|cool|chill|set|thicken|rub|"
    r"press|cut|place|put|remove|return|prepare|drain|wash|"
    r"dissolve|beat|whip|fold|sift|combine|shape|arrange)\b",
    re.IGNORECASE,
)

MEASURE_RE = re.compile(
    r"\b(\d+[\s\-–/]*\d*|\d+\.\d+)\s*"
    r"(cup|c\.?|tablespoon|tbsp|teaspoon|tsp|ounce|oz|pound|lb|quart|qt|pint|pt|"
    r"gallon|gal|pinch|dash|piece|slice|clove|head|bunch|can|package|pkg|box|"
    r"bottle|jar|bag|stalk|leaf|sprig|stick|pat|drop|gill|peck|bushel)s?\b",
    re.IGNORECASE,
)

AMOUNT_AT_START = re.compile(r"^\s*(\d+[\s\-/]*\d*|\d+\.\d+)")

INGREDIENT_WORDS = re.compile(
    r"\b(butter|sugar|salt|pepper|flour|egg|eggs|milk|cream|water|oil|"
    r"onion|garlic|tomato|cheese|chicken|beef|pork|fish|rice|pasta|bread|"
    r"vanilla|cinnamon|nutmeg|baking\s*(powder|soda)?|yeast|honey|syrup|"
    r"molasses|vinegar|lemon|orange|juice|stock|broth|wine|sauce|"
    r"cracker|corn|beans|potato|carrot|celery|lettuce|cabbage|spinach|"
    r"peas|sugar|coffee|tea|chocolate|cocoa|raisin|currant|nut|almond|"
    r"pepper|mustard|catsup|ketchup|pickle|relish|mace|clove|ginger|"
    r"allspice|coriander|thyme|parsley|bay\s*leaf|marjoram|sage|"
    r"gelatin|jelly|jam|marmalade|shortening|lard|suet)\b",
    re.IGNORECASE,
)


@dataclass
class Recipe:
    title: str
    ingredients: list[str] = field(default_factory=list)
    instructions: str = ""
    source_book_id: int = 0
    source_title: str = ""


def strip_gutenberg_headers(text: str) -> str:
    start = GUTENBERG_START.search(text)
    end = GUTENBERG_END.search(text)
    if start:
        text = text[start.end():]
    if end:
        text = text[:end.start()]
    return text.strip()


def has_cooking_content(text: str) -> bool:
    lines = text.split("\n")
    non_empty = [l for l in lines if l.strip()]
    if len(non_empty) < 2:
        return False
    n_measures = len(MEASURE_RE.findall(text))
    n_ingredients = len(INGREDIENT_WORDS.findall(text))
    core_verbs = re.findall(
        r"\b(boil|bake|roast|fry|broil|simmer|strain|knead|sift"
        r"|melt|thicken|marinate|baste|brown)\b",
        text,
        re.IGNORECASE,
    )
    n_verbs = len(core_verbs)
    score = n_verbs * 3 + n_measures * 2 + n_ingredients
    if score >= 3:
        return True
    first_line = non_empty[0]
    if detect_recipe_title(first_line):
        if len(text) >= 100:
            return True
    return False


def detect_recipe_title(line: str) -> bool:
    stripped = line.strip().rstrip(".")
    if not stripped or len(stripped) < 4 or len(stripped) > 120:
        return False
    if CHAPTER_HEADING.match(stripped):
        return False
    if NON_RECIPE_HEADINGS.match(stripped):
        return False
    if stripped.startswith("(") or stripped.startswith("["):
        return False
    if MEASURE_RE.match(stripped):
        return False
    words = stripped.split()
    if len(words) < 2:
        return False
    if stripped.isupper() and len(stripped) > 5:
        return True
    if re.match(r"^[A-Z][a-z]+[- ][A-Z][a-z]+", stripped):
        return True
    upper = sum(1 for c in stripped if c.isupper())
    lower = sum(1 for c in stripped if c.islower())
    total = upper + lower
    if total > 0 and upper / total > 0.5:
        return True
    if any(w[0].isupper() for w in words if len(w) > 1):
        title_words = sum(1 for w in words if w[0].isupper())
        if title_words >= 2 and len(words) <= 8:
            return True
    return False


def split_into_sections(text: str) -> list[str]:
    lines = text.split("\n")
    sections: list[str] = []
    current: list[str] = []
    blank_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank_count += 1
            if blank_count >= 2:
                content = "\n".join(current).strip()
                if content and len(content) > 60:
                    sections.append(content)
                current = []
        else:
            blank_count = 0
            current.append(line)
    content = "\n".join(current).strip()
    if content and len(content) > 60:
        sections.append(content)
    return sections


def extract_ingredients_from_text(text: str) -> list[str]:
    sentences = re.split(r"(?:\.\s+|\n+)", text)
    ingredient_lines = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        has_measure = bool(MEASURE_RE.search(sent))
        has_ingredient_word = bool(INGREDIENT_WORDS.search(sent))
        has_amount_start = bool(AMOUNT_AT_START.match(sent))
        cooking_verb_start = bool(
            re.match(
                r"^\s*(take|add|stir|mix|beat|boil|bake|roast|fry|broil)\b",
                sent,
                re.IGNORECASE,
            )
        )
        if (has_measure or has_amount_start) and has_ingredient_word:
            ingredient_lines.append(sent)
        elif has_measure and not cooking_verb_start:
            ingredient_lines.append(sent)
    return ingredient_lines


def parse_recipe_from_section(section: str, book_id: int, book_title: str) -> Recipe | None:
    if not has_cooking_content(section):
        return None

    lines = section.split("\n")
    non_empty = [l.strip() for l in lines if l.strip()]
    if len(non_empty) < 2:
        return None

    title = ""
    body_lines: list[str] = []

    first_line = non_empty[0]
    if detect_recipe_title(first_line):
        title = first_line.rstrip(".")
        body_lines = non_empty[1:]
    else:
        best_score = 0
        best_idx = -1
        for i, l in enumerate(non_empty):
            if detect_recipe_title(l):
                upper = sum(1 for c in l if c.isupper())
                lower = sum(1 for c in l if c.islower())
                total = upper + lower
                if total > 0:
                    score = upper / total + len(l.split()) * 0.1
                    if score > best_score:
                        best_score = score
                        best_idx = i
        if best_idx >= 0:
            title = non_empty[best_idx].rstrip(".")
            body_lines = non_empty[:best_idx] + non_empty[best_idx + 1:]
        else:
            return None

    body = " ".join(body_lines)
    if len(body) < 50:
        return None

    ingredient_lines = extract_ingredients_from_text(body)
    instructions = body

    return Recipe(
        title=title,
        ingredients=ingredient_lines,
        instructions=instructions,
        source_book_id=book_id,
        source_title=book_title,
    )


def _has_actual_instructions(text: str) -> bool:
    verbs = re.findall(
        r"\b(boil|bake|roast|fry|broil|simmer|strain|knead|sift|"
        r"melt|thicken|marinate|baste|brown|stew|steam|beat|whip|"
        r"season|serve|chop|slice|dice|mince|pour|add|stir|mix)\b",
        text,
        re.IGNORECASE,
    )
    return len(verbs) >= 2


def parse_cookbook(text: str, book_id: int, book_title: str) -> list[Recipe]:
    body = strip_gutenberg_headers(text)
    sections = split_into_sections(body)
    recipes: list[Recipe] = []
    for section in sections:
        recipe = parse_recipe_from_section(section, book_id, book_title)
        if recipe:
            recipes.append(recipe)

    filtered = [r for r in recipes if _has_actual_instructions(r.instructions)]

    seen: set[str] = set()
    deduped: list[Recipe] = []
    for r in filtered:
        key = r.title.lower().strip()
        if key not in seen and len(key) > 2:
            seen.add(key)
            deduped.append(r)
    print(f"  Extracted {len(deduped)} recipes from book #{book_id}")
    return deduped
