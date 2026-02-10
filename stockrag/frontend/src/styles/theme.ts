import { createTheme, type MantineColorsTuple } from '@mantine/core';

const stockragGreen: MantineColorsTuple = [
  '#ecfdf5',
  '#d1fae5',
  '#a7f3d0',
  '#6ee7b7',
  '#34d399',
  '#10b981',
  '#059669',
  '#047857',
  '#065f46',
  '#064e3b',
];

const stockragDark: MantineColorsTuple = [
  '#C1C2C5',
  '#A6A7AB',
  '#909296',
  '#5C5F66',
  '#373A40',
  '#2C2E33',
  '#25262B',
  '#1f1f1f', // 7: Border
  '#0f0f0f', // 8: Component Bg
  '#0a0a0a', // 9: App Bg
];

export const theme = createTheme({
  primaryColor: 'stockragGreen',
  colors: {
    stockragGreen,
    dark: stockragDark,
  },
  fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  defaultRadius: 'md',
  autoContrast: true,
});
