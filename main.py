from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from chatbot_query import extract_category, extract_location, preprocess_query
import spacy
import sqlite3
import os

# Create an instance of the FastAPI application
app = FastAPI()

# Load spaCy NLP model (small English model for efficiency)
nlp = spacy.load("en_core_web_sm")

# Read allowed origin from .env
allowed_origin = os.getenv("ALLOWED_ORIGIN", "*")  # Default to "*" if not set

# Configure CORS (Cross-Origin Resource Sharing) middleware
# This allows the frontend application to communicate with the backend API through localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin], # Read from .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_dir = "mcd_outlets.db"


# Define a route to fetch outlets from the database
# Returns a list of all outlets as a JSON response
@app.get("/outlets")
def get_outlets() -> dict:
  # Connect to the SQLite database
  with sqlite3.connect(db_dir) as conn:
    conn.row_factory = sqlite3.Row  # This allows fetching rows as dictionaries
    cursor = conn.cursor()
    # Execute a query to select all records from the 'outlets' table
    cursor.execute("SELECT * FROM outlets")
    # Fetch all the results from the query
    outlets = [dict(row) for row in cursor.fetchall()]  # Convert rows to dictionaries
  # Return the fetched outlets as a JSON response
  return {"outlets": outlets}

# Define a route to fetch outlets based on a search query
# The search is case-insensitive and matches any part of the outlet name
# Returns a list of outlets that match the search query
@app.get("/outlets/search")
def search_outlets(query: str) -> dict:
  # Connect to the SQLite database
  with sqlite3.connect(db_dir) as conn:
    conn.row_factory = sqlite3.Row  # This allows fetching rows as dictionaries
    cursor = conn.cursor()
    # Execute a query to search for outlets where the name matches the query (case-insensitive)
    cursor.execute("""
      SELECT * FROM outlets WHERE LOWER(name) LIKE LOWER(?)
    """, (f"%{query.lower()}%",))
    # Fetch all the results from the query
    outlets = [dict(row) for row in cursor.fetchall()]  # Convert rows to dictionaries
  # Return the fetched outlets as a JSON response
  return {"outlets": outlets}

@app.get("/outlets/category/location")
def get_outlet_by_category_and_location(categories: str, location: str) -> dict:
    """Fetch outlets that match BOTH category and location criteria."""
    with sqlite3.connect(db_dir) as conn:
        conn.row_factory = sqlite3.Row  
        cursor = conn.cursor()

        # Split the category string back into a list
        category_list = categories.split(",")

        # Base SQL query
        query = """
            SELECT o.* FROM outlets o
            JOIN categories c ON o.id = c.outlet_id
            WHERE LOWER(o.address) LIKE LOWER(?)
        """

        # Dynamically add category filters using `IN` for efficiency
        if category_list:
            placeholders = ", ".join(["?"] * len(category_list))  # Creates (?, ?, ?)
            query += f" AND LOWER(c.category) IN ({placeholders})"

        # Execute the query with parameters
        params = [f"%{location.lower()}%"] + [cat.lower() for cat in category_list]
        cursor.execute(query, params)

        # Convert results into dictionaries
        outlets = [dict(row) for row in cursor.fetchall()]

    return {"outlets": outlets}


@app.get("/outlets/location/{location}")
def get_outlets_by_location(location: str) -> dict:
    # Connect to the SQLite database
    with sqlite3.connect(db_dir) as conn:
        conn.row_factory = sqlite3.Row  # Allows fetching rows as dictionaries
        cursor = conn.cursor()

        # Query to search for the location within the address field
        cursor.execute("""
            SELECT * FROM outlets WHERE LOWER(address) LIKE ?
        """, (f"%{location.lower()}%",))

        # Fetch results and convert rows to dictionaries
        outlets = [dict(row) for row in cursor.fetchall()]

    # Return fetched outlets
    return {"outlets": outlets} if outlets else {"message": "No outlets found in this location."}


# Define a route to fetch nearby outlets based on latitude, longitude, and radius
# The haversine formula is used to calculate the distance between two points on the Earth's surface
# Default radius is set to 5 km
# Returns a list of outlets within the specified radius
@app.get("/outlets/nearby")
def get_nearby_outlets(lat: float, lng: float, radius_km: float = 5) -> dict:
  # Connect to the SQLite database
  with sqlite3.connect(db_dir) as conn:
    conn.row_factory = sqlite3.Row  # This allows fetching rows as dictionaries
    cursor = conn.cursor()
    # Execute a query to calculate the distance of outlets from the given coordinates
    # and filter outlets within the specified radius (in kilometers)
    cursor.execute("""
      SELECT *, 
      (6371 * acos(
        cos(radians(?)) * cos(radians(lat)) * 
        cos(radians(lng) - radians(?)) + 
        sin(radians(?)) * sin(radians(lat))
      )) AS distance
      FROM outlets
      WHERE distance <= ?
      ORDER BY distance ASC
    """, (lat, lng, lat, radius_km))
    # Fetch all the results from the query
    outlets = [dict(row) for row in cursor.fetchall()]  # Convert rows to dictionaries
  # Return the fetched outlets as a JSON response
  return {"outlets": outlets}

# Define a route to fetch a specific outlet by its ID
# The ID is expected to be an integer
# Returns the outlet details as a dictionary
@app.get("/outlets/{outlet_id}")
def get_outlet(outlet_id: int) -> dict:
  # Connect to the SQLite database
  with sqlite3.connect(db_dir) as conn:
    conn.row_factory = sqlite3.Row  # This allows fetching rows as dictionaries
    cursor = conn.cursor()
    # Execute a query to select a specific outlet by its ID
    cursor.execute("SELECT * FROM outlets WHERE id = ?", (outlet_id,))
    # Fetch the result from the query
    outlet = cursor.fetchone()
  # Return the fetched outlet as a JSON response
  return {"outlet": outlet}

# Define a route to fetch outlets by category from the database
# The category is case-insensitive
# Returns a list of outlets as dictionary that belong to the specified category
@app.get("/outlets/category/{category}")
def get_outlets_by_category(categories: list) -> dict:
    """Fetch outlets that match multiple categories."""
    if not categories:
        return {"outlets": []}  # Return empty if no categories are provided

    with sqlite3.connect(db_dir) as conn:
        conn.row_factory = sqlite3.Row  
        cursor = conn.cursor()

        # Prepare dynamic placeholders for categories
        placeholders = ", ".join(["?" for _ in categories])

        # SQL query to find outlets that match any of the given categories
        query = f"""
            SELECT DISTINCT o.* FROM outlets o
            JOIN categories c ON o.id = c.outlet_id
            WHERE LOWER(c.category) IN ({placeholders})
        """

        cursor.execute(query, [category.lower() for category in categories])  # Convert to lowercase for case-insensitive matching
        outlets = [dict(row) for row in cursor.fetchall()]

    return {"outlets": outlets}


# Define a route to fetch the services offered by a specific outlet
# Returns a list of services (categories) associated with the outlet ID
@app.get("/outlets/{outlet_id}/services")
def get_outlet_services(outlet_id: int) -> dict:
  # Connect to the SQLite database
  with sqlite3.connect(db_dir) as conn:
    cursor = conn.cursor()
    # Execute a query to select all categories (services) for the given outlet ID
    cursor.execute("""
      SELECT category FROM categories WHERE outlet_id = ?
    """, (outlet_id,))
    # Extract the services from the query results
    services = [row[0] for row in cursor.fetchall()]
  # Return the outlet ID and its services as a JSON response
  return {"outlet_id": outlet_id, "services": services}

# Define a route to fetch information relating to the user's query.
# Currently using rule-based. Need to implement a more advanced NLP model for better understanding of queries
@app.get("/chatbot/query")
def chatbot_query(query: str) -> dict:
    """Handles user queries using fuzzy matching and NLP."""
    query = query.lower()  # Normalize query

    query = preprocess_query(query)  # Preprocess the query
    print(f"Preprocessed Query: {query}")

    # Extract categories & location from query
    categories = extract_category(query)  # Returns a set of categories
    location = extract_location(query)  # Extracts location (can be None)

    # Get all matching outlets
    if categories and location:
        print('Both categories and location provided')
        category_string = ",".join(categories)  # Convert set to comma-separated string
        outlets = get_outlet_by_category_and_location(category_string, 
        location)
        return process_outlets_to_message(outlets)
    elif categories:
        print('Only categories provided')
        outlets = get_outlets_by_category(list(categories))
        return process_outlets_to_message(outlets)
    elif location:
        print('Only location provided')
        outlets = get_outlets_by_location(location)
        return process_outlets_to_message(outlets)

    return {
        "message": "Sorry, I can't find results for your request."
                    " If you think you made a mistake, please try again.\n"
                   "Please try something like:\n"
                   "- 'Which outlets are 24 hours?'\n"
                   "- 'Which outlets are in Bukit Bintang?'\n"
                   "- 'Which 24-hour outlets are in Bukit Bintang?'"
    }

# Define a function to process the outlets and format them into a message
# This function is called when the chatbot query returns results
def process_outlets_to_message(outlets: dict) -> dict:
    outlet_list = outlets.get("outlets", [])  # Extract the list of outlets safely

    if not outlet_list:
        return {"message": "No outlets found for your request."}

    message = "Here are the outlets I found:\n\n"
    for outlet in outlet_list:
        name = outlet['name'].strip()  # Remove spaces before/after the name
        address = outlet['address'].strip()  # Remove spaces before/after the address
        message += f"{name}\n{address}\n\n"  # Name on top, address below

    message += "If you need more information, please let me know!"
    return {"message": message}