package com.utf.locator;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

import java.util.List;
import java.util.Map;

/**
 * Java port of locator_resolution/strategies/accessibility_tree.py — same
 * strategies (ARIA label, label-association, placeholder, text content,
 * role+accessible-name), same reasoning for why Selenium needs them at
 * all (no built-in get_by_label/get_by_role the way Playwright has).
 * Each class here is deliberately narrow, exactly like the Python
 * version and the original playwright-modular-locator-framework it both
 * descend from.
 */
final class AccessibilityTreeStrategies {
    private AccessibilityTreeStrategies() {}

    private static String ciContains(String attrOrText, String value) {
        String upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        String lower = "abcdefghijklmnopqrstuvwxyz";
        return String.format("contains(translate(%s, '%s', '%s'), '%s')", attrOrText, upper, lower, value.toLowerCase());
    }

    private static WebElement firstOrNull(WebDriver driver, String xpath) {
        List<WebElement> elements = driver.findElements(By.xpath(xpath));
        for (WebElement el : elements) {
            if (el.isDisplayed()) return el;
        }
        return null;
    }

    static class AriaLabelStrategy implements LocatorStrategy {
        public String name() { return "aria_label"; }
        public WebElement find(WebDriver driver, Map<String, Object> target) {
            String value = (String) target.get("value");
            if (value == null) return null;
            String xpath = String.format("//*[@aria-label and %s]", ciContains("@aria-label", value));
            return firstOrNull(driver, xpath);
        }
    }

    static class LabelAssociationStrategy implements LocatorStrategy {
        public String name() { return "label_association"; }
        public WebElement find(WebDriver driver, Map<String, Object> target) {
            String value = (String) target.get("value");
            if (value == null) return null;
            String labelXpath = String.format("//label[%s]", ciContains(".", value));
            for (WebElement label : driver.findElements(By.xpath(labelXpath))) {
                String forId = label.getAttribute("for");
                if (forId != null && !forId.isEmpty()) {
                    List<WebElement> byId = driver.findElements(By.id(forId));
                    if (!byId.isEmpty() && byId.get(0).isDisplayed()) return byId.get(0);
                }
                List<WebElement> nested = label.findElements(By.xpath(".//input | .//select | .//textarea"));
                if (!nested.isEmpty() && nested.get(0).isDisplayed()) return nested.get(0);
            }
            return null;
        }
    }

    static class PlaceholderStrategy implements LocatorStrategy {
        public String name() { return "placeholder"; }
        public WebElement find(WebDriver driver, Map<String, Object> target) {
            String value = (String) target.get("value");
            if (value == null) return null;
            String xpath = String.format("//*[@placeholder and %s]", ciContains("@placeholder", value));
            return firstOrNull(driver, xpath);
        }
    }

    static class TextContentStrategy implements LocatorStrategy {
        public String name() { return "text_content"; }
        public WebElement find(WebDriver driver, Map<String, Object> target) {
            String value = (String) target.get("value");
            if (value == null) return null;
            String xpath = String.format("//*[%s]", ciContains("normalize-space(text())", value));
            return firstOrNull(driver, xpath);
        }
    }

    static class RoleAttributeStrategy implements LocatorStrategy {
        // Plain tag/predicate segments, no leading "//" -- the loop below
        // prepends exactly one "//" per segment, consistently.
        private static final Map<String, String> IMPLICIT_ROLE_TAGS = Map.of(
            "button", "button | input[@type='button'] | input[@type='submit']",
            "link", "a",
            "heading", "h1 | h2 | h3 | h4 | h5 | h6",
            "checkbox", "input[@type='checkbox']",
            "textbox", "input[@type='text'] | input[@type='email'] | textarea"
        );

        public String name() { return "role_attribute"; }
        public WebElement find(WebDriver driver, Map<String, Object> target) {
            String role = (String) target.get("role");
            String accessibleName = (String) target.get("name");
            if (role == null || accessibleName == null) return null;

            String tags = IMPLICIT_ROLE_TAGS.getOrDefault(role, "*[@role='" + role + "']");
            String namePredicate = String.format("[%s or %s]",
                ciContains("@aria-label", accessibleName), ciContains("normalize-space(.)", accessibleName));

            StringBuilder xpath = new StringBuilder();
            for (String part : tags.split("\\|")) {
                if (xpath.length() > 0) xpath.append(" | ");
                xpath.append("//").append(part.trim()).append(namePredicate);
            }
            return firstOrNull(driver, xpath.toString());
        }
    }
}
