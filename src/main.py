"""FastAPI application with routes for homepage, webhook, admin, and API."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config import settings
from src.services.admin import (
    generate_csrf_token,
    get_admin_user,
    make_session_value,
    validate_csrf_token,
    CSRF_COOKIE,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
)
from src.services.sheets import (
    append_product,
    count_all_products,
    delete_product_row,
    read_all_products,
    update_product,
    update_product_caption,
)
from src.services.telegram import router as webhook_router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Affiliate Katalog", version="2.0.0")
app.include_router(webhook_router)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _set_csrf(response, csrf_token):
    """Attach CSRF cookie to a response."""
    response.set_cookie(
        CSRF_COOKIE, csrf_token,
        httponly=True, samesite="strict",
    )


# ── Public Routes ──────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Render the homepage with latest products."""
    try:
        products = read_all_products(
            settings.GOOGLE_SHEETS_CREDENTIALS,
            settings.SPREADSHEET_ID,
            limit=20,
            offset=0,
        )
    except Exception as e:
        log.error(f"Failed to load products: {e}")
        products = []

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "products": products},
    )


@app.get("/api/products")
async def api_products(limit: int = 20, offset: int = 0, q: str = ""):
    """Return paginated products as JSON."""
    try:
        products = read_all_products(
            settings.GOOGLE_SHEETS_CREDENTIALS,
            settings.SPREADSHEET_ID,
            limit=limit,
            offset=offset,
            q=q,
        )
    except Exception as e:
        log.error(f"Failed to load products for API: {e}")
        products = []

    return [p.model_dump() for p in products]


@app.post("/api/captions/generate")
async def api_generate_caption(request: Request):
    """Generate a caption for a product using Gemini (public API)."""
    body = await request.json()
    name = (body.get("name") or "").strip()
    link = (body.get("link") or "").strip()
    price = (body.get("price") or "").strip()

    if not name:
        return JSONResponse({"error": "Nama produk wajib diisi"}, status_code=400)

    from src.services.ai import generate_caption

    try:
        print(name, price)
        caption = await generate_caption(
            name=name, price=price, link=link, platform="other",
        )
        return JSONResponse({"caption": caption})
    except Exception as e:
        log.error(f"Caption generation failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Admin Routes ───────────────────────────────────────────────


@app.get("/login")
async def admin_login(request: Request):
    """Show login page."""
    user = get_admin_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)

    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "show_login": True,
        "show_form": False,
        "form_mode": "",
        "products": [],
        "user": None,
        "q": "",
        "page": 1,
        "csrf_token": csrf_token,
        "error": None,
        "product": {},
        "settings": settings,
    })
    _set_csrf(response, csrf_token)
    return response


@app.post("/login")
async def admin_login_post(request: Request):
    """Process login form."""
    form = await request.form()

    csrf_token = generate_csrf_token()

    if not validate_csrf_token(request, form.get("csrf_token", "")):
        response = templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "show_login": True,
            "error": "CSRF token tidak valid. Coba refresh halaman.",
            "csrf_token": csrf_token,
        })
        _set_csrf(response, csrf_token)
        return response

    username = form.get("username", "").strip()
    password = form.get("password", "").strip()

    if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
        response = templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "show_login": True,
            "error": "Username atau password salah.",
            "csrf_token": csrf_token,
        })
        _set_csrf(response, csrf_token)
        return response

    session_val = make_session_value()
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        SESSION_COOKIE, session_val,
        httponly=True, samesite="strict", max_age=SESSION_MAX_AGE,
    )
    return response


@app.post("/logout")
async def admin_logout(request: Request):
    """Logout and clear session."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.get("/dashboard")
async def admin_dashboard(request: Request, page: int = 1, q: str = ""):
    """Show admin dashboard with product table."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    limit = 20
    offset = (page - 1) * limit

    try:
        products = read_all_products(
            settings.GOOGLE_SHEETS_CREDENTIALS,
            settings.SPREADSHEET_ID,
            limit=limit,
            offset=offset,
            q=q,
        )
        total_count = count_all_products(
            settings.GOOGLE_SHEETS_CREDENTIALS,
            settings.SPREADSHEET_ID,
            q=q,
        )
    except Exception as e:
        log.error(f"Failed to load products: {e}")
        products = []
        total_count = 0

    total_pages = max(1, (total_count + limit - 1) // limit)

    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "show_login": False,
        "show_form": False,
        "form_mode": "",
        "products": products,
        "user": user,
        "q": q,
        "page": page,
        "total_count": total_count,
        "total_pages": total_pages,
        "limit": limit,
        "csrf_token": csrf_token,
        "error": None,
        "product": {},
        "settings": settings,
    })
    _set_csrf(response, csrf_token)
    return response


@app.get("/product/add")
async def admin_product_add_form(request: Request):
    """Show add product form."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "show_login": False,
        "show_form": True,
        "form_mode": "add",
        "products": [],
        "user": user,
        "q": "",
        "page": 1,
        "csrf_token": csrf_token,
        "error": None,
        "product": {"link": "", "name": "", "price": "", "caption": ""},
        "settings": settings,
    })
    _set_csrf(response, csrf_token)
    return response


@app.post("/product/add")
async def admin_product_add_submit(request: Request):
    """Save new product (with optional caption generation)."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()

    if not validate_csrf_token(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/product/add", status_code=303)

    link = (form.get("link") or "").strip()
    name = (form.get("name") or "").strip()
    price = (form.get("price") or "").strip()
    caption = (form.get("caption") or "").strip()

    if not link or not name:
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "show_login": False,
            "show_form": True,
            "form_mode": "add",
            "error": "Link dan nama wajib diisi.",
            "product": {"link": link, "name": name, "price": price, "caption": caption},
            "csrf_token": csrf_token,
        })
        _set_csrf(response, csrf_token)
        return response

    try:
        from src.services.telegram import _format_price

        append_product(
            credentials_json=settings.GOOGLE_SHEETS_CREDENTIALS,
            spreadsheet_id=settings.SPREADSHEET_ID,
            link=link,
            name=name,
            price=_format_price(price),
            caption=caption,
        )

        return RedirectResponse(url="/dashboard", status_code=303)

    except Exception as e:
        log.error(f"Failed to add product: {e}")
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "show_login": False,
            "show_form": True,
            "form_mode": "add",
            "error": f"Gagal menyimpan: {e}",
            "product": {"link": link, "name": name, "price": price, "caption": caption},
            "csrf_token": csrf_token,
        })
        _set_csrf(response, csrf_token)
        return response


@app.get("/product/{pid}/edit")
async def admin_product_edit_form(request: Request, pid: int):
    """Show edit caption form for a product."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    try:
        products = read_all_products(
            settings.GOOGLE_SHEETS_CREDENTIALS,
            settings.SPREADSHEET_ID,
            limit=9999,
            offset=0,
        )
        product = next((p for p in products if p.id == pid), None)
    except Exception as e:
        log.error(f"Failed to load product {pid}: {e}")
        product = None

    if not product:
        return RedirectResponse(url="/dashboard", status_code=303)

    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "show_login": False,
        "show_form": True,
        "form_mode": "edit",
        "products": [],
        "user": user,
        "q": "",
        "page": 1,
        "csrf_token": csrf_token,
        "error": None,
        "product": product.model_dump(),
        "settings": settings,
    })
    _set_csrf(response, csrf_token)
    return response


@app.post("/product/{pid}/edit")
async def admin_product_edit_submit(request: Request, pid: int):
    """Update name, price, and caption for a product."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()

    if not validate_csrf_token(request, form.get("csrf_token", "")):
        return RedirectResponse(url=f"/product/{pid}/edit", status_code=303)

    name = (form.get("name") or "").strip()
    price = (form.get("price") or "").strip()
    caption = (form.get("caption") or "").strip()

    try:
        from src.services.telegram import _format_price

        update_product(
            settings.GOOGLE_SHEETS_CREDENTIALS,
            settings.SPREADSHEET_ID,
            pid,
            name=name or None,
            price=_format_price(price) if price else None,
            caption=caption or None,
        )
    except Exception as e:
        log.error(f"Failed to update product {pid}: {e}")

    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/product/{pid}/delete")
async def admin_product_delete(request: Request, pid: int):
    """Delete a product row from the sheet."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()

    if not validate_csrf_token(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/dashboard", status_code=303)

    try:
        delete_product_row(
            settings.GOOGLE_SHEETS_CREDENTIALS,
            settings.SPREADSHEET_ID,
            pid,
        )
    except Exception as e:
        log.error(f"Failed to delete product {pid}: {e}")

    return RedirectResponse(url="/dashboard", status_code=303)
