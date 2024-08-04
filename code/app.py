from flask import Flask, render_template, redirect, url_for
import subprocess
import time
import requests
import os

app = Flask(__name__)

CHAINLIT_URL = "http://127.0.0.1:8000"
MAX_WAIT_TIME = 10  # Maximum wait time in seconds
INITIAL_RETRY_DELAY = 0.1  # Initial delay between retries in seconds


def is_chainlit_running(url):
    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.ConnectionError:
        return False


@app.route("/", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/guest-signin", methods=["GET"])
def guest_signin():
    # Implement guest sign-in logic here
    # For example, set up a session and redirect to the Chainlit app
    if not is_chainlit_running(CHAINLIT_URL):
        try:
            subprocess.Popen(
                ["chainlit", "run", "main.py", "--port", "8000"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Wait for the Chainlit app to be ready with exponential backoff
            total_wait_time = 0
            retry_delay = INITIAL_RETRY_DELAY
            while total_wait_time < MAX_WAIT_TIME:
                if is_chainlit_running(CHAINLIT_URL):
                    return redirect(CHAINLIT_URL)
                time.sleep(retry_delay)
                total_wait_time += retry_delay
                retry_delay *= 2  # Exponential backoff
        except Exception as e:
            return f"Error starting Chainlit app: {e}"

    return redirect(CHAINLIT_URL)


@app.route("/auth/google")
def google_signin():
    # This would be the route that handles the Google OAuth flow
    # For this example, we'll just simulate the redirect
    # In production, this would involve redirecting to Google's OAuth 2.0 server
    return redirect("https://accounts.google.com/o/oauth2/auth")


if __name__ == "__main__":
    app.run(port=8080)
