import type { Config } from 'tailwindcss';
import { tailwindTheme } from './design-tokens';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: tailwindTheme.colors,
      fontFamily: tailwindTheme.fontFamily,
      borderRadius: {
        '2xl': '1.5rem'
      },
      boxShadow: {
        soft: '0 10px 30px -15px rgba(15, 23, 42, 0.25)'
      }
    }
  },
  plugins: []
};

export default config;
