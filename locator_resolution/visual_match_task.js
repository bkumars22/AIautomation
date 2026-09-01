/**
 * Cypress "task" (Node-side code, runs outside the browser sandbox —
 * necessary since browser JS can't spawn processes) that shells out to
 * scripts/visual_match_cli.py to reuse the exact same OpenCV template-
 * matching logic the Selenium adapter's VisualFallbackStrategy uses.
 *
 * Node has no OpenCV binding as simple/mature as Python's cv2 — reusing
 * the already-proven Python implementation via a subprocess is a more
 * honest engineering choice than a partial from-scratch reimplementation
 * in JS just to avoid a cross-language call.
 */
const { execFileSync } = require("child_process");
const path = require("path");

function matchTemplate({ screenshotPath, referenceImagePath, confidenceThreshold }) {
  const cliPath = path.join(__dirname, "..", "scripts", "visual_match_cli.py");
  const args = [cliPath, screenshotPath, referenceImagePath];
  if (confidenceThreshold !== undefined) args.push(String(confidenceThreshold));

  const output = execFileSync("python", args, { encoding: "utf-8" });
  return JSON.parse(output.trim());
}

module.exports = { matchTemplate };
