package com.utf.locator;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

import java.util.Map;

/**
 * Java port of the same Strategy-pattern contract used by every other
 * language's resolver in this framework (see locator_resolution/base.py
 * and its docstring for the original playwright-modular-locator-framework
 * pattern this generalizes) — every strategy implements find(), the
 * engine only ever calls that, so strategies are swappable without
 * touching engine code.
 */
public interface LocatorStrategy {
    WebElement find(WebDriver driver, Map<String, Object> target);
    String name();
}
