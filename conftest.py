"""
Root conftest.py — provides a `driver` fixture so generated Selenium
scripts (which take `driver` as a plain function parameter, matching this
fixture's name) can be run as ordinary pytest tests to get structured
results via pytest-json-report, the same way pytest-playwright's `page`
fixture already lets generated Playwright scripts do the same. Selenium
itself ships no such fixture — every real Selenium+pytest project defines
its own, this is that, not a special-case hack for this repo.
"""
from __future__ import annotations

import os

import pytest
from selenium import webdriver


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    if os.environ.get("HEADED") != "1":
        options.add_argument("--headless=new")
    d = webdriver.Chrome(options=options)
    yield d
    d.quit()
