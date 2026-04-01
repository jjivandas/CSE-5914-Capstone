import { Box, Paper, Skeleton, Stack, Group } from "@mantine/core";

export function LoadingSkeleton() {
  return (
    <Box style={{ alignSelf: "flex-start", width: "100%" }} className="fade-in">
      <Paper p="md" radius="md" bg="gray.0" withBorder>
        <Stack gap="xs">
          <Skeleton height={12} width="70%" radius="xl" />
          <Skeleton height={12} width="90%" radius="xl" />
          <Skeleton height={12} width="40%" radius="xl" />
          <Group mt="sm">
             <Skeleton height={100} width="48%" radius="md" />
             <Skeleton height={100} width="48%" radius="md" />
          </Group>
        </Stack>
      </Paper>
    </Box>
  );
}
