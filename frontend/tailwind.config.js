/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        agronex: {
          deep: '#0B5D3B',
          primary: '#16A36A',
          bright: '#22C55E',
          soft: '#E8F7EE',
          light: '#F5FBF7',
          darkText: '#16352A',
          secondaryText: '#60756A',
          bg: '#F7FBF8'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
