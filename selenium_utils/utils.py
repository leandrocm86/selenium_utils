from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, TypeVar

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as WDWait

if TYPE_CHECKING:
    from .driver import SeleniumDriver
    from .element import SeleniumElement

# Drivers alternativos em https://sites.google.com/chromium.org/driver/
# Instalados com snap install chromium no ubuntu (chromium é só via snap agora)
DEFAULT_DRIVER_PATH = "/usr/bin/chromedriver"
SNAP_DRIVER_PATH = "/snap/bin/chromium.chromedriver"
DEFAULT_BIN_PATH = "/usr/bin/chromium"
SNAP_BIN_PATH = "/snap/bin/chromium"

T = TypeVar("T")


def remove_tags(text: str):
    while True:
        index_tag_start = text.find("<")
        index_tag_end = text.find(">", index_tag_start)
        if index_tag_start == -1 or index_tag_end == -1:
            break
        text = text[:index_tag_start] + text[index_tag_end + 1 :]
    return text


def wait_for(
    parent: SeleniumElement | SeleniumDriver, selector: str, by: str = By.CSS_SELECTOR, timeout: int = 10
) -> list[SeleniumElement]:
    from .element import SeleniumElement
    
    driver = parent.driver if hasattr(parent, "driver") and not hasattr(parent, "xvfb") else parent # SeleniumElement has .driver, SeleniumDriver is parent.driver
    # Wait, SeleniumElement has self.driver which is SeleniumDriver.
    # SeleniumDriver has self.driver which is uc.Chrome.
    
    # In original code:
    # driver = parent.driver if isinstance(parent, SeleniumElement) else parent
    # but I can't use isinstance without importing.
    
    if hasattr(parent, "webelement"): # It's a SeleniumElement
        actual_driver = parent.driver
    else: # It's a SeleniumDriver
        actual_driver = parent

    try:
        def search():
            if hasattr(parent, "webelement"):
                found_elems = parent.webelement.find_elements(by, selector)
            else:
                found_elems = parent.driver.find_elements(by, selector)
            actual_driver.logfunc(f"Found {len(found_elems)} searching for {selector}")
            return [SeleniumElement(e, actual_driver) for e in found_elems]

        return WDWait(actual_driver.driver, poll_frequency=1, timeout=timeout).until(lambda _: search())
    except TimeoutException:
        actual_driver.logfunc("Timeout reached while searching for " + selector)
        return []
