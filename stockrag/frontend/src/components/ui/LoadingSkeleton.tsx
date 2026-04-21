import { useState, useEffect } from "react";
import { Box, Group, Loader, Paper, Text } from "@mantine/core";
import { IconSparkles } from "@tabler/icons-react";

const PHASES = [
  "Searching SEC filings...",
  "Analyzing companies...",
  "Generating response...",
];

export function LoadingSkeleton() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPhase((prev) => Math.min(prev + 1, PHASES.length - 1));
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box style={{ alignSelf: "flex-start", maxWidth: "85%" }} className="fade-in">
      <Group gap="sm" align="flex-start" wrap="nowrap">
        <Box
          p={6}
          mt={2}
          bg="stockragGreen.9"
          style={{ borderRadius: "50%", flexShrink: 0 }}
        >
          <IconSparkles size={16} color="var(--mantine-color-stockragGreen-4)" />
        </Box>
        <Paper
          p="md"
          radius="md"
          bg="dark.7"
          withBorder
          style={{ borderColor: "var(--mantine-color-dark-6)" }}
        >
          <Group gap="sm">
            <Loader size="xs" color="stockragGreen" type="dots" />
            <Text size="sm" c="dimmed" fw={500}>
              {PHASES[phase]}
            </Text>
          </Group>
        </Paper>
      </Group>
    </Box>
  );
}
