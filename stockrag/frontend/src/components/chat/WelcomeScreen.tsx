import { Container, Title, Text, SimpleGrid, Paper, Stack, Box } from "@mantine/core";
import { IconSparkles, IconTrendingUp, IconChartPie, IconBolt } from "@tabler/icons-react";

// --- Constants ---

const EXAMPLES = [
  { icon: IconSparkles, text: "Semiconductor stocks with P/E < 25" },
  { icon: IconTrendingUp, text: "Cybersecurity with >20% revenue growth" },
  { icon: IconChartPie, text: "High-dividend healthcare with low debt" },
  { icon: IconBolt, text: "EV makers profitable in 2024" },
];

// --- Sub-Components ---

function WelcomeHeader() {
  return (
    <Stack align="center" gap="xs" mb="xl">
      <Box p="sm" bg="stockragGreen.9" style={{ borderRadius: "50%" }} c="stockragGreen.4">
        <IconSparkles size={32} />
      </Box>
      <Title order={2} size={32} fw={800} ta="center" c="white">
        AI-Powered Stock Discovery
      </Title>
      <Text c="dimmed" size="lg" ta="center" maw={500}>
        Ask complex questions about financials, industry trends, and growth metrics.
      </Text>
    </Stack>
  );
}

interface QueryChipProps {
  text: string;
  Icon: typeof IconSparkles;
  onClick: () => void;
}

function QueryChip({ text, Icon, onClick }: QueryChipProps) {
  return (
    <Paper
      component="button"
      onClick={onClick}
      p="md"
      radius="md"
      bg="dark.8"
      className="fade-in"
      style={{
        border: "1px solid var(--mantine-color-dark-6)",
        cursor: "pointer",
        textAlign: "left",
        transition: "all 0.2s ease",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--mantine-color-stockragGreen-6)")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--mantine-color-dark-6)")}
    >
      <Stack gap="xs">
        <Icon size={20} color="var(--mantine-color-stockragGreen-5)" />
        <Text size="sm" fw={500} c="gray.3">
          {text}
        </Text>
      </Stack>
    </Paper>
  );
}

// --- Main Component ---

interface WelcomeScreenProps {
  onChipClick: (text: string) => void;
}

export function WelcomeScreen({ onChipClick }: WelcomeScreenProps) {
  return (
    <Container size="sm" py={60}>
      <WelcomeHeader />
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {EXAMPLES.map((ex) => (
          <QueryChip
            key={ex.text}
            text={ex.text}
            Icon={ex.icon}
            onClick={() => onChipClick(ex.text)}
          />
        ))}
      </SimpleGrid>
    </Container>
  );
}
