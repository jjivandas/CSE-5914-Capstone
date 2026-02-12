import { Card, Text, Group, Badge, Stack, SimpleGrid } from "@mantine/core";
import classes from "./StockCard.module.css";
import type { StockProfile } from "../../api/types";

// --- Sub-Components ---

interface MetricProps {
  label: string;
  value?: string | number;
}

function Metric({ label, value }: MetricProps) {
  if (!value) return null;
  return (
    <Stack gap={1}>
      <Text size="10px" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text size="xs" fw={500} c="white">
        {value}
      </Text>
    </Stack>
  );
}

function CardHeader({ stock }: { stock: StockProfile }) {
  return (
    <Group justify="space-between" mb="xs" wrap="nowrap">
      <div style={{ minWidth: 0 }}>
        <Text size="md" fw={700} component="span" c="white" truncate>
          {stock.ticker}
        </Text>
        <Text size="xs" c="dimmed" component="span" ml="xs" truncate>
          {stock.companyName}
        </Text>
      </div>
      <Badge color="green" variant="light" size="sm">
        {stock.matchPercent}%
      </Badge>
    </Group>
  );
}

function CardMetrics({ stock }: { stock: StockProfile }) {
  return (
    <SimpleGrid cols={3} spacing="xs" verticalSpacing="xs">
      <Metric label="Price" value={stock.peRatio} />
      <Metric label="Sector" value={stock.sector} />
      <Metric label="Industry" value={stock.industry} />
      <Metric label="Market Cap" value={stock.marketCap} />
      <Metric label="Employees" value={stock.employees?.toLocaleString()} />
      <Metric label="Founded" value={stock.founded} />
    </SimpleGrid>
  );
}

function CardReasoning({ reason }: { reason?: string }) {
  if (!reason) return null;
  return (
    <Stack gap={4} mt="sm" pt="xs" style={{ borderTop: "1px solid var(--mantine-color-dark-5)" }}>
      <Text size="10px" c="dimmed" fw={700} tt="uppercase">
        Why it fits
      </Text>
      <Text size="xs" c="gray.3" lh={1.4}>
        {reason}
      </Text>
    </Stack>
  );
}

// --- Main Component ---

interface StockCardProps {
  stock: StockProfile;
}

export function StockCard({ stock }: StockCardProps) {
  return (
    <Card
      withBorder
      padding="sm"
      radius="md"
      bg="dark.8"
      className={classes.card}
      component="a"
      href={stock.detailsUrl || "#"}
      target="_blank"
      style={{ borderColor: 'var(--mantine-color-dark-5)' }}
    >
      <CardHeader stock={stock} />
      <CardMetrics stock={stock} />
      <CardReasoning reason={stock.whyFits} />
    </Card>
  );
}
