import { Anchor, Card, Text, Group, Badge, Stack, SimpleGrid } from "@mantine/core";
import classes from "./StockCard.module.css";
import type { StockProfile } from "../../api/types";

// --- Sub-Components ---

interface MetricProps {
  label: string;
  value?: string | number | null;
}

function Metric({ label, value }: MetricProps) {
  return (
    <Stack gap={1}>
      <Text size="10px" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text size="xs" fw={500} c="white">
        {value ?? "N/A"}
      </Text>
    </Stack>
  );
}

function PriceOrLink({ stock }: { stock: StockProfile }) {
  if (stock.currentPrice != null) {
    return (
      <Text size="sm" fw={700} c="teal.4">
        ${stock.currentPrice.toFixed(2)}
      </Text>
    );
  }
  if (stock.edgarUrl) {
    return (
      <Anchor
        href={stock.edgarUrl}
        target="_blank"
        rel="noopener noreferrer"
        size="xs"
        c="blue.4"
      >
        SEC Filings &rarr;
      </Anchor>
    );
  }
  return null;
}

function CardHeader({ stock }: { stock: StockProfile }) {
  return (
    <Group justify="space-between" mb="xs" wrap="nowrap">
      <div style={{ minWidth: 0 }}>
        <Text size="md" fw={700} component="span" c="white" truncate>
          {stock.ticker || "N/A"}
        </Text>
        <Text size="xs" c="dimmed" component="span" ml="xs" truncate>
          {stock.companyName}
        </Text>
      </div>
      <Group gap="xs" wrap="nowrap">
        <PriceOrLink stock={stock} />
        <Badge color="green" variant="light" size="sm">
          {stock.exchange || "N/A"}
        </Badge>
      </Group>
    </Group>
  );
}

function fmtUsd(val?: number | null): string | null {
  if (val == null) return null;
  const abs = Math.abs(val);
  if (abs >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

function CardMetrics({ stock }: { stock: StockProfile }) {
  const hasRow4 = stock.ocf != null || stock.currentRatio != null || stock.grossMargin != null;

  return (
    <SimpleGrid cols={3} spacing="xs" verticalSpacing="xs">
      {/* Row 1 */}
      <Metric label="Fiscal Year" value={stock.fiscalYear ? `FY${stock.fiscalYear}` : null} />
      <Metric label="Revenue" value={fmtUsd(stock.revenue)} />
      <Metric label="Net Income" value={fmtUsd(stock.netIncome)} />

      {/* Row 2 */}
      <Metric label="Gross Profit" value={fmtUsd(stock.grossProfit)} />
      <Metric label="Operating Income" value={fmtUsd(stock.operatingIncome)} />
      <Metric label="Profit Margin" value={stock.profitMargin} />

      {/* Row 3 */}
      <Metric label="Total Assets" value={fmtUsd(stock.totalAssets)} />
      <Metric label="Cash" value={fmtUsd(stock.cash)} />
      <Metric label="EPS" value={stock.epsD != null ? `$${stock.epsD.toFixed(2)}` : null} />

      {/* Row 4 (conditional) */}
      {hasRow4 && (
        <>
          <Metric label="OCF" value={fmtUsd(stock.ocf)} />
          <Metric label="Current Ratio" value={stock.currentRatio} />
          <Metric label="Gross Margin" value={stock.grossMargin} />
        </>
      )}
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
      style={{ borderColor: 'var(--mantine-color-dark-5)' }}
    >
      <CardHeader stock={stock} />
      <CardMetrics stock={stock} />
      <CardReasoning reason={stock.whyFits} />
    </Card>
  );
}
