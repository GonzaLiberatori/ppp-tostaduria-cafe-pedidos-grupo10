/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        coffee: {
          50:  '#faf6f3',
          100: '#f0eae3',
          200: '#e1d5c9',
          300: '#c9b8a3',
          400: '#a89070',
          500: '#8B6F47',
          600: '#735839',
          700: '#5d462e',
          800: '#4a3726',
          900: '#3d2e1f',
          950: '#221810',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 2px 8px -2px rgba(61, 46, 31, 0.08), 0 4px 16px -4px rgba(61, 46, 31, 0.06)',
        'card': '0 1px 3px rgba(61, 46, 31, 0.08), 0 4px 6px -2px rgba(61, 46, 31, 0.04)',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
      },
    },
  },
  plugins: [],
}