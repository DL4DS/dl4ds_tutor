from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from chainlit.utils import mount_chainlit
from chainlit_app import start_chainlit_app
from chainlit_instructor_app import start_chainlit_instructor_app
import secrets

import os
from fastapi import FastAPI
from chainlit.config import config, load_module
from chainlit.server import combined_asgi_app as chainlit_app
from chainlit.utils import check_file, ensure_jwt_secret


app = FastAPI()
templates = Jinja2Templates(directory="templates")
session_store = {}
CHAINLIT_PATH = "/chainlit_tutor"
CHAINLIT_INSTRUCTOR_PATH = "/chainlit_instructor"


USER_ROLES = {
    "tgardos@example.com": "instructor",
    # Add more users and roles as needed
}


def get_user_role(username: str):
    return USER_ROLES.get(username, "student")  # Default to "student" role


def get_username(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token and session_token in session_store:
        return session_store[session_token]
    return None


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login/guest")
async def login_guest():
    username = "guest"
    session_token = secrets.token_hex(16)
    session_store[session_token] = username
    response = RedirectResponse(url="/post-signin", status_code=303)
    response.set_cookie(key="session_token", value=session_token)
    return response


@app.get("/login/google")
async def login_google():
    # Redirect to Google OAuth endpoint (replace with actual URL)
    return RedirectResponse(url="/auth/google")


@app.get("/auth/google")
async def auth_google(request: Request):
    # This is a placeholder for the OAuth callback
    # In a real implementation, extract the Google-provided token and fetch user info
    username = "tgardos@example.com"  # Replace with actual username fetched from Google
    session_token = secrets.token_hex(16)
    session_store[session_token] = username
    response = RedirectResponse(url="/post-signin", status_code=303)
    response.set_cookie(key="session_token", value=session_token)
    return response


@app.get("/post-signin", response_class=HTMLResponse)
async def post_signin(request: Request, username: str = Depends(get_username)):
    if username:
        role = get_user_role(username)
        return templates.TemplateResponse(
            "dashboard.html", {"request": request, "username": username, "role": role}
        )
    return RedirectResponse("/")


@app.post("/start-tutor")
async def start_tutor(request: Request):
    username = get_username(request)
    if username:
        await start_chainlit_app(username)
        # Redirect with 303 status code to enforce a GET request
        return RedirectResponse(CHAINLIT_PATH, status_code=303)
    return RedirectResponse("/")


@app.post("/start-instructor")
async def start_instructor(request: Request):
    username = get_username(request)
    if username == "tgardos@example.com":
        await start_chainlit_instructor_app(username)
        return RedirectResponse(CHAINLIT_INSTRUCTOR_PATH, status_code=303)
    return RedirectResponse("/")


mount_chainlit(app=app, target="chainlit_app.py", path=CHAINLIT_PATH)
mount_chainlit(
    app=app, target="chainlit_instructor_app.py", path=CHAINLIT_INSTRUCTOR_PATH
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
