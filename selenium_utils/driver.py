from __future__ import annotations

import base64
import subprocess
import re
import time
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
        driver_path: str | None = None,
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

        if driver_path:
            self.driver = uc.Chrome(options=options, version_main=chrome_version, driver_executable_path=driver_path)
        else:
            self.driver = uc.Chrome(options=options, version_main=chrome_version)

        self.logfunc = logfunc
        self.logfunc("Starting Selenium driver")

        if download_path:
            self.driver.execute_cdp_cmd(
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
        return options


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.quit()
        self.xvfb.stop()

    def quit(self):
        self.logfunc("Closing browser driver")
        self.driver.quit()

    def get(self, url: str, timeout=300):
        self.driver.set_page_load_timeout(timeout)
        self.logfunc("Retrieving " + url)
        self.driver.get(url)

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
        pdf_data = self.driver.print_page(print_options=print_options)
        with open(path, "wb") as f:
            f.write(base64.b64decode(pdf_data))

    def print_page_source(self, path: str | None = None) -> str:
        if path:
            with open(path, "w") as f:
                f.write(self.driver.page_source)
        return self.driver.page_source

    def sleep(self, seconds: int) -> None:
        self.logfunc(f"Sleeping for {seconds} seconds")
        time.sleep(seconds)
