package com.utf.locator;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

import java.util.List;
import java.util.Map;

/**
 * Java port of locator_resolution/selenium_resolver.py — assembles the
 * right strategy chain per target type, hints tried first. Visual
 * (OpenCV) fallback is intentionally not ported here: it would need a
 * Java OpenCV binding (JavaCV/OpenPnP) as a brand-new dependency, whereas
 * the Python and Cypress resolvers were able to reuse one already-proven
 * OpenCV implementation (see locator_resolution/strategies/
 * visual_fallback.py and visual_match_task.js) -- a real, honest scope
 * boundary for this first Java runner, not an oversight. See
 * docs/adding_a_new_language.md.
 */
public final class SeleniumResolver {
    private SeleniumResolver() {}

    public static class LocatorResolutionException extends RuntimeException {
        public LocatorResolutionException(String message) { super(message); }
    }

    @SuppressWarnings("unchecked")
    public static WebElement resolve(WebDriver driver, Map<String, Object> target) {
        Map<String, Object> hint = (Map<String, Object>) target.getOrDefault("hint", Map.of());

        if (hint.containsKey("test_id")) {
            List<WebElement> els = driver.findElements(By.cssSelector("[data-testid=\"" + hint.get("test_id") + "\"]"));
            if (!els.isEmpty()) return els.get(0);
        }
        if (hint.containsKey("css")) {
            List<WebElement> els = driver.findElements(By.cssSelector((String) hint.get("css")));
            if (!els.isEmpty()) return els.get(0);
        }

        String type = (String) target.get("type");
        List<LocatorStrategy> chain = strategiesFor(type);
        for (LocatorStrategy strategy : chain) {
            WebElement el = strategy.find(driver, target);
            if (el != null) return el;
        }

        throw new LocatorResolutionException(
            "No locator strategy matched target " + target + ". See docs/locator_hints.md for how to add a hint."
        );
    }

    private static List<LocatorStrategy> strategiesFor(String type) {
        var ariaLabel = new AccessibilityTreeStrategies.AriaLabelStrategy();
        var labelAssoc = new AccessibilityTreeStrategies.LabelAssociationStrategy();
        var placeholder = new AccessibilityTreeStrategies.PlaceholderStrategy();
        var textContent = new AccessibilityTreeStrategies.TextContentStrategy();
        var role = new AccessibilityTreeStrategies.RoleAttributeStrategy();

        // Same per-type chains as the Python (accessibility_tree.py) and
        // JS (cypress/support/commands.js) resolvers, for consistency
        // across all languages this framework targets.
        return switch (type) {
            case "field_description" -> List.of(ariaLabel, labelAssoc, placeholder, textContent);
            case "checkbox_description", "dropdown_description" -> List.of(ariaLabel, labelAssoc);
            case "button_text", "link_text" -> List.of(textContent, ariaLabel);
            case "element_role" -> List.of(role);
            case "page_text" -> List.of(textContent);
            default -> throw new LocatorResolutionException("Unknown target type: " + type);
        };
    }
}
