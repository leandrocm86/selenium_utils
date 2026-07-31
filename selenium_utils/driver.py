from __future__ import annotations

import base64
import subprocess
import re
import time
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Callable, TYPE_CHECKING

import undetected_chromedriver as uc
from xvfbwrapper import Xvfb

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.print_page_options import PrintOptions

from .utils import wait_for, DEFAULT_BIN_PATH

if TYPE_CHECKING:
    from .element import SeleniumElement


class SeleniumDriver:
    def __init__(
        self,
        logfunc: Callable[[str], None] = print,
        options: uc.ChromeOptions | None = None,
        download_path: str | None = None
    ):

        self.xvfb = Xvfb(width=1920, height=1080, colordepth=24)
        self.xvfb.start()

        if not options:
            options = self.build_default_options()

        chrome_version = self._get_chrome_major_version(options.binary_location)
        logfunc(f'{chrome_version=}')

        self.raw_driver = uc.Chrome(options=options, version_main=chrome_version, user_data_dir="/tmp/custom_profile")

        self.logfunc = logfunc
        self.logfunc("Starting Selenium driver")

        if download_path:
            self.raw_driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {
                    "behavior": "allow",
                    "downloadPath": download_path
                }
            )

        self.logfunc("Selenium driver loaded")


    def _get_chrome_major_version(self, binary_location: str) -> int:
        out = subprocess.run([binary_location, "--version"], capture_output=True, text=True, check=True)
        assert (version_search := re.search(r"(\d+)\.\d+\.\d+", out.stdout))
        return int(version_search.group(1))


    @staticmethod
    def build_default_options() -> uc.ChromeOptions:
        options = uc.ChromeOptions()
        options.binary_location = DEFAULT_BIN_PATH
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-crash-reporter")
        options.add_argument("--kiosk-printing")
        options.add_argument("--disable-features=OptimizationGuideModelDownloading,OptimizationHints,AutofillServerCommunication,Translate,OptimizationGuide,BackForwardCache,BackForwardCacheMemoryControls")

        #options.add_argument("--disable-gpu") -> desnecessario atualmente
        #options.add_argument("--disable-software-rasterizer")
        options.add_argument("--use-gl=swiftshader")
        options.add_argument("--enable-unsafe-swiftshader")  # necessário em Chrome recentes p/ permitir swiftshader fora de contextos "seguros"
        options.add_argument("--use-angle=swiftshader")

        # === LOGGING PARA VER MOTIVOS DE CRASHES ===
        options.add_argument("--enable-logging")
        options.add_argument("--v=1")  # verbosidade

        return options


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.raw_driver:
            self.quit()
        self.xvfb.stop()

    def quit(self):
        self.logfunc("Closing browser driver")
        self.raw_driver.quit()

    def get(self, url: str, timeout=300):
        self.raw_driver.set_page_load_timeout(timeout)
        self.logfunc("Retrieving " + url)
        self.raw_driver.get(url)

    def by_css(self, css_selector: str, timeout: int = 10) -> SeleniumElement:
        found = self.find_by_css(css_selector, timeout=timeout)
        if not found:
            raise NoSuchElementException(f"Cannot find element with selector {css_selector}")
        return found

    def by_xpath(self, xpath: str, timeout: int = 10) -> SeleniumElement:
        found = self.find_by_xpath(xpath, timeout=timeout)
        if not found:
            raise NoSuchElementException(f"Cannot find element with selector {xpath}")
        return found

    def find_by_css(self, css_selector: str, timeout: int = 10) -> SeleniumElement | None:
        found = self.all_by_css(css_selector, timeout=timeout)
        assert len(found) <= 1, f"Found {len(found)} elements searching for {css_selector}"
        return found[0] if found else None

    def find_by_xpath(self, xpath: str, timeout: int = 10) -> SeleniumElement | None:
        found = self.all_by_xpath(xpath, timeout=timeout)
        assert len(found) <= 1, f"Found {len(found)} elements searching for {xpath}"
        return found[0] if found else None

    def all_by_css(self, css_selector: str, timeout: int = 10) -> list[SeleniumElement]:
        return wait_for(parent=self, selector=css_selector, timeout=timeout)

    def all_by_xpath(self, xpath: str, timeout: int = 10) -> list[SeleniumElement]:
        return wait_for(parent=self, selector=xpath, by=By.XPATH, timeout=timeout)

    def by_id(self, id: str, timeout: int = 10) -> SeleniumElement:
        css_selector = f'[id="{id}"]'
        return self.by_css(css_selector, timeout=timeout)

    def find_by_id(self, id: str, timeout: int = 10) -> SeleniumElement | None:
        css_selector = f'[id="{id}"]'
        return self.find_by_css(css_selector, timeout=timeout)

    def all_by_id(self, id: str, timeout: int = 10) -> list[SeleniumElement]:
        css_selector = f'[id="{id}"]'
        return self.all_by_css(css_selector, timeout=timeout)

    def by_name(self, name: str, timeout: int = 10) -> SeleniumElement:
        css_selector = f'[name="{name}"]'
        return self.by_css(css_selector, timeout=timeout)

    def find_by_name(self, name: str, timeout: int = 10) -> SeleniumElement | None:
        css_selector = f'[name="{name}"]'
        return self.find_by_css(css_selector, timeout=timeout)

    def all_by_name(self, name: str, timeout: int = 10) -> list[SeleniumElement]:
        css_selector = f'[name="{name}"]'
        return self.all_by_css(css_selector, timeout=timeout)

    def by_tag(self, tag_name: str, timeout: int = 10) -> SeleniumElement:
        css_selector = tag_name
        return self.by_css(css_selector, timeout=timeout)

    def find_by_tag(self, tag_name: str, timeout: int = 10) -> SeleniumElement | None:
        css_selector = tag_name
        return self.find_by_css(css_selector, timeout=timeout)

    def all_by_tag(self, tag_name: str, timeout: int = 10) -> list[SeleniumElement]:
        css_selector = tag_name
        return self.all_by_css(css_selector, timeout=timeout)

    def print_page(self, path: Path | str, width: float, height: float):
        """Saves a page as PDF in the given path.
        A3 = 29.7 x 42; A4 = 21 x 29.7
        """
        print_options = PrintOptions()
        print_options.page_width = width
        print_options.page_height = height
        pdf_data = self.raw_driver.print_page(print_options=print_options)
        with open(path, "wb") as f:
            f.write(base64.b64decode(pdf_data))

    def screenshot(self, path: str | Path, full_page: bool = True) -> None:
        """Salva um screenshot da página renderizada.
        Args:
            path: Caminho para salvar o arquivo PNG.
            full_page: Se True, captura a página inteira (além do viewport).
        """
        self.logfunc(f"Taking screenshot: {path}")
        path = str(path)

        result = self.raw_driver.execute_cdp_cmd("Page.captureScreenshot", {
            "format": "png",
            "captureBeyondViewport": full_page,
        })
        with open(str(path), "wb") as f:
            f.write(base64.b64decode(result["data"]))

    def extract_page_source(self, live: bool = True, pretty: bool = True) -> str:
        try:
            source = self.raw_driver.execute_script("return document.documentElement.outerHTML") if live else self.raw_driver.page_source
            if pretty:
                source = BeautifulSoup(source, "html.parser").prettify()
            return source
        except Exception as e:
            self.logfunc(f"Failed to extract page source: {e}")
            return ""

    def save_mhtml(self, path: str | Path) -> None:
        """Salva a página completa como MHTML (HTML + todos os recursos em um arquivo)."""
        self.logfunc(f"Saving MHTML snapshot: {path}")
        result = self.raw_driver.execute_cdp_cmd("Page.captureSnapshot", {"format": "mhtml"})
        with open(path, "w", encoding="utf-8") as f:
            f.write(result["data"])

    def sleep(self, seconds: int) -> None:
        self.logfunc(f"Sleeping for {seconds} seconds")
        time.sleep(seconds)
