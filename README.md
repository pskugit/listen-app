# Listen App

The **Listen App** is designed to help swiftly take notes about the people you care about, enabling you to retrieve anecdotes and important information in future interactions. The app emphasizes attentiveness, awareness, and memory, allowing you to maintain meaningful connections through the details you've captured.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Note Taking**: Add and manage notes (so called 'statements') for individuals.
- **Anecdote Retrieval**: Retrieve important details during interactions to foster deeper connections.
- **Graph Database**: Utilizes Neo4j for efficient data storage and retrieval.
- **Mobile Compatibility**: Built with React Native for a smooth mobile experience.

## Tech Stack

- **Frontend**: 
  - **React Native**: For building the mobile application.
  
- **Backend**: 
  - **FastAPI**: For creating the RESTful API.
  - **Python**: Primary language for the backend logic.
  - **Neo4j**: Graph database for storing and managing notes and relationships.
  
- **Development Tools**:
  - **Docker**: For containerization of the application.
  - **Docker Compose**: For managing multi-container Docker applications.

## Project Structure

```
listen-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # Entry point for FastAPI
│   │   ├── models.py        # Pydantic models
│   │   ├── endpoints/
│   │   │   ├── named_entities.py  # Endpoints for NamedEntity
│   │   │   └── statements.py       # Endpoints for Statement
│   │   └── db/
│   │       └── setup_db.py        # Database setup scripts
│   ├── Dockerfile
│   ├── requirements.txt    # Python dependencies
│   └── tests/
│       └── test_endpoints.py # API tests
├── frontend/
│   ├── App.js               # Entry point for React Native
│   ├── src/
│   │   ├── config.js        # Configuration settings
│   │   ├── components/       # Reusable components
│   │   ├── screens/          # Different screens/views
│   │   └── services/         # API service handling
├── docker-compose.yml        # Compose file to run both backend and frontend
└── README.md                # Project documentation
```

## Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd listen-app
   ```

2. **Set Up the Backend**:
   - Navigate to the backend directory:
     ```bash
     cd backend
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

3. **Set Up the Frontend**:
   - Navigate to the frontend directory:
     ```bash
     cd frontend
     ```
   - Install dependencies:
     ```bash
     npm install
     ```

4. **Run with Docker**:
   - Start the application with Docker:
     ```bash
     docker-compose up --build
     ```

## Usage

- Access the FastAPI documentation at `http://0.0.0.0:8000/docs` to explore available API endpoints.
- Use the Neo4j browser at `http://localhost:7474/` to manage your graph database.

## API Endpoints

- **Add Named Entity**: `POST /add_namedentity/`
- **Add Statement**: `POST /add_statement/`
- **Test Connection**: `GET /test_connection`
- **Root Endpoint**: `GET /` for a welcome message.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.