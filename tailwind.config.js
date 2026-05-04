/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#080a0f',
          800: '#0d1017',
          700: '#111520',
          600: '#161b2a',
          500: '#1c2235',
          400: '#252d42',
          300: '#2e3850',
        },
      },
    },
  },
  plugins: [],
}
