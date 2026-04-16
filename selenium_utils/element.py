from __future__ import annotations

from typing import TYPE_CHECKING

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from .utils import remove_tags, wait_for

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement
    from .driver import SeleniumDriver


class SeleniumElement:
    def __init__(self, webelement: WebElement, driver: SeleniumDriver):
        self.webelement = webelement
        self.driver = driver

    def child_by_css(self, css_selector: str, timeout: int = 10) -> SeleniumElement:
        found = self.find_child_by_css(css_selector, timeout=timeout)
        if not found:
            raise NoSuchElementException(f"Cannot find child with selector {css_selector}")
        return found

    def child_by_xpath(self, xpath: str, timeout: int = 10) -> SeleniumElement:
        found = self.find_child_by_xpath(xpath, timeout=timeout)
        if not found:
            raise NoSuchElementException(f"Cannot find child with selector {xpath}")
        return found

    def find_child_by_css(self, css_selector: str, timeout: int = 10) -> SeleniumElement | None:
        found = self.all_children_by_css(css_selector, timeout=timeout)
        assert len(found) <= 1, f"Found {len(found)} children searching for {css_selector}"
        return found[0] if found else None

    def find_child_by_xpath(self, xpath: str, timeout: int = 10) -> SeleniumElement | None:
        found = self.all_children_by_xpath(xpath, timeout=timeout)
        assert len(found) <= 1, f"Found {len(found)} children searching for {xpath}"
        return found[0] if found else None

    def all_children_by_css(self, css_selector: str, timeout: int = 10) -> list[SeleniumElement]:
        return wait_for(parent=self, selector=css_selector, timeout=timeout)

    def all_children_by_xpath(self, xpath: str, timeout: int = 10) -> list[SeleniumElement]:
        return wait_for(parent=self, selector=xpath, by=By.XPATH, timeout=timeout)

    def child_by_id(self, id: str, timeout: int = 10) -> SeleniumElement:
        css_selector = f'[id="{id}"]'
        return self.child_by_css(css_selector, timeout=timeout)

    def find_child_by_id(self, id: str, timeout: int = 10) -> SeleniumElement | None:
        css_selector = f'[id="{id}"]'
        return self.find_child_by_css(css_selector, timeout=timeout)

    def all_children_by_id(self, id: str, timeout: int = 10) -> list[SeleniumElement]:
        css_selector = f'[id="{id}"]'
        return self.all_children_by_css(css_selector, timeout=timeout)

    def child_by_name(self, name: str, timeout: int = 10) -> SeleniumElement:
        css_selector = f'[name="{name}"]'
        return self.child_by_css(css_selector, timeout=timeout)

    def find_child_by_name(self, name: str, timeout: int = 10) -> SeleniumElement | None:
        css_selector = f'[name="{name}"]'
        return self.find_child_by_css(css_selector, timeout=timeout)

    def all_children_by_name(self, name: str, timeout: int = 10) -> list[SeleniumElement]:
        css_selector = f'[name="{name}"]'
        return self.all_children_by_css(css_selector, timeout=timeout)

    def child_by_tag(self, tag_name: str, timeout: int = 10) -> SeleniumElement:
        css_selector = tag_name
        return self.child_by_css(css_selector, timeout=timeout)

    def find_child_by_tag(self, tag_name: str, timeout: int = 10) -> SeleniumElement | None:
        css_selector = tag_name
        return self.find_child_by_css(css_selector, timeout=timeout)

    def all_children_by_tag(self, tag_name: str, timeout: int = 10) -> list[SeleniumElement]:
        css_selector = tag_name
        return self.all_children_by_css(css_selector, timeout=timeout)

    def text(self) -> str:
        text = self.webelement.get_attribute("innerHTML") or ""
        return remove_tags(text).strip()

    def attr(self, attribute_name: str) -> str | None:
        return self.webelement.get_attribute(attribute_name)

    def click(self):
        self.webelement.click()

    def send_keys(self, keys: str):
        self.webelement.send_keys(keys)

    def __str__(self) -> str:
        id = self.attr("id")
        tag = self.webelement.tag_name
        return f"{tag}#{id if id else '-'}"

    def __repr__(self) -> str:
        return str(self)
