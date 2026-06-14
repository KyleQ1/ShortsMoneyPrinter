/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Deep studio backdrop
        canvas: "#080a0f",
        night: "#0a0c12",
        // Elevated glass surfaces
        surface: "#11141d",
        "surface-2": "#161a25",
        "surface-3": "#1c2130",
        // Hairlines
        line: "#262b39",
        "line-strong": "#333a4d",
        // Text
        ink: "#eef1f6",
        muted: "#9aa3b6",
        faint: "#646d82",
        // Brand: emerald/teal "money" gradient
        accent: "#2dd4bf",
        "accent-strong": "#10b981",
        "accent-soft": "#0c3b36",
        // Semantic
        danger: "#f87171",
        warning: "#fbbf24",
        success: "#34d399",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "JetBrains Mono",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        panel: "0 1px 0 rgba(255,255,255,0.02) inset, 0 12px 32px -16px rgba(0,0,0,0.7)",
        glow: "0 0 0 1px rgba(45,212,191,0.25), 0 8px 30px -8px rgba(16,185,129,0.45)",
        "glow-soft": "0 8px 40px -12px rgba(16,185,129,0.35)",
      },
      backgroundImage: {
        "accent-gradient": "linear-gradient(135deg, #34d399 0%, #14b8a6 100%)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(45,212,191,0.5)" },
          "70%": { boxShadow: "0 0 0 8px rgba(45,212,191,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(45,212,191,0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.4s cubic-bezier(0.22, 1, 0.36, 1) both",
        "fade-in": "fade-in 0.3s ease-out both",
        "pulse-ring": "pulse-ring 1.8s ease-out infinite",
      },
    },
  },
  plugins: [],
};
