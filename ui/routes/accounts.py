from urllib import response

from fastapi import APIRouter, Request, Depends, Form, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from deps.auth import get_current_user_optional
from core.security import verify_password, hash_password
from models.account import Account
from core.audit_logger import log_action

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="ui/templates")
templates.env.cache.clear()

async def count_admins(db: AsyncSession) -> int:
    stmt = select(Account).where(Account.role == "admin")
    result = await db.execute(stmt)
    return len(result.scalars().all())


# =============================== Separated =========================

@router.get("/accounts/{user_id}/edit")
async def admin_edit_page(
    user_id: int,
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if current_user is None or current_user.role != "admin":
        log_action(
            current_user,
            "accounts_edit_view",
            "Redirected to login page due to unauthenticated access attempt",
            request,
            category="ui/accounts"
        )
        return RedirectResponse("/ui/login")

    stmt = select(Account).where(Account.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        return RedirectResponse("/ui/accounts")

    log_action(
        current_user,
        "accounts_edit_view",
        "Viewed account edit page",
        request,
        category="ui/accounts"
    )

    return templates.TemplateResponse(
        "account_edit.html",
        {
            "request": request,
            "user": user,       
            "current_user": current_user,
            "error": None,
        },
    )


# Edit account submission (admin)
@router.post("/accounts/{user_id}/edit", response_class=HTMLResponse)
async def accounts_edit_submit_page(
    user_id: int,
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
):
    if current_user is None:
        return RedirectResponse("/ui/login")

    # Extract form fields from frontend POST
    form = await request.form()

    payload = {
        "username": form.get("username"),
        "first_name": form.get("first_name"),
        "last_name": form.get("last_name"),
        "email": form.get("email"),
        "role": form.get("role"),
        "profiles": [p.strip() for p in form.get("profiles").split(",")] if form.get("profiles") else None,
        "new_password": form.get("new_password"),
        "confirm_password": form.get("confirm_password"),
    }

    # Backend API endpoint
    api_url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/api/accounts/{user_id}"

    # Forward cookies (auth)
    cookies = request.cookies

    # Forward POST to backend API
    api_resp = await request.app.state.http_client.post(
        api_url,
        json=payload,
        cookies=cookies
    )

    data = api_resp.json()

    # If backend API returns error → re-render page with error
    if api_resp.status_code != 200:
        # Fetch latest user data again for re-render
        api_get_url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/api/accounts/{user_id}"
        api_user_resp = await request.app.state.http_client.get(api_get_url, cookies=cookies)
        user_data = api_user_resp.json()

        return templates.TemplateResponse(
            "account_edit.html",
            {
                "request": request,
                "current_user": current_user,
                "user": user_data,
                "error": data.get("error") or "Unknown error",
            },
        )

    # Success → redirect to accounts page
    return RedirectResponse("/ui/accounts?success=1", status_code=302)


# Create account submission (admin)
@router.post("/accounts/create", response_class=HTMLResponse)
async def accounts_create_submit_page(
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
):
    if current_user is None:
        return RedirectResponse("/ui/login")

    # Extract form fields
    form = await request.form()

    # Convert profiles string → list
    profiles_raw = form.get("profiles")
    profiles_list = [p.strip() for p in profiles_raw.split(",") if p.strip()] if profiles_raw else []

    # Build payload for backend API
    payload = {
        "username": form.get("username"),
        "password": form.get("password"),
        "confirm_password": form.get("confirm_password"),
        "role": form.get("role"),
        "first_name": form.get("first_name"),
        "last_name": form.get("last_name"),
        "email": form.get("email"),
        "source": form.get("source"),
        "profiles": profiles_list,
    }

    # Backend API endpoint
    api_url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/api/accounts"

    # Forward cookies for authentication
    cookies = request.cookies

    # Forward POST to backend API
    api_resp = await request.app.state.http_client.post(
        api_url,
        json=payload,
        cookies=cookies
    )

    data = api_resp.json()

    # Handle backend errors
    if api_resp.status_code != 200:
        return templates.TemplateResponse(
            "account_create.html",
            {
                "request": request,
                "current_user": current_user,
                "error": data.get("error") or "Unknown error",
                "form_data": payload,
            },
        )

    # Success → redirect to accounts list
    return RedirectResponse("/ui/accounts?success=1", status_code=303)





# ========================= Original ========




@router.get("/accounts", response_class=HTMLResponse)
async def accounts_page(
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if current_user is None:
        log_action(
        current_user,
        "accounts_view",
        "Redirected to login page due to unauthenticated access attempt",
        request,
        category="accounts"
    )

        return RedirectResponse("/ui/login")

    if current_user.role != "admin":
        log_action(
            current_user,
            "accounts_view",
            "Attempted to view accounts list without admin privileges",
            request,
            category="accounts"
        )
        return RedirectResponse("/ui/devices")

    stmt = select(Account)
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    log_action(
        current_user,
        "accounts_view",
        "Viewed accounts list",
        request,
        category="accounts"
    )

    return templates.TemplateResponse(
        "accounts.html",
        {"request": request, "current_user": current_user, "accounts": accounts},
    )

@router.get("/accounts/create")
async def account_create_page(
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
):
    if current_user is None or current_user.role != "admin":
        log_action(
            current_user,
            "accounts_create_view",
            "Redirected to login page due to unauthenticated access attempt",
            request,
            category="accounts"
        )
        return RedirectResponse("/ui/login")

    log_action(
        current_user,
        "accounts_create_view",
        "Viewed account creation page",
        request,
        category="accounts"
    )

    return templates.TemplateResponse(
        "account_create.html",
        {
            "request": request,
            "current_user": current_user,
            "error": None,
        },
    )


@router.post("/accounts/create")
async def accounts_create(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form(...),
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if current_user is None or current_user.role != "admin":
        log_action(
            current_user,
            "accounts_create_submit",
            "Redirected to login page due to unauthenticated access attempt",
            request,
            category="accounts"
        )
        return RedirectResponse("/ui/login")

    # BACKEND PASSWORD VALIDATION
    if password != confirm_password:
        log_action(
            current_user,
            "account_create_failed",
            "Password and confirm password did not match",
            request,
            category="accounts"
        )

        return templates.TemplateResponse(
            "account_create.html",
            {
                "request": request,
                "current_user": current_user,
                "error": "Passwords do not match",
            },
            status_code=400
        )

    hashed = hash_password(password)

    new_user = Account(
        username=username,
        email=email,
        password_hash=hashed,
        role=role,
        auth_source="local",
        is_active=True
    )

    db.add(new_user)
    await db.commit()

    log_action(
        user=current_user,
        action="account_create",
        details=f"Created account {username}",
        request=request,
        category="accounts"
    )

    return RedirectResponse("/ui/accounts", status_code=303)


@router.get("/account/self/edit")
async def account_self_edit_page(
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
):
    if current_user is None:
        log_action(
            current_user,
            "accounts_self_edit_view",
            "Redirected to login page due to unauthenticated access attempt",
            request,
            category="accounts"
        )
        return RedirectResponse("/ui/login")

    log_action(
        current_user,
        "accounts_self_edit_view",
        "Viewed self-edit page",
        request,
        category="accounts"
    )

    return templates.TemplateResponse(
        "account_self_edit.html",
        {
            "request": request,
            "current_user": current_user, 
            "user": current_user,         
            "error": None,
        },
    )



@router.post("/account/self/edit")
async def account_self_edit(
    request: Request,
    username: str = Form(None),
    email: str = Form(None),
    current_password: str = Form(None),
    new_password: str = Form(None),
    confirm_password: str = Form(None),
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if current_user is None:
        log_action(
            current_user,
            "accounts_self_edit_submit",
            "Redirected to login page due to unauthenticated access attempt",
            request,
            category="accounts"
        )
        return RedirectResponse("/ui/login")

    # Must provide current password
    if not current_password or not verify_password(current_password, current_user.password_hash):
        log_action(
            current_user,
            "accounts_self_edit_submit",
            "Current password verification failed during self-edit",
            request,
            category="accounts"
        )
        return templates.TemplateResponse(
            "account_self_edit.html",
            {"request": request, "user": current_user, "error": "Current password is incorrect"},
        )

    # Username uniqueness
    if username and username != current_user.username:
        stmt = select(User).where(User.username == username)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            return templates.TemplateResponse(
                "account_self_edit.html",
                {"request": request, "user": current_user, "error": "Username already exists"},
            )
        current_user.username = username

    # Email update
    if email:
        current_user.email = email

    # Password update
    if new_password:
        if new_password != confirm_password:
            return templates.TemplateResponse(
                "account_self_edit.html",
                {"request": request, "user": current_user, "error": "New passwords do not match"},
            )
        current_user.password_hash = hash_password(new_password)

    await db.commit()
    log_action(
        current_user,
        "accounts_self_edit_submit",
        "Submitted self-edit form",
        request,
        category="accounts"
    )
    return RedirectResponse(f"/ui/account/{current_user.id}?success=1", status_code=302)




@router.post("/accounts/{user_id}/delete")
async def accounts_delete(
    user_id: int,
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if current_user is None or current_user.role != "admin":
        log_action(
            current_user,
            "accounts_delete",
            "Redirected to login page due to unauthenticated access attempt",
            request,
            category="accounts"
        )
        return RedirectResponse("/ui/login")

    # Count admins BEFORE deleting
    admin_count = await count_admins(db)

    stmt = select(Account).where(Account.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Prevent deleting the last admin
    if user and user.role == "admin" and admin_count <= 1:
        # Return table with error message inline
        stmt = select(Account)
        result = await db.execute(stmt)
        accounts = result.scalars().all()

        error_html = """
        <tr class='bg-red-100'>
            <td colspan='3' class='px-4 py-2 text-red-700 font-semibold'>
                Cannot delete the last admin account.
            </td>
        </tr>
        """

        table_html = templates.get_template("partials/accounts_table.html").render(
            request=request,
            accounts=accounts
        )

        return HTMLResponse(error_html + table_html)

    # Safe to delete
    if user:
        await db.delete(user)
        await db.commit()

    # Reload table
    stmt = select(User)
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    log_action(
        current_user,
        "accounts_delete",
        f"Account {user.username} deleted",
        request,
        category="accounts"
    )
    return templates.TemplateResponse(
        "partials/accounts_table.html",
        {"request": request, "accounts": accounts},
    )



@router.get("/accounts/create")
async def account_create_page(
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
):
    if current_user is None or current_user.role != "admin":
        log_action(
            current_user,
            "accounts_create_view",
            "Redirected to login page due to unauthenticated access attempt",
            request,
            category="accounts"
        )
        return RedirectResponse("/ui/login")

    log_action(
        current_user,
        "accounts_create_view",
        "Viewed account creation page",
        request,
        category="accounts"
    )

    return templates.TemplateResponse(
        "account_create.html",
        {
            "request": request,
            "error": None,
            "user": current_user,
        },
    )






@router.get("/accounts/{user_id}/delete-inline")
async def account_delete_inline(
    user_id: int,
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if current_user is None or current_user.role != "admin":
        log_action(
            current_user,
            "accounts_delete_inline",
            "Redirected to login page due to unauthenticated access attempt",
            request,
            category="accounts"
        )
        return RedirectResponse("/ui/login")

    stmt = select(Account).where(Account.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return HTMLResponse("<tr><td colspan='3'>User not found</td></tr>")

    log_action(
        current_user,
        "accounts_delete_inline",
        f"Initiated inline delete confirmation for user {user.username}",
        request,
        category="accounts"
    )
    # Inline confirmation HTML
    html = f"""
    <tr id="row-{user.id}" class="bg-red-50">
      <td class="px-4 py-2" colspan="3">
        <div class="flex justify-between items-center">
          <span>Delete <strong>{user.username}</strong>?</span>

          <div class="space-x-3">
            <button
              class="px-3 py-1 bg-gray-300 rounded"
              hx-get="/ui/accounts"
              hx-target="#accounts-table"
              hx-swap="innerHTML">
              Cancel
            </button>

            <button
              class="px-3 py-1 bg-red-600 text-white rounded"
              hx-post="/ui/accounts/{user.id}/delete"
              hx-target="#accounts-table"
              hx-swap="innerHTML">
              Confirm
            </button>
          </div>
        </div>
      </td>
    </tr>
    """

    return HTMLResponse(html)

@router.get("/account/{user_id}", response_class=HTMLResponse)
async def account_self(
    user_id: int,
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
):
    if current_user is None:
        log_action(
            current_user,
            "accounts_self_view",
            "Redirected to login page due to unauthenticated access attempt",
            request,
            category="accounts"
        )
        return RedirectResponse("/ui/login")

    # requester/approver can only view their own account
    if current_user.role != "admin" and current_user.id != user_id:
        log_action(
            current_user,
            "accounts_self_view",
            "Attempted to view another user's account",
            request,
            category="accounts"
        )
        return RedirectResponse(f"/ui/account/{current_user.id}")

    success = request.query_params.get("success")
    log_action(
        current_user,
        "accounts_self_view",
        f"Viewed own account page",
        request,
        category="accounts"
    )
    return templates.TemplateResponse(
        "account_self.html",
        {
            "request": request,
            "current_user": current_user,
            "user": current_user,  
            "success": "Account updated successfully" if success else None
        },
    )


@router.get("/account/{account_id}/edit", response_class=HTMLResponse)
async def account_edit_page(
    request: Request,
    account_id: int,
    current_user: Account = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    roles = request.app.state.roles

    # Permission check: user can edit themselves OR admin can edit anyone
    if current_user.id != account_id and not has_permission(current_user.role, "update_accounts", roles):
        return RedirectResponse("/ui/login")

    # Fetch account
    result = await db.execute(select(Account).where(Account.id == account_id))
    user = result.scalar_one_or_none()

    if not user:
        return HTMLResponse("Account not found", status_code=404)

    return templates.TemplateResponse(
        "account_edit.html",
        {
            "request": request,
            "user": user,
            "current_user": current_user,
        },
    )

@router.post("/account/{account_id}/edit")
async def account_edit_submit(
    request: Request,
    account_id: int,
    username: str = Form(...),
    first_name: str = Form(None),
    last_name: str = Form(None),
    email: str = Form(None),
    role: str = Form(...),
    source: str = Form(...),
    profiles: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
    current_user: Account = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    roles = request.app.state.roles

    # Permission check
    if current_user.id != account_id and not has_permission(current_user.role, "update_accounts", roles):
        return RedirectResponse("/ui/login")

    # Password validation
    if new_password or confirm_password:
        if new_password != confirm_password:
            return templates.TemplateResponse(
                "account_edit.html",
                {
                    "request": request,
                    "user": current_user,
                    "error": "Passwords do not match",
                },
            )

    # Fetch account
    result = await db.execute(select(Account).where(Account.id == account_id))
    user = result.scalar_one_or_none()

    if not user:
        return HTMLResponse("Account not found", status_code=404)

    # Update fields
    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.role = role
    user.source = source
    user.profiles = [p.strip() for p in profiles.split(",") if p.strip()]

    if new_password:
        user.password_hash = hash_password(new_password)

    await db.commit()

    return RedirectResponse(f"/ui/account/{account_id}", status_code=303)
