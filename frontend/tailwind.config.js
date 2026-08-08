/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#030712",
        surface: "rgba(255,255,255,0.05)",
        border: "rgba(255,255,255,0.1)",
        accent: "#a78bfa",
        "accent-hover": "#8b5cf6",
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
}

