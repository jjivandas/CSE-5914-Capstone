import { MantineProvider } from '@mantine/core';
import '@mantine/core/styles.css';
import './styles/global.css';
import { theme } from './styles/theme';
import { MainLayout } from './components/layout/MainLayout';

export default function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <MainLayout />
    </MantineProvider>
  );
}
