import os
from fastapi import FastAPI
from app.db.setup_db import is_database_empty, setup_database, fill_database_with_testdata  # Make sure to import the driver
from app.endpoints import router as endpoints_router

app = FastAPI()

@app.on_event("startup")
async def startup_event():
        #print("Database is filled initally since there is no backup file")
        #setup_database()
        #fill_database_with_testdata()
        pass


# Include your endpoints router
app.include_router(endpoints_router)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Listen app API!"}
