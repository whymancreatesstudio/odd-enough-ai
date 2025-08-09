import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        odd: {
          bg: '#0b0b0f',
          card: '#12121a',
          primary: '#ffe14d',
          text: '#f1f5f9',
          dim: '#a8b0bd',
          accent: '#8b5cf6'
        }
      },
      boxShadow: {
        soft: '0 10px 30px rgba(0,0,0,0.25)'
      },
      borderRadius: {
        '2xl': '1rem'
      }
    }
  },
  plugins: []
}
export default config
