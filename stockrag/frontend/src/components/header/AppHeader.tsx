import { Box, Group, Title } from '@mantine/core';
import { Logo } from '../ui/Logo';
import { StatusBadge } from '../ui/StatusBadge';

export function AppHeader() {
  return (
    <Box p={20} bg="dark.9" style={{ borderBottom: '1px solid var(--mantine-color-dark-7)' }}>
      <Group justify="space-between">
        <Group gap={16}>
          <Logo />
          <Title order={1} size={20} c="white" lts={-0.5}>StockRAG</Title>
        </Group>
        <StatusBadge />
      </Group>
    </Box>
  );
}
