from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from chainlit.utils import mount_chainlit
from main import start_chainlit_app
import secrets

app = FastAPI()
templates = Jinja2Templates(directory="templates")
session_store = {}
CHAINLIT_PATH = "/chainlit"


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
    # Set username to "guest"
    username = "guest"
    session_token = secrets.token_hex(16)
    session_store[session_token] = username
    response = RedirectResponse(url="/guest-signin", status_code=303)
    response.set_cookie(key="session_token", value=session_token)
    return response


@app.get("/login/google")
async def login_google():
    # Redirect to Google OAuth endpoint (replace with actual URL)
    # In production, use the correct OAuth flow
    return RedirectResponse(url="/auth/google")


@app.get("/auth/google")
async def auth_google(request: Request):
    # This is a placeholder for the OAuth callback
    # In a real implementation, extract the Google-provided token and fetch user info
    # For this example, assume the username is fetched successfully
    username = (
        "google_user@example.com"  # Replace with actual username fetched from Google
    )
    session_token = secrets.token_hex(16)
    session_store[session_token] = username
    response = RedirectResponse(url="/guest-signin", status_code=303)
    response.set_cookie(key="session_token", value=session_token)
    return response


@app.get("/guest-signin")
async def guest_signin(username: str = Depends(get_username)):
    if username:
        print(f"User signed in: {username}")
        await start_chainlit_app(username)
        return RedirectResponse(CHAINLIT_PATH)
    else:
        return RedirectResponse("/")


mount_chainlit(app=app, target="./main.py", path=CHAINLIT_PATH)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
