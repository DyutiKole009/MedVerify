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
          50: '#f0f7ff',
          100: '#e0effe',
          500: '#0284c7',
          600: '#0369a1',
          700: '#075985',
          800: '#0c4a6e',
          900: '#082f49',
        },
        safety: {
          clear: '#10b981',
          nsq: '#f59e0b',
          spurious: '#ef4444',
          community: '#8b5cf6',
        }
      }
    },
  },
  plugins: [],
}
