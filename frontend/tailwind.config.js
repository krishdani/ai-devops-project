/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0a0b",
        card: "#111114",
        border: "#1f1f23",
        primary: "#3b82f6",
        secondary: "#64748b",
        danger: "#ef4444",
        warning: "#f59e0b",
        success: "#10b981",
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
