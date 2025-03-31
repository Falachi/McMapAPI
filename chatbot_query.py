import re
from fuzzywuzzy import fuzz, process
import spacy
import sqlite3
from spacy.lang.en.stop_words import STOP_WORDS

nlp = spacy.load("en_core_web_sm")

# Define known outlet categories
OUTLET_CATEGORIES = {
    "24 Hours": ["24 hours", "open all day", "always open"],
    "Birthday Party": ["birthday party", "kids party", "celebration"],
    "Breakfast": ["breakfast", "morning menu", "breakfast hours"],
    "Cashless Facility": ["cashless", "no cash", "digital payment"],
    "Dessert Center": ["dessert", "sweets", "ice cream"],
    "Drive-Thru": ["drive-thru", "drive through", "car pickup"],
    "McCafe": ["mccafe", "cafe", "coffee"],
    "McDelivery": ["mcdelivery", "home delivery", "food delivery"],
    "Surau": ["surau", "prayer room", "mosque, masjid"],
    "WiFi": ["wifi", "internet", "free wifi"],
    "Digital Order Kiosk": ["digital kiosk", "self-service kiosk", "order kiosk"],
    "Electric Vehicle": ["electric vehicle", "ev charging", "charging station"],
}

# Define common street-type prefixes to remove
STREET_PREFIXES = ["jalan", "jl", "st", "street", "persiaran", "lorong", "lebuhraya", "avenue", "ave"]

def get_cleaned_locations():
    """Extracts cleaned locations (without street-type words) from database."""
    with sqlite3.connect("mcd_outlets.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT address FROM outlets")
        addresses = [row[0] for row in cursor.fetchall()]

    locations = set()
    
    for address in addresses:
        # Remove postal codes
        address = re.sub(r"\b\d{5}\b", "", address)

        # Split address components
        parts = [part.strip() for part in address.split(",")]

        for part in parts:
            words = part.lower().split()
            
            # Remove street-type words if present
            filtered_words = [word for word in words if word not in STREET_PREFIXES]
            cleaned_part = " ".join(filtered_words).strip()
            
            if cleaned_part:  
                locations.add(cleaned_part.title())  # Capitalize words for consistency

    return list(locations)

# Get cleaned locations from DB
locations = get_cleaned_locations()

def extract_location(query: str):
    """Extracts a potential location from the query using fuzzy matching."""

    # Perform fuzzy matching with known locations
    match, score = process.extractOne(query.title(), locations)
    return match if score > 80 else None

def extract_category(query: str):
    """Extracts categories based on fuzzy matching of keywords."""

    categories = set()  # Initialize an empty set to store categories

    for category, keywords in OUTLET_CATEGORIES.items():
        for keyword in keywords:
            # Perform fuzzy matching with the cleaned query
            if fuzz.partial_ratio(query, keyword) > 80:  # Adjust threshold as needed
                categories.add(category)

    return categories  # Return the set of matched categories


def preprocess_query(query: str) -> str:
    """Preprocesses the query by removing stop words and normalizing it."""
    stop_words = STOP_WORDS  # SpaCy's predefined stop words
    query_cleaned = " ".join([word for word in query.lower().split() if word not in stop_words])
    return query_cleaned.strip()