from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.security import (
    SESSION_COOKIE,
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
    get_current_admin,
    verify_credentials,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/dashboard/templates")


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str | None = None):
    if get_current_admin(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
def login_submit(username: str = Form(...), password: str = Form(...)):
    if not verify_credentials(username, password):
        return RedirectResponse(url="/login?error=1", status_code=303)
    token = create_session_token(username)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_MAX_AGE_SECONDS, httponly=True, samesite="lax"
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
