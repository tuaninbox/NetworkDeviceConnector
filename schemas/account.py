from pydantic import BaseModel
from typing import List, Optional

class AccountBase(BaseModel):
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    role: str = "user"
    source: str = "local"
    profiles: Optional[List[str]] = None

class AccountRead(AccountBase):
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    role: str = "user"
    source: str = "local"
    profiles: Optional[List[str]] = None

    class Config:
        from_attributes = True

class AccountCreate(AccountBase):
    password: str
    confirm_password: str

    class Config:
        from_attributes = True

class AccountUpdate(AccountBase):
    new_password: Optional[str] = None
    confirm_password: Optional[str] = None

    class Config:
        from_attributes = True
