import { Box, Paper, Text, SimpleGrid } from "@mantine/core";
import { StockCard } from "../stock/StockCard";
import type { AssistantContent } from "../../api/types";

// --- User Message ---

export function UserMessage({ text }: { text?: string }) {
  if (!text) return null;
  return (
    <Box className="fade-in" style={{ alignSelf: "flex-end", maxWidth: "70%" }}>
      <Paper p="md" radius="md" bg="stockragGreen.9">
        <Text size="sm" c="white">
          {text}
        </Text>
      </Paper>
    </Box>
  );
}

// --- Assistant Sub-Components ---

function StockGrid({ stocks }: { stocks?: AssistantContent["stocks"] }) {
  if (!stocks?.length) return null;
  return (
    <SimpleGrid cols={{ base: 1, xl: 2 }} mt="md">
      {stocks.map((stock) => (
        <StockCard key={stock.ticker} stock={stock} />
      ))}
    </SimpleGrid>
  );
}

// --- Assistant Message ---

export function AssistantMessage({ content }: { content?: AssistantContent }) {
  if (!content) return null;
  return (
    <Box className="fade-in" style={{ alignSelf: "flex-start", maxWidth: "70%" }}>
      <Paper p="md" radius="md" bg="dark.7" withBorder style={{ borderColor: 'var(--mantine-color-dark-6)' }}>
        <Text size="sm" mb={content.stocks?.length ? "sm" : 0} c="white">
          {content.text}
        </Text>
        <StockGrid stocks={content.stocks} />
      </Paper>
    </Box>
  );
}
