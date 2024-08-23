from fastapi import FastAPI
from app.db.setup_db import setup_database, fill_database_with_testdata  # Make sure to import the driver
from app.endpoints import router as endpoints_router

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    setup_database()
    fill_database_with_testdata()

# Include your endpoints router
app.include_router(endpoints_router)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Listen app API!"}
