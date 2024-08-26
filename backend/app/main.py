import os
from fastapi import FastAPI
from app.db.setup_db import is_database_empty, setup_database, fill_database_with_testdata
from app.endpoints.general import router as general_router
from app.endpoints.statement import router as statement_router
from app.endpoints.namedentity import router as namedentity_router
from app.endpoints.topic import router as topic_router

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Uncomment and modify as needed
    # if is_database_empty():
    #     setup_database()
    #     fill_database_with_testdata()
    pass

# Include your routers with distinct prefixes
app.include_router(general_router, prefix="/general", tags=["General"])
app.include_router(namedentity_router, prefix="/namedentity", tags=["Named Entity"])
app.include_router(statement_router, prefix="/statement", tags=["Statement"])
app.include_router(topic_router, prefix="/topic", tags=["Topic"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Listen app API!"}
