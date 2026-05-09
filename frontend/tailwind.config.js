/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // MedMap brand palette — deep teal + amber accents
        primary: {
          50:  '#edfafa',
          100: '#d5f5f6',
          200: '#aaeaec',
          300: '#6dd8db',
          400: '#2cbec4',
          500: '#13a0a9',
          600: '#0e808c',
          700: '#0f6571',
          800: '#125260',
          900: '#134150',
          950: '#0a2a35',
        },
        accent: {
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
        },
        danger: {
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
        },
        surface: {
          DEFAULT: '#0d1f2d',
          light: '#162635',
          card:  '#1a2e3f',
          border: '#1e3a4a',
        }
      },
      fontFamily: {
        display: ['"Syne"', 'sans-serif'],
        body:    ['"DM Sans"', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.4s ease-out forwards',
        'slide-up': 'slideUp 0.4s ease-out forwards',
        'typewriter': 'typing 0.05s steps(1) forwards',
      },
      keyframes: {
        fadeIn:  { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(12px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
      },
      boxShadow: {
        'glow-teal':   '0 0 20px rgba(19,160,169,0.25)',
        'glow-red':    '0 0 20px rgba(239,68,68,0.25)',
        'glow-amber':  '0 0 20px rgba(245,158,11,0.20)',
      },
    },
  },
  plugins: [],
}
