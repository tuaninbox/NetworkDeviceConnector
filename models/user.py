from sqlalchemy import Column, Integer, String, Boolean
from core.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    auth_source = Column(String, default="local")  # local, ldap, saml, oidc
    password_hash = Column(String, nullable=True)
    role = Column(String, nullable=False)  # admin, requester, approver, requester_approver
    otp_secret = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
