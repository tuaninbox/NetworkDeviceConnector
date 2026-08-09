from pydantic import BaseModel
from typing import List, Optional

class AccountRead(BaseModel):
    id: int
    username: str
    role: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    source: str
    profiles: Optional[List[str]]

    class Config:
        from_attributes = True

class AccountCreate(BaseModel):
    username: str
    password: str
    confirm_password: str
    role: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    source: str
    profiles: Optional[List[str]] = []
