/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    screens: {
      'xs': '360px',
      'sm': '600px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1440px',
    },
    extend: {
      colors: {
        navy: {
          DEFAULT: "var(--color-navy)",
          dark: "var(--color-navy-dark)",
        },
        teal: {
          DEFAULT: "var(--color-teal)",
          hover: "var(--color-teal-hover)",
          tint: "var(--color-teal-tint)",
        },
        surface: {
          DEFAULT: "var(--color-surface)",
          bg: "var(--color-background)",
        },
        border: {
          DEFAULT: "var(--color-border)",
          subtle: "var(--color-border-subtle)",
        },
        tx: {
          DEFAULT: "var(--color-text)",
          muted: "var(--color-text-muted)",
          inverse: "var(--color-text-inverse)",
        },
        crowd: {
          low: "var(--color-crowd-low)",
          'low-tint': "var(--color-crowd-low-tint)",
          'low-border': "var(--color-crowd-low-border)",
          mod: "var(--color-crowd-mod)",
          'mod-text': "var(--color-crowd-mod-text)",
          'mod-tint': "var(--color-crowd-mod-tint)",
          'mod-border': "var(--color-crowd-mod-border)",
          high: "var(--color-crowd-high)",
          'high-tint': "var(--color-crowd-high-tint)",
          'high-border': "var(--color-crowd-high-border)",
          unknown: "var(--color-crowd-unknown)",
          'unknown-tint': "var(--color-crowd-unknown-tint)",
          'unknown-border': "var(--color-crowd-unknown-border)",
        }
      },
      borderRadius: {
        control: "var(--radius-control)",
        panel: "var(--radius-panel)",
        badge: "var(--radius-badge)",
        chip: "var(--radius-chip)",
      },
      boxShadow: {
        overlay: "var(--shadow-overlay)",
      },
      transitionDuration: {
        fast: "var(--duration-fast)",
        medium: "var(--duration-medium)",
        slow: "var(--duration-slow)",
      },
      transitionTimingFunction: {
        transit: "var(--ease-transit)",
      }
    },
  },
  plugins: [],
}
