/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "#0B1F3A",
          teal: "#0FA3A3",
          tealHover: "#0D8B8B",
          canvas: "#F7FAFC",
        },
        crowd: {
          green: "#22A06B",
          amber: "#F5A623",
          red: "#E5484D",
        }
      }
    },
  },
  plugins: [],
}

