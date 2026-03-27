/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Cyber Fintech 配色方案
      colors: {
        // 深色背景层次
        cyber: {
          darker: '#0a0a0f',
          dark: '#0d0d14',
          base: '#12121a',
          light: '#1a1a25',
          lighter: '#252532',
        },
        // 霓虹主色 - 电子青
        neon: {
          cyan: '#00f5ff',
          blue: '#0080ff',
          purple: '#a855f7',
          pink: '#ff00aa',
          green: '#00ff88',
          yellow: '#ffdd00',
          orange: '#ff6b00',
        },
        // 状态色
        status: {
          profit: '#00ff88',
          loss: '#ff3366',
          warning: '#ffaa00',
          neutral: '#6b7280',
        },
        // 兼容旧代码
        primary: {
          50: '#e0f7ff',
          100: '#b3ecff',
          200: '#80e0ff',
          300: '#4dd4ff',
          400: '#26c9ff',
          500: '#00f5ff',
          600: '#00c4cc',
          700: '#009399',
          800: '#006266',
          900: '#003133',
        },
        success: '#00ff88',
        danger: '#ff3366',
        warning: '#ffaa00',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'SF Mono', 'monospace'],
        display: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'neon-cyan': '0 0 20px rgba(0, 245, 255, 0.3), 0 0 40px rgba(0, 245, 255, 0.1)',
        'neon-green': '0 0 20px rgba(0, 255, 136, 0.3), 0 0 40px rgba(0, 255, 136, 0.1)',
        'neon-pink': '0 0 20px rgba(255, 0, 170, 0.3), 0 0 40px rgba(255, 0, 170, 0.1)',
        'neon-purple': '0 0 20px rgba(168, 85, 247, 0.3), 0 0 40px rgba(168, 85, 247, 0.1)',
        'inner-glow': 'inset 0 0 30px rgba(0, 245, 255, 0.05)',
        'card': '0 4px 30px rgba(0, 0, 0, 0.5)',
      },
      backgroundImage: {
        'grid-pattern': `linear-gradient(rgba(0, 245, 255, 0.03) 1px, transparent 1px),
                         linear-gradient(90deg, rgba(0, 245, 255, 0.03) 1px, transparent 1px)`,
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'cyber-gradient': 'linear-gradient(135deg, #0a0a0f 0%, #12121a 50%, #0d0d14 100%)',
      },
      backgroundSize: {
        'grid': '50px 50px',
      },
      animation: {
        'pulse-slow': 'pulse-slow 3s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'scan': 'scan 3s linear infinite',
        'float': 'float 6s ease-in-out infinite',
        'data-stream': 'data-stream 2s linear infinite',
        'border-glow': 'border-glow 3s ease-in-out infinite',
      },
      keyframes: {
        'pulse-slow': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.7 },
        },
        'glow': {
          '0%': { boxShadow: '0 0 5px rgba(0, 245, 255, 0.5), 0 0 10px rgba(0, 245, 255, 0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(0, 245, 255, 0.8), 0 0 40px rgba(0, 245, 255, 0.4)' },
        },
        'scan': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'data-stream': {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '0% 100%' },
        },
        'border-glow': {
          '0%, 100%': { borderColor: 'rgba(0, 245, 255, 0.3)' },
          '50%': { borderColor: 'rgba(0, 245, 255, 0.6)' },
        },
      },
    },
  },
  plugins: [],
}
