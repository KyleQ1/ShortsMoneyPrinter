/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Light app backdrop
        canvas: "#f6f7fb",
        night: "#0a0c12",
        surface: "#ffffff",
        "surface-2": "#f8fafc",
        "surface-3": "#eef2f7",
        line: "#e2e8f0",
        "line-strong": "#cbd5e1",
        // Text
        ink: "#172033",
        muted: "#64748b",
        faint: "#94a3b8",
        // Brand accent
        accent: "#2563eb",
        "accent-strong": "#1d4ed8",
        "accent-soft": "#dbeafe",
        // Semantic
        danger: "#dc2626",
        warning: "#d97706",
        success: "#059669",
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
        panel: "0 1px 2px rgba(15,23,42,0.04), 0 16px 36px -26px rgba(15,23,42,0.28)",
        glow: "0 8px 24px -12px rgba(37,99,235,0.55)",
        "glow-soft": "0 8px 24px -18px rgba(37,99,235,0.45)",
      },
      backgroundImage: {
        "accent-gradient": "linear-gradient(135deg, #2563eb 0%, #0f766e 100%)",
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
          "0%": { boxShadow: "0 0 0 0 rgba(37,99,235,0.35)" },
          "70%": { boxShadow: "0 0 0 8px rgba(37,99,235,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(37,99,235,0)" },
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
