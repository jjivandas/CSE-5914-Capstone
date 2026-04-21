import { Box, Group, Paper, Text, SimpleGrid } from "@mantine/core";
import { IconSparkles } from "@tabler/icons-react";
import Markdown from "react-markdown";
import { StockCard } from "../stock/StockCard";
import type { AssistantContent } from "../../api/types";

// --- Helpers ---

function formatTime(ts?: number): string {
  if (!ts) return "";
  return new Date(ts).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

// --- User Message ---

export function UserMessage({ text, createdAt }: { text?: string; createdAt?: number }) {
  if (!text) return null;
  return (
    <Box className="fade-in" style={{ alignSelf: "flex-end", maxWidth: "70%" }}>
      <Paper p="md" radius="md" bg="stockragGreen.9">
        <Text size="sm" c="white">
          {text}
        </Text>
      </Paper>
      <Text size="10px" c="dimmed" ta="right" mt={4} mr={4}>
        {formatTime(createdAt)}
      </Text>
    </Box>
  );
}

// --- Assistant Sub-Components ---

function StockGrid({ stocks }: { stocks?: AssistantContent["stocks"] }) {
  if (!stocks?.length) return null;
  return (
    <SimpleGrid cols={{ base: 1, xl: 2 }} mt="md">
      {stocks.map((stock, i) => (
        <Box
          key={stock.cik || stock.ticker}
          className="fade-in"
          style={{ animationDelay: `${i * 80}ms` }}
        >
          <StockCard stock={stock} />
        </Box>
      ))}
    </SimpleGrid>
  );
}

// --- Assistant Message ---

export function AssistantMessage({
  content,
  createdAt,
}: {
  content?: AssistantContent;
  createdAt?: number;
}) {
  if (!content) return null;
  return (
    <Box className="fade-in" style={{ alignSelf: "flex-start", maxWidth: "85%" }}>
      <Group gap="sm" align="flex-start" wrap="nowrap">
        <Box
          p={6}
          mt={2}
          bg="stockragGreen.9"
          style={{ borderRadius: "50%", flexShrink: 0 }}
        >
          <IconSparkles size={16} color="var(--mantine-color-stockragGreen-4)" />
        </Box>
        <Box style={{ minWidth: 0, flex: 1 }}>
          <Paper
            p="md"
            radius="md"
            bg="dark.7"
            withBorder
            style={{ borderColor: "var(--mantine-color-dark-6)" }}
          >
            <Box mb={content.stocks?.length ? "sm" : 0}>
              <Markdown
                components={{
                  p: ({ children }) => (
                    <Text size="sm" c="white" mb="xs">
                      {children}
                    </Text>
                  ),
                  strong: ({ children }) => (
                    <Text component="span" fw={700} c="white">
                      {children}
                    </Text>
                  ),
                  li: ({ children }) => (
                    <Text component="li" size="sm" c="white" ml="md">
                      {children}
                    </Text>
                  ),
                  h3: ({ children }) => (
                    <Text size="md" fw={700} c="white" mt="sm" mb="xs">
                      {children}
                    </Text>
                  ),
                  hr: () => (
                    <Box
                      my="sm"
                      style={{
                        borderTop: "1px solid var(--mantine-color-dark-5)",
                      }}
                    />
                  ),
                }}
              >
                {content.text}
              </Markdown>
            </Box>
            <StockGrid stocks={content.stocks} />
          </Paper>
          <Text size="10px" c="dimmed" mt={4} ml={4}>
            {formatTime(createdAt)}
          </Text>
        </Box>
      </Group>
    </Box>
  );
}
