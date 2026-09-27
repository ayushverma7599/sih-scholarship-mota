import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Government-appropriate palette (GIGW-inspired): deep navy + saffron accent.
        ink: "#0f172a",
        navy: { DEFAULT: "#1e3a5f", 700: "#16304f", 900: "#0b2038" },
        saffron: { DEFAULT: "#ea7317", 600: "#d3620b" },
        leaf: "#137a4b",
        sky: "#0369a1",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "Arial", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(15,23,42,0.08), 0 1px 2px rgba(15,23,42,0.04)",
      },
    },
  },
  plugins: [],
};
export default config;
