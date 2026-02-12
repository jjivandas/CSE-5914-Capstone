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
    <Stack gap={2}>
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text size="sm" fw={500}>
        {value}
      </Text>
    </Stack>
  );
}

function CardHeader({ stock }: { stock: StockProfile }) {
  return (
    <Group justify="space-between" mb="md">
      <div>
        <Text size="lg" fw={700} component="span">
          {stock.ticker}
        </Text>
        <Text size="sm" c="dimmed" component="span" ml="xs">
          {stock.companyName}
        </Text>
      </div>
      <Badge color="green" variant="light" size="lg">
        {stock.matchPercent}% Match
      </Badge>
    </Group>
  );
}

function CardMetrics({ stock }: { stock: StockProfile }) {
  return (
    <SimpleGrid cols={{ base: 2, xs: 3 }} spacing="sm" verticalSpacing="md">
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
    <Stack gap="xs" mt="lg" pt="md" style={{ borderTop: "1px solid var(--mantine-color-gray-2)" }}>
      <Text size="xs" c="dimmed" fw={700} tt="uppercase">
        Why it fits
      </Text>
      <Text size="sm" c="dark.3" lh={1.5}>
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
      padding="lg"
      radius="md"
      className={classes.card}
      component="a"
      href={stock.detailsUrl || "#"}
      target="_blank"
    >
      <CardHeader stock={stock} />
      <CardMetrics stock={stock} />
      <CardReasoning reason={stock.whyFits} />
    </Card>
  );
}
