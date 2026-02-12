import { Box, Paper, Text, SimpleGrid } from "@mantine/core";
import { StockCard } from "../stock/StockCard";
import type { AssistantContent } from "../../api/types";

// --- User Message ---

export function UserMessage({ text }: { text?: string }) {
  if (!text) return null;
  return (
    <Box style={{ alignSelf: "flex-end", maxWidth: "80%" }}>
      <Paper p="md" radius="md" bg="blue.1">
        <Text size="sm" c="dark.9">
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
    <SimpleGrid cols={{ base: 1, md: 2 }} mt="md">
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
    <Box style={{ alignSelf: "flex-start", width: "100%" }}>
      <Paper p="md" radius="md" bg="gray.0" withBorder>
        <Text size="sm" mb={content.stocks?.length ? "sm" : 0} c="dark.9">
          {content.text}
        </Text>
        <StockGrid stocks={content.stocks} />
      </Paper>
    </Box>
  );
}
