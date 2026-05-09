/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        sans:    ['DM Sans', 'sans-serif'],
        mono:    ['JetBrains Mono', 'monospace'],
      },
      colors: {
        // Background layers
        surface: {
          DEFAULT: '#0d1f2d',
          light:   '#111f2e',
          card:    '#162534',
          border:  '#1e3a4a',
        },
        // Brand teal
        primary: {
          300: '#4dd8e0',
          400: '#2ac4ce',
          500: '#13a0a9',
          600: '#0e808c',
          700: '#0a6070',
          900: '#052030',
        },
        // Danger red
        danger: {
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
        },
        // Warning amber
        accent: {
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
        },
      },
      boxShadow: {
        'glow-teal':  '0 0 20px rgba(19,160,169,0.35)',
        'glow-amber': '0 0 20px rgba(245,158,11,0.35)',
      },
      animation: {
        'fade-in':    'fadeIn 0.3s ease-out',
        'slide-up':   'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:  { from: { opacity: 0 },                        to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(12px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
};