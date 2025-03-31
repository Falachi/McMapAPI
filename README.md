# Mindhive Assessment - Backend

## Project Overview

This is the backend service for the Mindhive Assessment project, built using FastAPI. It provides APIs and handles business logic for the application.

## Features

- RESTful API endpoints
- Database integration
- Authentication and authorization

## Requirements

- Python (v3.8 or higher)
- pip (latest version)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Falachi/McMapAPI.git
```

2. Navigate to the project directory:

```bash
cd McMapAPI
```

3. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Create a `.env` folder and put in the allowed origin URL.
```
ALLOWED_ORIGIN={YOUR URL HERE}
```
## Usage

1. Start the development server:

```bash
uvicorn main:app --reload
```

2. Access the API documentation at `http://localhost:8000/docs`.
