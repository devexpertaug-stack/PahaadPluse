import type { Config } from "tailwindcss";

/**
 * PahadPulse design system — a vibrant multi-hue alpine / Himalayan palette
 * with a Mussoorie / Uttarakhand hill-town identity: crisp fresh teal-leaning
 * greens, a vivid glacier/sky blue, a warm sunrise amber, and a cool slate for
 * depth. These tokens are the single source of truth shared across every page.
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
        // Crisp, fresh alpine green — the primary brand colour (teal-leaning,
        // higher saturation than the old muted forest green).
        forest: {
          50: "#e8faf1",
          100: "#c6f3dd",
          200: "#8ee7bd",
          300: "#54d79a",
          400: "#28c483",
          500: "#17b47f",
          600: "#1f8a5b",
          700: "#1f8a5b",
          800: "#166b4a",
          900: "#0f5f44",
          950: "#063b2b",
        },
        // Cool glacier off-whites — the hill-town morning haze.
        mist: {
          50: "#fbfdfd",
          100: "#f1f7f6",
          200: "#e2efed",
          300: "#cde3df",
          400: "#aecfc9",
          white: "#fbfdfd",
        },
        // Livelier accent green for highlights and ridge motifs.
        pine: {
          400: "#2fd79a",
          500: "#17b47f",
          600: "#108a63",
        },
        // Warm, vivid sunrise accent for emphasis (Himalayan golden hour).
        dawn: {
          400: "#ffc14d",
          500: "#f6a623",
          600: "#e08a0b",
        },
        // Vivid glacier / sky blue — a new multi-hue accent.
        sky: {
          50: "#e8f6fd",
          100: "#c6eafa",
          200: "#90d6f4",
          300: "#54bdeb",
          400: "#38bdf8",
          500: "#1d9bd1",
          600: "#0c6fa0",
          700: "#0a567c",
        },
        // Cool slate for depth and secondary surfaces.
        slate: {
          50: "#f1f5f7",
          100: "#dde6ea",
          200: "#bccbd3",
          300: "#94aab6",
          400: "#7a94a3",
          500: "#4b6472",
          600: "#39505c",
          700: "#2b3f4a",
          800: "#1d2d35",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "sans-serif"],
      },
      boxShadow: {
        ridge: "0 16px 40px -16px rgba(15, 95, 68, 0.35)",
        tile: "0 1px 2px 0 rgba(18, 59, 47, 0.07), 0 10px 24px -14px rgba(18, 59, 47, 0.22)",
        glow: "0 8px 28px -10px rgba(29, 155, 209, 0.4)",
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.25rem",
      },
      backgroundImage: {
        // Fresh glacier-to-meadow haze used by the app body.
        "hill-haze":
          "linear-gradient(160deg, #fbfdfd 0%, #eef7f6 38%, #e2efed 70%, #e4f1fb 100%)",
        // Vivid alpine sidebar gradient: sky blue sweeping into deep green.
        "forest-header":
          "linear-gradient(150deg, #0a567c 0%, #0f5f44 48%, #1f8a5b 100%)",
        // Lively sunrise-over-ridge accent for hero/emphasis surfaces.
        "dawn-ridge":
          "linear-gradient(120deg, #1d9bd1 0%, #17b47f 55%, #f6a623 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
