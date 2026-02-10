import { Paper, Stack, Box } from '@mantine/core';
import { AppHeader } from '../header/AppHeader';

export function MainLayout() {
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
      <Stack flex={1} bg="dark.9" p={30} style={{ overflowY: 'auto' }} gap={24}>
        {/* Chat Placeholder */}
      </Stack>
      <Box px={30} py={20} bg="dark.9" style={{ borderTop: '1px solid var(--mantine-color-dark-7)' }}>
        {/* Input Placeholder */}
      </Box>
    </Paper>
  );
}
