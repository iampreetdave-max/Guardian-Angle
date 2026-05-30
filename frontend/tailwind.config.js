/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Deep navy — the emblem's shield
        ink: {
          900: "#0a1124",
          800: "#0f1a33",
          700: "#172544",
          600: "#223354",
          500: "#324468",
        },
        // Gold — the phoenix. Primary brand accent.
        accent: {
          DEFAULT: "#f4b23c", // bright gold: text/icons on dark
          600: "#c9821a", // button surface (white bold text ≥3:1)
          700: "#a4630c", // hover
        },
        // Indian tricolor — national identity accents
        flag: { saffron: "#ff9933", white: "#ffffff", green: "#138808" },
        signal: { green: "#22c55e", amber: "#f59e0b", red: "#ef4444" },
      },
      fontFamily: {
        serif: ['"EB Garamond"', "Georgia", "serif"],
        sans: ['"Lato"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
