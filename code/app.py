from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
from chainlit.utils import mount_chainlit
from chainlit_app import start_chainlit_app
from chainlit_instructor_app import start_chainlit_instructor_app
import secrets
import json
import os
import base64
from fastapi import FastAPI
from chainlit.config import config, load_module
from chainlit.server import combined_asgi_app as chainlit_app
from chainlit.utils import check_file, ensure_jwt_secret

from modules.config.constants import OAUTH_GOOGLE_CLIENT_ID, OAUTH_GOOGLE_CLIENT_SECRET
from fastapi.middleware.cors import CORSMiddleware


GOOGLE_CLIENT_ID = OAUTH_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = OAUTH_GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/oauth/google/callback"


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with appropriate origins
    allow_methods=["*"],
    allow_headers=["*"],  # or specify the headers you want to allow
    expose_headers=["X-User-Info"],  # Expose the custom header
)

templates = Jinja2Templates(directory="templates")
session_store = {}
CHAINLIT_PATH = "/chainlit_tutor"
CHAINLIT_INSTRUCTOR_PATH = "/chainlit_instructor"


USER_ROLES = {
    "tgardos@bu.edu": ["instructor", "bu"],
    "xthomas@bu.edu": ["instructor", "bu"],
    "faridkar@bu.edu": ["instructor", "bu"],
    "xavierohan1@gmail.com": ["guest"],
    # Add more users and roles as needed
}

# Create a Google OAuth flow
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
            "scopes": [
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ],
        }
    },
    scopes=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ],
    redirect_uri=GOOGLE_REDIRECT_URI,
)


def get_user_role(username: str):
    return USER_ROLES.get(username, ["student"])  # Default to "student" role


def get_user_info(request: Request):
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
    authorization_url, _ = flow.authorization_url(prompt="consent")
    return RedirectResponse(authorization_url)


@app.get("/auth/oauth/google/callback")
async def auth_google(request: Request):

    flow.fetch_token(code=request.query_params.get("code"))
    credentials = flow.credentials
    user_info = id_token.verify_oauth2_token(
        credentials.id_token, requests.Request(), GOOGLE_CLIENT_ID
    )

    email = user_info["email"]
    name = user_info.get("name", "")
    profile_image = user_info.get("picture", "")

    session_token = secrets.token_hex(16)
    session_store[session_token] = {
        "email": email,
        "name": name,
        "profile_image": profile_image,
    }
    response = RedirectResponse(url="/post-signin", status_code=303)
    response.set_cookie(key="session_token", value=session_token)
    return response


@app.get("/post-signin", response_class=HTMLResponse)
async def post_signin(request: Request, user_info: dict = Depends(get_user_info)):
    if user_info:
        username = user_info["email"]
        role = get_user_role(username)
        return templates.TemplateResponse(
            "dashboard.html", {"request": request, "username": username, "role": role}
        )
    return RedirectResponse("/")


@app.post("/start-tutor")
async def start_tutor(request: Request):
    user_info = get_user_info(request)
    if user_info:
        user_info_json = json.dumps(user_info)
        user_info_encoded = base64.b64encode(user_info_json.encode()).decode()

        print("\n\nHERE!!!")
        print("User Info JSON:", user_info_json)
        print()

        response = RedirectResponse(CHAINLIT_PATH, status_code=303)
        # response.headers["X-User-Info"] = user_info_encoded # Headers were not being sent to the chainlit app # TODO: Fix this
        response.set_cookie(key="X-User-Info", value=user_info_encoded, httponly=True)
        print("X-User-Info cookie set")
        print("\n\n\nSession Token:", request.cookies.get("session_token"))
        print()
        return response

    return RedirectResponse(url="/")


@app.post("/start-instructor")
async def start_instructor(request: Request):
    username = get_username(request)
    if username == "tgardos@example.com":
        await start_chainlit_instructor_app(username)
        return RedirectResponse(CHAINLIT_INSTRUCTOR_PATH, status_code=303)
    return RedirectResponse("/")


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "error.html", {"request": request, "error": str(exc)}, status_code=500
    )


mount_chainlit(app=app, target="chainlit_app.py", path=CHAINLIT_PATH)
mount_chainlit(
    app=app, target="chainlit_instructor_app.py", path=CHAINLIT_INSTRUCTOR_PATH
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
