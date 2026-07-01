"""Default categories and builtin categorization rules (Canadian context).

Rules are seeded into the DB on first run. Each builtin rule matches a keyword in
the normalized (uppercased) description. Patterns that should *never* be
auto-classified (cash withdrawals, e-transfers, generic descriptions) are handled
by :mod:`bankbot.core.categorize.review`, not here.
"""
from __future__ import annotations

ESSENTIAL = "essential"
WANT = "want"

# (category name, default Essential/Want)
DEFAULT_CATEGORIES: list[tuple[str, str]] = [
    ("Groceries", ESSENTIAL),
    ("Rent/Mortgage", ESSENTIAL),
    ("Utilities", ESSENTIAL),
    ("Phone/Internet", ESSENTIAL),
    ("Insurance", ESSENTIAL),
    ("Healthcare", ESSENTIAL),
    ("Transport", ESSENTIAL),
    ("Bank Fees", ESSENTIAL),
    ("Subscriptions", WANT),
    ("Dining", WANT),
    ("Entertainment", WANT),
    ("Shopping", WANT),
    ("Cash Withdrawal", WANT),   # forced to review before this default applies
    ("Transfer", WANT),          # forced to review
    ("Uncategorized", WANT),
]

# category -> list of uppercase keyword fragments
_KEYWORDS: dict[str, list[str]] = {
    "Groceries": [
        "LOBLAW", "NO FRILLS", "NOFRILLS", "METRO", "SOBEYS", "COSTCO", "WALMART",
        "FRESHCO", "FOOD BASICS", "SUPERSTORE", "SAVE-ON", "SAVE ON FOODS",
        "WHOLE FOODS", "FARM BOY", "LONGO", "T&T", "GROCERY",
    ],
    "Utilities": [
        "HYDRO", "ENBRIDGE", "ENMAX", "EPCOR", "FORTIS", "UTILITY", "WATER",
        "ELECTRIC", "GAS BILL",
    ],
    "Phone/Internet": [
        "ROGERS", "BELL", "TELUS", "FIDO", "KOODO", "VIRGIN", "FREEDOM MOBILE",
        "SHAW", "VIDEOTRON", "TEKSAVVY", "INTERNET",
    ],
    "Insurance": [
        "INSURANCE", "SUN LIFE", "MANULIFE", "INTACT", "ALLSTATE", "TD INSURANCE",
        "BELAIR", "AVIVA",
    ],
    "Healthcare": [
        "SHOPPERS DRUG", "PHARMA", "DENTAL", "CLINIC", "REXALL", "MEDICAL",
        "PHYSIO", "OPTOMETR",
    ],
    "Transport": [
        "PETRO", "ESSO", "SHELL", "CHEVRON", "HUSKY", "UBER", "LYFT", "PRESTO",
        "GO TRANSIT", "TTC", "PARKING", "TRANSIT", "VIA RAIL", "GAS STATION",
    ],
    "Bank Fees": [
        "MONTHLY FEE", "OVERDRAFT", "NSF", "SERVICE CHARGE", "ACCOUNT FEE",
        "ANNUAL FEE",
    ],
    "Subscriptions": [
        "NETFLIX", "SPOTIFY", "DISNEY", "AMAZON PRIME", "APPLE.COM/BILL",
        "APPLE.COM", "GOOGLE", "CRAVE", "YOUTUBE PREMIUM", "AUDIBLE", "ADOBE",
        "MICROSOFT", "PATREON",
    ],
    "Dining": [
        "TIM HORTONS", "MCDONALD", "STARBUCKS", "UBER EATS", "UBEREATS",
        "DOORDASH", "SKIP", "SKIPTHEDISHES", "RESTAURANT", "PIZZA", "SUBWAY",
        "A&W", "WENDY", "BURGER", "CAFE", "BAR &",
    ],
    "Entertainment": [
        "CINEPLEX", "STEAM", "PLAYSTATION", "XBOX", "NINTENDO", "TICKETMASTER",
        "CONCERT", "EVENTBRITE", "GOLF", "CINEMA",
    ],
    "Shopping": [
        "AMAZON.CA", "AMAZON.COM", "AMZN", "BEST BUY", "CANADIAN TIRE", "IKEA",
        "INDIGO", "WINNERS", "HOMESENSE", "THE BAY", "SEPHORA", "LULULEMON",
    ],
    "Rent/Mortgage": [
        "RENT", "PROPERTY MGMT", "PROPERTY MANAGEMENT", "MORTGAGE", "LANDLORD",
    ],
}

# Some keywords are stronger/more specific than others -> higher confidence.
_STRONG = {
    "NETFLIX", "SPOTIFY", "TIM HORTONS", "MCDONALD", "STARBUCKS", "UBER EATS",
    "DOORDASH", "CINEPLEX", "SHOPPERS DRUG", "NO FRILLS", "LOBLAW", "COSTCO",
    "PRESTO", "ROGERS", "BELL", "TELUS", "ENBRIDGE", "AMAZON PRIME",
}


def default_rule_rows() -> list[dict]:
    """Builtin keyword rules as kwargs for :class:`~bankbot.core.models.Rule`."""
    cat_default = {name: ess for name, ess in DEFAULT_CATEGORIES}
    rows: list[dict] = []
    for category, keywords in _KEYWORDS.items():
        ess = cat_default.get(category, WANT)
        recurring = category in {"Subscriptions", "Utilities", "Phone/Internet",
                                 "Insurance", "Rent/Mortgage"}
        for kw in keywords:
            rows.append(
                dict(
                    match_type="keyword",
                    pattern=kw,
                    category=category,
                    essential_want=ess,
                    is_recurring_bill=recurring,
                    priority=110 if kw in _STRONG else 100,
                    source="builtin",
                )
            )
    return rows
