"""Visit the Streamlit Community Cloud app in a real browser so it stays awake.

Streamlit Cloud puts an app to sleep after ~12h without viewers, and only a real
browser session counts as a viewer -- a plain HTTP ping does not. If the app is
already asleep, this clicks the wake button and waits for it to boot.

Exits non-zero if the app never loads or shows an exception, so a broken app
shows up as a failed workflow run instead of a silent green check.
"""
import os
import sys
import time

from playwright.sync_api import Error as PlaywrightError, sync_playwright

URL = os.environ.get("APP_URL", "https://smartreview-ai.streamlit.app/")
WAKE_BUTTON = "Yes, get this app back up!"
BOOT_TIMEOUT_S = 300  # a cold wake took ~30s in testing; leave plenty of room
STAY_S = 20           # keep the session open long enough to register as a visit


def app_frame(page):
    """The iframe the Streamlit app renders in, once it has mounted (else None)."""
    for frame in page.frames:
        try:
            if "/~/+/" in frame.url and frame.locator('[data-testid="stApp"]').count():
                return frame
        except PlaywrightError:  # frame detached mid-check while the page swaps
            continue
    return None


def fail(message):
    print(f"::error::{message}")
    sys.exit(1)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=90_000)

    deadline = time.monotonic() + BOOT_TIMEOUT_S
    clicked_wake = False
    frame = None
    while time.monotonic() < deadline:
        frame = app_frame(page)
        if frame:
            break
        wake = page.get_by_role("button", name=WAKE_BUTTON)
        if not clicked_wake and wake.is_visible():
            print("App was asleep; clicking the wake button.")
            wake.click()
            clicked_wake = True
        page.wait_for_timeout(5_000)

    if not frame:
        fail(f"App did not load within {BOOT_TIMEOUT_S}s: {URL}")

    page.wait_for_timeout(STAY_S * 1000)
    if frame.locator('[data-testid="stException"]').count():
        fail("App loaded but is showing a Python exception.")
    if not frame.locator("body").inner_text().strip():
        fail("App loaded but rendered nothing.")

    print("App is up" + (" (woken from sleep)." if clicked_wake else " (was already awake)."))
    browser.close()
