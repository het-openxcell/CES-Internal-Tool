const cesTokens = {
  "--ces-red": "#C41230",
  "--edit-indicator": "#D97706",
  "--surface": "#F9FAFB"
};

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "ces-red": cesTokens["--ces-red"],
        "edit-indicator": cesTokens["--edit-indicator"],
        surface: cesTokens["--surface"]
      }
    }
  },
  cesTokens
};
