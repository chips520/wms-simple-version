from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MaterialLocationBase(BaseModel):
    MaterialID: Optional[str] = None
    TrayNumber: Optional[str] = None
    ProcessID: Optional[str] = None
    TaskID: Optional[str] = None
    StatusNotes: Optional[str] = None

class MaterialLocationCreate(MaterialLocationBase):
    pass

class MaterialLocation(MaterialLocationBase):
    LocationID: int
    Timestamp: datetime

    model_config = {"from_attributes": True}

class MaterialLocationUpdate(BaseModel):
    MaterialID: Optional[str] = None
    TrayNumber: Optional[str] = None
    ProcessID: Optional[str] = None
    TaskID: Optional[str] = None
    StatusNotes: Optional[str] = None

class BatchUpdateItem(BaseModel):
    LocationID: int
    data: MaterialLocationUpdate

class BatchUpdateRequest(BaseModel):
    updates: List[BatchUpdateItem]

class ClearLocationRequest(BaseModel):
    LocationID: int

class BatchClearLocationRequest(BaseModel):
    LocationIDs: List[int]

class ClearByMaterialTrayRequest(BaseModel):
    MaterialID: str
    TrayNumber: str
