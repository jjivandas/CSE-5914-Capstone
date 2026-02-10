import { Group, Box, Text } from '@mantine/core';

export function StatusBadge() {
  return (
    <Group
      gap={8}
      px={16}
      py={8}
      bg="dark.7"
      style={{ borderRadius: 20, border: '1px solid var(--mantine-color-dark-4)' }}
    >
      <Box
        w={6}
        h={6}
        bg="stockragGreen.5"
        style={{ borderRadius: '50%', boxShadow: '0 0 8px var(--mantine-color-stockragGreen-5)' }}
      />
      <Text size="xs" c="dimmed">
        System Online
      </Text>
    </Group>
  );
}
