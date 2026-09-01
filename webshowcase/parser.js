/**
 * Rule-based (NOT AI) plain-English -> intermediate-format parser, for the
 * static GitHub Pages showcase where a real LLM call isn't possible (no
 * way to hold an API key securely on a static page -- see
 * docs/getting_started.md's LLM-generation section for the real thing,
 * which needs ANTHROPIC_API_KEY on a real backend).
 *
 * Deliberately the exact INVERSE of generation/manual_case_generator.py's
 * phrasing (ported in adapters.js as describeStep/generateManualCase) --
 * type "Load" on any example in Plain English mode, and you get back
 * exactly the text this parser is designed to consume, so the two
 * directions round-trip. Anything this parser can't confidently match is
 * reported as a skipped line, never silently guessed at.
 */

const QUOTED = '"([^"]*)"';

// Order matters: more specific patterns (element_role, checkbox/dropdown/
// button/link wording) must be tried before the generic bare-word fallback.
const TARGET_PATTERNS = [
  { re: new RegExp(`^the (\\w+) named ${QUOTED}$`, "i"), toTarget: (m) => ({ type: "element_role", role: m[1], name: m[2] }) },
  { re: new RegExp(`^the ${QUOTED} checkbox$`, "i"), toTarget: (m) => ({ type: "checkbox_description", value: m[1] }) },
  { re: new RegExp(`^the ${QUOTED} dropdown$`, "i"), toTarget: (m) => ({ type: "dropdown_description", value: m[1] }) },
  { re: new RegExp(`^the ${QUOTED} button$`, "i"), toTarget: (m) => ({ type: "button_text", value: m[1] }) },
  { re: new RegExp(`^the ${QUOTED} link$`, "i"), toTarget: (m) => ({ type: "link_text", value: m[1] }) },
];

// Bare-word fallback target type per action, when none of the quoted
// TARGET_PATTERNS above match -- the manual-case phrasing for
// field_description and page_text is identical plain text, so this is a
// genuine ambiguity the rule-based parser resolves with a sensible
// default rather than guessing per-word. See webshowcase/README section
// in the main README for this documented limitation.
const BARE_TARGET_TYPE_BY_ACTION = {
  fill: "field_description",
  click: "button_text",
  select: "dropdown_description",
  check: "checkbox_description",
  uncheck: "checkbox_description",
  assert_visible: "page_text",
  assert_text: "page_text",
};

function parseTargetPhrase(phrase, action) {
  const trimmed = phrase.trim().replace(/\.$/, "");
  for (const { re, toTarget } of TARGET_PATTERNS) {
    const m = trimmed.match(re);
    if (m) return toTarget(m);
  }
  return { type: BARE_TARGET_TYPE_BY_ACTION[action] || "page_text", value: trimmed };
}

const LINE_PATTERNS = [
  { action: "navigate", re: /^go to (.+?)\.?$/i, build: (m) => ({ action: "navigate", target: { type: "url", value: m[1].trim() } }) },
  { action: "fill", re: new RegExp(`^enter ${QUOTED} into (.+?)\\.?$`, "i"), build: (m) => ({ action: "fill", target: parseTargetPhrase(m[2], "fill"), value: m[1] }) },
  { action: "click", re: /^click (.+?)\.?$/i, build: (m) => ({ action: "click", target: parseTargetPhrase(m[1], "click") }) },
  { action: "select", re: new RegExp(`^choose ${QUOTED} from (.+?)\\.?$`, "i"), build: (m) => ({ action: "select", target: parseTargetPhrase(m[2], "select"), value: m[1] }) },
  { action: "check", re: /^check (.+?)\.?$/i, build: (m) => ({ action: "check", target: parseTargetPhrase(m[1], "check") }) },
  { action: "uncheck", re: /^uncheck (.+?)\.?$/i, build: (m) => ({ action: "uncheck", target: parseTargetPhrase(m[1], "uncheck") }) },
  { action: "assert_url", re: new RegExp(`^verify the page url contains ${QUOTED}\\.?$`, "i"), build: (m) => ({ action: "assert_url", value: m[1] }) },
  { action: "assert_text", re: new RegExp(`^verify that (.+?) shows ${QUOTED}\\.?$`, "i"), build: (m) => ({ action: "assert_text", target: parseTargetPhrase(m[1], "assert_text"), value: m[2] }) },
  { action: "assert_visible", re: /^verify that (.+?) is visible\.?$/i, build: (m) => ({ action: "assert_visible", target: parseTargetPhrase(m[1], "assert_visible") }) },
];

/**
 * Parses free-text in the shape generateManualCase() produces:
 *   Test Case: <name>
 *   <optional description line>
 *
 *   Steps:
 *   1. <step sentence>
 *   2. <step sentence>
 *   ...
 *
 * Returns { testDef, skipped } -- skipped is a list of { line, reason }
 * for every input line that didn't confidently match a pattern, so
 * nothing is ever silently dropped.
 */
export function parsePlainEnglish(text) {
  const rawLines = text.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
  const skipped = [];

  let testName = "Untitled test";
  let description = "";
  const steps = [];

  let i = 0;
  const nameMatch = rawLines[0] && rawLines[0].match(/^test case:\s*(.+)$/i);
  if (nameMatch) {
    testName = nameMatch[1].trim();
    i = 1;
    if (rawLines[i] && !/^steps:?$/i.test(rawLines[i]) && !/^\d+[.)]/.test(rawLines[i])) {
      description = rawLines[i];
      i += 1;
    }
  }

  for (; i < rawLines.length; i++) {
    const line = rawLines[i];
    if (/^steps:?$/i.test(line)) continue;

    const stepText = line.replace(/^\d+[.)]\s*/, "");
    let matched = false;
    for (const { re, build } of LINE_PATTERNS) {
      const m = stepText.match(re);
      if (m) {
        steps.push(build(m));
        matched = true;
        break;
      }
    }
    if (!matched) skipped.push({ line, reason: "No recognized step pattern (see webshowcase docs for supported phrasings)" });
  }

  if (steps.length === 0) {
    throw new Error("No recognizable steps found. See the format examples via 'Load' in Plain English mode.");
  }

  const testDef = { test_name: testName, steps };
  if (description) testDef.description = description;
  return { testDef, skipped };
}

export const SUPPORTED_PHRASINGS = [
  'Go to <path>.',
  'Enter "<value>" into <description | the "X" button/link/checkbox/dropdown | the ROLE named "X">.',
  'Click <description | the "X" button/link | the ROLE named "X">.',
  'Choose "<value>" from <description | the "X" dropdown>.',
  'Check / Uncheck <description | the "X" checkbox>.',
  'Verify that <description> is visible.',
  'Verify that <description> shows "<value>".',
  'Verify the page URL contains "<value>".',
];
