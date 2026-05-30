/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0a0f1a",
          800: "#0f1626",
          700: "#161f33",
          600: "#1f2b45",
          500: "#2c3a5a",
        },
        accent: {
          DEFAULT: "#38bdf8",
          600: "#0ea5e9",
          700: "#0284c7",
        },
        signal: { green: "#22c55e", amber: "#f59e0b", red: "#ef4444" },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
