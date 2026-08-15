from api import device, inventory
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from core.db import Base, engine, AsyncSessionLocal
from core.security import hash_password
# from core.middleware import AuditMiddleware
from models.account import Account

# API Routers
from api import auth, accounts, logs as api_logs

# UI Routers
from ui.routes import (
    auth as ui_auth,
    accounts as ui_accounts,
    devices as ui_devices,
    logs as ui_logs,
)

from core.config_loader import load_config
from core.credential_loader import load_credentials
from core.device_loader import load_devices
from core.role_loader import load_roles
from core.ssh_manager import SSHManager


from fastapi.responses import RedirectResponse


app = FastAPI(title="Network Devices")
# app.add_middleware(AuditMiddleware)


# ---------------------------------------------------------
# Seed admin user
# ---------------------------------------------------------
async def seed_admin_user():
    """
    Create an admin user on first startup if none exists.
    This runs automatically and is idempotent.
    """
    async with AsyncSessionLocal() as db:
        stmt = select(Account).where(Account.username == "admin")
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return  # Admin already exists

        admin_user = Account(
            username="admin",
            email="admin@example.com",
            role="admin",
            password_hash=hash_password("admin123"),
            source="local",
            first_name="Super",
            last_name="Admin",
        )

        db.add(admin_user)
        await db.commit()
        print("✔ Admin user created: username=admin password=admin123")


# ---------------------------------------------------------
# Startup
# ---------------------------------------------------------
@app.on_event("startup")
async def startup():
    # Load configuration
    app.state.config = load_config()
    # Load credentials (ENV → file fallback)
    creds = load_credentials(app.state.config)
    print("✔ Loaded credentials")

    # Merge credentials into config so Nagios loader can use them
    if "devices" in app.state.config and "nagios" in app.state.config["devices"]:
        if "nagios" in creds:
            app.state.config["devices"]["nagios"].update(creds["nagios"])
            print("✔ Merged Nagios credentials into config")

    # Store loader for later use if needed
    app.state.credential_loader = load_credentials
    app.state.ssh_manager = SSHManager(app)
    print("✔ Loaded configuration")

    app.state.roles = load_roles()

    # Create async HTTP client for UI → API calls
    app.state.http_client = httpx.AsyncClient()
    print("✔ HTTP client initialized")

    # Optional: preload devices at startup (still allowed)
    try:
        app.state.devices = await load_devices(app.state.config)
        print(f"✔ Loaded {len(app.state.devices)} devices")
    except Exception as e:
        print("⚠ Device load failed:", e)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed admin user
    await seed_admin_user()


# ---------------------------------------------------------
# Shutdown
# ---------------------------------------------------------
@app.on_event("shutdown")
async def shutdown():
    # Close async HTTP client
    await app.state.http_client.aclose()
    print("✔ HTTP client closed")


# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------

# API Routers
app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(accounts.router)
app.include_router(api_logs.router)
app.include_router(device.router)

# UI Routers
app.include_router(ui_auth.router)
app.include_router(ui_accounts.router)
app.include_router(ui_devices.router)
app.include_router(ui_logs.router)


# ---------------------------------------------------------
# Root redirect
# ---------------------------------------------------------
@app.get("/")
async def root():
    return RedirectResponse(url="/ui/login")
