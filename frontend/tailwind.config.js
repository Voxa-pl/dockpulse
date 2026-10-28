/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        charcoal: {
          900: '#0B0F19',
          800: '#111827',
          700: '#1F2937',
          600: '#374151'
        },
        yard: {
          green: '#10B981',
          amber: '#F59E0B',
          cyan: '#06B6D4',
          purple: '#8B5CF6',
          red: '#EF4444'
        }
      }
    },
  },
  plugins: [],
}
