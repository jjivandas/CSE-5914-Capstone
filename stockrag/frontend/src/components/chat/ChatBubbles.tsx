import { Box, Paper, Text, SimpleGrid } from "@mantine/core";
import Markdown from "react-markdown";
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
        <StockCard key={stock.cik || stock.ticker} stock={stock} />
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
        <Box mb={content.stocks?.length ? "sm" : 0}>
          <Markdown
            components={{
              p: ({ children }) => <Text size="sm" c="white" mb="xs">{children}</Text>,
              strong: ({ children }) => <Text component="span" fw={700} c="white">{children}</Text>,
              li: ({ children }) => <Text component="li" size="sm" c="white" ml="md">{children}</Text>,
              h3: ({ children }) => <Text size="md" fw={700} c="white" mt="sm" mb="xs">{children}</Text>,
              hr: () => <Box my="sm" style={{ borderTop: '1px solid var(--mantine-color-dark-5)' }} />,
            }}
          >
            {content.text}
          </Markdown>
        </Box>
        <StockGrid stocks={content.stocks} />
      </Paper>
    </Box>
  );
}
