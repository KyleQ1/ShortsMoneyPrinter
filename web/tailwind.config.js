/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f7f7f4",
        ink: "#202124",
        muted: "#6b6f76",
        line: "#d9ddd6",
        accent: "#0f766e",
        danger: "#b91c1c",
        warning: "#b45309",
        success: "#15803d",
      },
      boxShadow: {
        panel: "0 1px 2px rgba(32, 33, 36, 0.04)",
      },
    },
  },
  plugins: [],
};
