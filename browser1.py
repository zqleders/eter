import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from patchright.sync_api import BrowserContext, Playwright
from nopecha import verify_api_key

load_dotenv()

BASE_DIR = Path(__file__).parent.absolute()
NOPECHA_EXTENSION_PATH = BASE_DIR / "extensions" / "nopecha"
CHROME_PROFILE_DIR = BASE_DIR / ".chrome_profile"

class BrowserManager:
    def __init__(self, playwright: Playwright):
        self.playwright = playwright
        self.context: Optional[BrowserContext] = None

    def __enter__(self) -> BrowserContext:
        nopecha_enabled = os.getenv("NOPECHA_ENABLED", "true").lower() == "true"
        api_key = os.getenv("NOPECHA_API_KEY")

        if nopecha_enabled:
            if not api_key:
                raise EnvironmentError("NOPECHA_API_KEY is not set.")
            verify_api_key(api_key)

        CHROME_PROFILE_DIR.mkdir(exist_ok=True)

        launch_args = [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
        ]
        if nopecha_enabled:
            launch_args += [
                f"--disable-extensions-except={NOPECHA_EXTENSION_PATH}",
                f"--load-extension={NOPECHA_EXTENSION_PATH}",
            ]

        proxy_url = os.getenv("PROXY_SOCKS5")
        proxy_config = {"server": proxy_url} if proxy_url else None

        self.context = self.playwright.chromium.launch_persistent_context(
            str(CHROME_PROFILE_DIR),
            channel="chromium",
            headless=False,
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            args=launch_args,
            env={**os.environ},
            proxy=proxy_config,
        )

        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = {runtime: {}};
        """)

        if nopecha_enabled:
            self._inject_api_key(api_key)

        return self.context

    def __exit__(self, *_):
        if self.context:
            try: self.context.close()
            except: pass

    def _inject_api_key(self, api_key: str) -> None:
        page = self.context.new_page()
        try:
            page.goto(f"https://nopecha.com/setup#{api_key}", wait_until="load", timeout=10_000)
            page.wait_for_timeout(2000)
        finally:
            page.close()
