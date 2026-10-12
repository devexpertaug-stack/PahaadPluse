import type { Config } from "tailwindcss";

/**
 * PahadPulse design system — a green/white palette with a forest accent and a
 * Mussoorie / Uttarakhand hill-town visual identity (deep forest greens, misty
 * off-whites, pine/ridge motifs). These tokens are the single source of truth
 * shared across every page.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep forest greens — the primary brand colour.
        forest: {
          50: "#f1f7f2",
          100: "#dcebdf",
          200: "#bcd9c1",
          300: "#90be99",
          400: "#5f9d6c",
          500: "#3f8150",
          600: "#2f663e",
          700: "#275233",
          800: "#21422b",
          900: "#1c3725",
          950: "#0d1f14",
        },
        // Misty off-whites — the hill-town morning haze.
        mist: {
          50: "#fbfdfb",
          100: "#f4f8f4",
          200: "#e8f0e9",
          300: "#d7e4d8",
          400: "#bdd0bf",
        },
        // Pine accent for highlights and ridge motifs.
        pine: {
          400: "#6aa17b",
          500: "#4f8a63",
          600: "#3c6e4d",
        },
        // Warm sunrise accent for emphasis (Himalayan dawn).
        dawn: {
          400: "#e9b872",
          500: "#dca24c",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        ridge: "0 10px 30px -12px rgba(28, 55, 37, 0.25)",
        tile: "0 1px 2px 0 rgba(28, 55, 37, 0.08), 0 4px 12px -6px rgba(28, 55, 37, 0.12)",
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.25rem",
      },
      backgroundImage: {
        // Subtle misty ridge gradient used by the app shell.
        "hill-haze":
          "linear-gradient(180deg, #fbfdfb 0%, #f4f8f4 40%, #e8f0e9 100%)",
        "forest-header":
          "linear-gradient(135deg, #1c3725 0%, #275233 55%, #2f663e 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
