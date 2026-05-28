module.exports = {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        neon: {
          50: '#f6f9ff',
          100: '#e6f0ff',
          300: '#7be0ff',
          500: '#00e5ff',
          700: '#00c0d6'
        },
        cyber: '#0f172a'
      },
      boxShadow: {
        'neon-lg': '0 10px 30px rgba(0,229,255,0.12)'
      }
    }
  },
  plugins: []
}
