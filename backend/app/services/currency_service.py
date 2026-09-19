from typing import Dict


CURRENCY_MAP: Dict[str, Dict[str, str]] = {
    "India": {
        "code": "INR",
        "symbol": "₹",
    },
    "Japan": {
        "code": "JPY",
        "symbol": "¥",
    },
    "United Kingdom": {
        "code": "GBP",
        "symbol": "£",
    },
    "France": {
        "code": "EUR",
        "symbol": "€",
    },
    "Germany": {
        "code": "EUR",
        "symbol": "€",
    },
    "Italy": {
        "code": "EUR",
        "symbol": "€",
    },
    "Spain": {
        "code": "EUR",
        "symbol": "€",
    },
    "United States": {
        "code": "USD",
        "symbol": "$",
    },
    "Canada": {
        "code": "CAD",
        "symbol": "C$",
    },
    "Australia": {
        "code": "AUD",
        "symbol": "A$",
    },
    "Singapore": {
        "code": "SGD",
        "symbol": "S$",
    },
    "UAE": {
        "code": "AED",
        "symbol": "د.إ",
    },
}


# Common destination cities.
# Used when the user enters only a city name.
CITY_COUNTRY_MAP: Dict[str, str] = {
    # India
    "mumbai": "India",
    "delhi": "India",
    "new delhi": "India",
    "pune": "India",
    "bangalore": "India",
    "bengaluru": "India",
    "hyderabad": "India",
    "chennai": "India",
    "kolkata": "India",
    "nagpur": "India",
    "nashik": "India",
    "jaipur": "India",
    "ahmedabad": "India",
    "surat": "India",
    "goa": "India",
    "panaji": "India",
    "agra": "India",
    "varanasi": "India",
    "udaipur": "India",
    "amritsar": "India",
    "lucknow": "India",
    "kochi": "India",
    "mysore": "India",
    "mysuru": "India",

    # Japan
    "tokyo": "Japan",
    "osaka": "Japan",
    "kyoto": "Japan",
    "hiroshima": "Japan",
    "nara": "Japan",
    "sapporo": "Japan",
    "yokohama": "Japan",

    # France
    "paris": "France",
    "lyon": "France",
    "nice": "France",
    "marseille": "France",
    "bordeaux": "France",
    "toulouse": "France",

    # United Kingdom
    "london": "United Kingdom",
    "manchester": "United Kingdom",
    "birmingham": "United Kingdom",
    "liverpool": "United Kingdom",
    "edinburgh": "United Kingdom",
    "glasgow": "United Kingdom",

    # Germany
    "berlin": "Germany",
    "munich": "Germany",
    "hamburg": "Germany",
    "frankfurt": "Germany",
    "cologne": "Germany",

    # Italy
    "rome": "Italy",
    "milan": "Italy",
    "venice": "Italy",
    "florence": "Italy",
    "naples": "Italy",

    # Spain
    "madrid": "Spain",
    "barcelona": "Spain",
    "seville": "Spain",
    "valencia": "Spain",

    # United States
    "new york": "United States",
    "new york city": "United States",
    "los angeles": "United States",
    "san francisco": "United States",
    "chicago": "United States",
    "las vegas": "United States",
    "miami": "United States",
    "boston": "United States",
    "seattle": "United States",
    "washington dc": "United States",
    "washington, dc": "United States",

    # Canada
    "toronto": "Canada",
    "vancouver": "Canada",
    "montreal": "Canada",
    "calgary": "Canada",

    # Australia
    "sydney": "Australia",
    "melbourne": "Australia",
    "brisbane": "Australia",
    "perth": "Australia",

    # Singapore
    "singapore": "Singapore",

    # UAE
    "dubai": "UAE",
    "abu dhabi": "UAE",
}


# Common country aliases.
COUNTRY_ALIASES: Dict[str, str] = {
    "india": "India",
    "japan": "Japan",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "united kingdom": "United Kingdom",
    "england": "United Kingdom",
    "france": "France",
    "germany": "Germany",
    "italy": "Italy",
    "spain": "Spain",
    "usa": "United States",
    "u.s.a.": "United States",
    "us": "United States",
    "u.s.": "United States",
    "united states": "United States",
    "canada": "Canada",
    "australia": "Australia",
    "singapore": "Singapore",
    "uae": "UAE",
    "united arab emirates": "UAE",
}


def get_country_for_destination(destination: str) -> str:
    """
    Determine the country from a destination.

    Examples:
        Tokyo -> Japan
        Tokyo, Japan -> Japan
        Mumbai -> India
        Mumbai, India -> India
        London, UK -> United Kingdom
    """

    if not destination:
        return "United States"

    destination_clean = destination.strip().lower()

    # 1. Exact city lookup
    if destination_clean in CITY_COUNTRY_MAP:
        return CITY_COUNTRY_MAP[destination_clean]

    # 2. Check city names contained in destination.
    # Example: "Tokyo, Japan" -> Japan
    for city, country in CITY_COUNTRY_MAP.items():
        if city in destination_clean:
            return country

    # 3. Check country names and aliases.
    # Example: "Kyoto, Japan" -> Japan
    for alias, country in COUNTRY_ALIASES.items():
        if alias in destination_clean:
            return country

    # 4. Check canonical currency-map country names.
    for country in CURRENCY_MAP:
        if country.lower() in destination_clean:
            return country

    # Keep USD as the final fallback only when the destination
    # cannot be identified from the local mapping.
    return "United States"


def get_currency_for_country(country: str) -> Dict[str, str]:
    """
    Return the currency code and symbol for a country.
    """

    if not country:
        return CURRENCY_MAP["United States"]

    country_clean = country.strip()

    return CURRENCY_MAP.get(
        country_clean,
        CURRENCY_MAP["United States"],
    )


def get_currency_for_destination(destination: str) -> Dict[str, str]:
    """
    Determine the local currency directly from a destination.

    Examples:
        Tokyo -> JPY
        Tokyo, Japan -> JPY
        Paris -> EUR
        Mumbai -> INR
        London, UK -> GBP
    """

    country = get_country_for_destination(destination)

    return get_currency_for_country(country)