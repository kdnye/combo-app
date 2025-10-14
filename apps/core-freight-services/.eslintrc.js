module.exports = {
  root: true,
  extends: ['next/core-web-vitals', 'prettier'],
  parserOptions: {
    project: './tsconfig.json'
  },
  rules: {
    'react/function-component-definition': [
      'error',
      {
        namedComponents: 'arrow-function',
        unnamedComponents: 'arrow-function'
      }
    ],
    'react/jsx-props-no-spreading': 'off'
  }
};
