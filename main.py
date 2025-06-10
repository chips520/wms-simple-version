from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional
import logging
from datetime import datetime

import database
import models

from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Application startup: Creating database table if it doesn't exist.")
    database.create_table()
    yield
    # Shutdown logic (if any)
    logger.info("Application shutdown.")

app = FastAPI(title="WMS Service", version="1.0.0", lifespan=lifespan)

# Dependency to get DB connection (though database functions manage their own)
# This is more for consistency or if we wanted to pass sessions around.
# For now, database functions are self-contained.
async def get_db():
    # In a real async setup, this would be an async connection pool
    db = database.get_db_connection()
    try:
        yield db
    finally:
        db.close()

# @app.on_event("startup") # Replaced by lifespan
# async def startup_event():
#     logger.info("Application startup: Creating database table if it doesn't exist.")
#     database.create_table()

@app.post("/locations/", response_model=models.MaterialLocation, status_code=201)
async def create_location(location: models.MaterialLocationCreate):
    logger.info(f"Received request to create location: {location.model_dump()}")
    db_location = database.create_material_location(location)
    logger.info(f"Created location with ID: {db_location.LocationID}")
    return db_location

@app.get("/locations/", response_model=List[models.MaterialLocation])
async def read_locations(skip: int = 0, limit: int = 100):
    logger.info(f"Received request to read locations: skip={skip}, limit={limit}")
    locations = database.get_material_locations(skip=skip, limit=limit)
    logger.info(f"Found {len(locations)} locations.")
    return locations

@app.get("/locations/{location_id}", response_model=models.MaterialLocation)
async def read_location(location_id: int):
    logger.info(f"Received request to read location with ID: {location_id}")
    db_location = database.get_material_location(location_id)
    if db_location is None:
        logger.warning(f"Location with ID {location_id} not found.")
        raise HTTPException(status_code=404, detail="Location not found")
    logger.info(f"Found location: {db_location.model_dump()}")
    return db_location

@app.put("/locations/{location_id}", response_model=models.MaterialLocation)
async def update_location(location_id: int, location: models.MaterialLocationUpdate):
    logger.info(f"Received request to update location ID {location_id} with data: {location.model_dump(exclude_unset=True)}")
    updated_location = database.update_material_location(location_id, location)
    if updated_location is None:
        logger.warning(f"Location with ID {location_id} not found for update.")
        raise HTTPException(status_code=404, detail="Location not found")
    logger.info(f"Updated location ID {location_id}: {updated_location.model_dump()}")
    return updated_location

@app.delete("/locations/{location_id}", status_code=204)
async def delete_location(location_id: int):
    logger.info(f"Received request to delete location ID {location_id}")
    success = database.delete_material_location(location_id)
    if not success:
        logger.warning(f"Location with ID {location_id} not found for deletion.")
        raise HTTPException(status_code=404, detail="Location not found")
    logger.info(f"Successfully deleted location ID {location_id}")
    return Response(status_code=204) # FastAPI expects a Response for 204

@app.post("/locations/batch-update/", response_model=List[models.MaterialLocation])
async def batch_update_locations(request: models.BatchUpdateRequest):
    logger.info(f"Received request for batch update: {len(request.updates)} items.")
    updated_locations = []
    for item in request.updates:
        updated_location = database.update_material_location(item.LocationID, item.data)
        if updated_location is None:
            logger.warning(f"Location with ID {item.LocationID} not found during batch update.")
            # Decide if to raise error or skip. For now, skip and don't include in response.
            # Or, collect errors and return a summary.
            # For simplicity, we'll skip non-existent ones.
            continue
        updated_locations.append(updated_location)
    logger.info(f"Batch update processed. {len(updated_locations)} locations updated.")
    return updated_locations

@app.post("/locations/clear-one/", response_model=models.MaterialLocation)
async def clear_one_location(request: models.ClearLocationRequest):
    logger.info(f"Received request to clear location ID: {request.LocationID}")
    cleared_location = database.clear_material_location(request.LocationID)
    if cleared_location is None:
        logger.warning(f"Location with ID {request.LocationID} not found for clearing.")
        raise HTTPException(status_code=404, detail="Location not found")
    logger.info(f"Cleared location ID {request.LocationID}: {cleared_location.model_dump()}")
    return cleared_location

@app.post("/locations/batch-clear/", response_model=List[models.MaterialLocation])
async def batch_clear_locations(request: models.BatchClearLocationRequest):
    logger.info(f"Received request for batch clear: {len(request.LocationIDs)} IDs.")
    cleared_locations = []
    for loc_id in request.LocationIDs:
        cleared_location = database.clear_material_location(loc_id)
        if cleared_location is None:
            logger.warning(f"Location with ID {loc_id} not found during batch clear.")
            # Similar to batch update, skipping non-existent ones.
            continue
        cleared_locations.append(cleared_location)
    logger.info(f"Batch clear processed. {len(cleared_locations)} locations cleared.")
    return cleared_locations

# Need to import Response for 204 status code
from fastapi import Response
# Add uvicorn runner for local testing if needed.
# if __name__ == "__main__":
# import uvicorn
# uvicorn.run(app, host="0.0.0.0", port=8000)
