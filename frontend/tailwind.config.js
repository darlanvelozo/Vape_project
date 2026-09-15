/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Roxo-petróleo: identidade da marca sem cair no roxo genérico.
        marca: {
          50: '#f2f6fc', 100: '#e2ebf8', 200: '#cbdaf2', 300: '#a7c2e9',
          400: '#7ca2dd', 500: '#5c83d2', 600: '#4767c5', 700: '#3d55b4',
          800: '#374893', 900: '#313f75', 950: '#212848',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
