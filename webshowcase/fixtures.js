/**
 * Fixtures embedded directly (not fetched) so this page works standalone
 * when embedded/iframed elsewhere, with no relative-path/CORS assumptions.
 * Mirrors tests/fixtures/*.json and examples/scip_login.json exactly.
 */
export const FIXTURES = [
  {
    name: "scip-real-world",
    label: "★ Real-world: SCIP login (not a toy demo)",
    real: true,
    def: {
      test_name: "SCIP: user can log in and reach the dashboard",
      description:
        "Real-world demonstration against the actual Supply Chain Intelligence Platform app (a separate project, not this framework's own bundled demo site) -- proves the generated code and locator resolution work against a real, independently-built app they were never designed around.",
      steps: [
        { action: "navigate", target: { type: "url", value: "/login" } },
        { action: "fill", target: { type: "field_description", value: "Username" }, value: "demo" },
        { action: "fill", target: { type: "field_description", value: "Password" }, value: "Demo@2026" },
        { action: "click", target: { type: "button_text", value: "Sign In" } },
        { action: "assert_url", value: "/dashboard" },
        { action: "assert_visible", target: { type: "page_text", value: "Welcome back" } },
      ],
    },
  },
  {
    name: "login",
    label: "Login",
    def: {
      test_name: "User can log in with valid credentials",
      description: "Verifies a registered user can sign in and reach the dashboard.",
      steps: [
        { action: "navigate", target: { type: "url", value: "/login" } },
        { action: "fill", target: { type: "field_description", value: "email input field" }, value: "test@example.com" },
        { action: "fill", target: { type: "field_description", value: "password input field" }, value: "SecurePass123" },
        { action: "click", target: { type: "button_text", value: "Sign In" } },
        { action: "assert_visible", target: { type: "field_description", value: "dashboard welcome message" } },
      ],
    },
  },
  {
    name: "form_submission",
    label: "Form submission",
    def: {
      test_name: "User can submit the contact form with a subject and consent",
      description: "Verifies the contact form accepts a message, a selected subject, and a required consent checkbox, then shows a confirmation.",
      steps: [
        { action: "navigate", target: { type: "url", value: "/contact" } },
        { action: "fill", target: { type: "field_description", value: "full name input field" }, value: "Jordan Lee" },
        { action: "fill", target: { type: "field_description", value: "message textarea" }, value: "I'd like a demo of the enterprise plan." },
        { action: "select", target: { type: "dropdown_description", value: "subject dropdown" }, value: "Sales" },
        { action: "check", target: { type: "checkbox_description", value: "I agree to be contacted" } },
        { action: "click", target: { type: "element_role", role: "button", name: "Send Message" } },
        {
          action: "assert_text",
          target: { type: "page_text", value: "confirmation banner", hint: { test_id: "confirmation-banner" } },
          value: "Thanks - we'll be in touch shortly.",
        },
      ],
    },
  },
  {
    name: "navigation",
    label: "Navigation",
    def: {
      test_name: "User can reach the pricing page from the homepage nav",
      description: "Verifies the top nav's Pricing link lands on the correct URL and renders the pricing heading.",
      steps: [
        { action: "navigate", target: { type: "url", value: "/" } },
        { action: "click", target: { type: "link_text", value: "Pricing" } },
        { action: "assert_url", value: "/pricing" },
        { action: "assert_visible", target: { type: "element_role", role: "heading", name: "Simple, transparent pricing" } },
      ],
    },
  },
];
