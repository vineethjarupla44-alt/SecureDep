/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        aicte: {
          dark: '#0B2545',
          navy: '#134074',
          blue: '#1D4E89',
          light: '#EEF4F8',
          teal: '#00A896',
          mint: '#02C39A',
          amber: '#F59E0B',
          red: '#EF4444',
          slate: '#8DA9C4',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
