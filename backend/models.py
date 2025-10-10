from pydantic import BaseModel
from typing import List, Optional

class Contact(BaseModel):
    id: Optional[int] = None
    name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    post: Optional[str] = None
    company_id: Optional[int] = None

class Company(BaseModel):
    id: Optional[int] = None
    title: str
    phone: Optional[str] = None
    email: Optional[str] = None
    contacts: List[Contact] = []

class CreateTestDataRequest(BaseModel):
    session_id: str