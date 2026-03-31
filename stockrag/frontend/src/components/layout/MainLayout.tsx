import { Paper, Box } from '@mantine/core';
import { AppHeader } from '../header/AppHeader';
import { ReactNode } from 'react';

interface MainLayoutProps {
  children: ReactNode;
  footer: ReactNode;
}

export function MainLayout({ children, footer }: MainLayoutProps) {
  return (
    <Paper
      w="100%"
      maw={1400}
      h="90vh"
      bg="dark.8"
      radius={16}
      withBorder
      style={{
        borderColor: 'var(--mantine-color-dark-7)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.8)',
      }}
    >
      <AppHeader />
      <Box flex={1} bg="dark.9" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {children}
      </Box>
      <Box px={30} py={20} bg="dark.9" style={{ borderTop: '1px solid var(--mantine-color-dark-7)' }}>
        {footer}
      </Box>
    </Paper>
  );
}
