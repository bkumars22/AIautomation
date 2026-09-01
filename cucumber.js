module.exports = {
  default: {
    paths: ["generated/**/*.feature"],
    require: ["cucumber/step_definitions/**/*.js", "cucumber/support/**/*.js"],
    format: ["summary"],
  },
};
