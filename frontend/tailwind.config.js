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
        pertamina: {
          navy: '#002D62',
          'navy-dark': '#001D42',
          'navy-light': '#0B4080',
          red: '#ED1C24',
          'red-light': '#FDE8E9',
          green: '#009A44',
          'green-light': '#E6F5EC',
          blue: '#0072BC',
          'blue-light': '#E8F1F9',
          gray: {
            50: '#F8FAFC',
            100: '#F1F5F9',
            200: '#E2E8F0',
            300: '#CBD5E1',
            400: '#94A3B8',
            500: '#64748B',
            600: '#475569',
            700: '#334155',
            800: '#1E293B',
            900: '#0F172A',
          }
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'monospace'],
      },
      boxShadow: {
        'pertamina-sm': '0 1px 3px 0 rgba(0, 45, 98, 0.08)',
        'pertamina-md': '0 4px 6px -1px rgba(0, 45, 98, 0.12), 0 2px 4px -2px rgba(0, 45, 98, 0.08)',
        'pertamina-lg': '0 10px 15px -3px rgba(0, 45, 98, 0.15), 0 4px 6px -4px rgba(0, 45, 98, 0.1)',
        'sheet': '0 8px 30px rgba(0, 0, 0, 0.1)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.94)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'dropdown-pop': {
          from: { opacity: '0', transform: 'translateY(-8px) scale(0.97)' },
          to: { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        'pulse-dot': {
          '0%': { transform: 'scale(0.95)', boxShadow: '0 0 0 0 rgba(16, 185, 129, 0.5)' },
          '70%': { transform: 'scale(1)', boxShadow: '0 0 0 5px rgba(16, 185, 129, 0)' },
          '100%': { transform: 'scale(0.95)', boxShadow: '0 0 0 0 rgba(16, 185, 129, 0)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-in-out',
        'scale-in': 'scale-in 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        'dropdown-pop': 'dropdown-pop 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-dot': 'pulse-dot 2s infinite',
      },
    },
  },
  plugins: [],
}
