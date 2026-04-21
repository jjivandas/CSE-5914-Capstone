import { Anchor, Badge, Box, Card, Group, SimpleGrid, Stack, Text } from "@mantine/core";
import classes from "./StockCard.module.css";
import type { StockProfile } from "../../api/types";

// --- Helpers ---

function fmtUsd(val?: number | null): string | null {
  if (val == null) return null;
  const abs = Math.abs(val);
  if (abs >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

/** Return a color for a numeric value: green if positive, red if negative. */
function valColor(val?: number | null): string {
  if (val == null) return "white";
  return val >= 0 ? "teal.4" : "red.4";
}

/** Parse a margin string like "23.5%" or "-1.2%" and return a color. */
function marginColor(val?: string | null): string {
  if (!val) return "white";
  const num = parseFloat(val);
  if (isNaN(num)) return "white";
  return num >= 0 ? "teal.4" : "red.4";
}

// --- Sub-Components ---

interface MetricProps {
  label: string;
  value?: string | number | null;
  color?: string;
}

function Metric({ label, value, color = "white" }: MetricProps) {
  return (
    <Stack gap={1}>
      <Text fz={10} c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text size="xs" fw={500} c={value != null ? color : "dimmed"}>
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
    <Group justify="space-between" mb="xs" wrap="nowrap" align="flex-start">
      <Stack gap={0} style={{ minWidth: 0, flex: 1 }}>
        <Text size="md" fw={700} c="white" truncate>
          {stock.ticker || "N/A"}
        </Text>
        <Text size="xs" c="dimmed" truncate>
          {stock.companyName}
        </Text>
      </Stack>
      <Group gap="xs" wrap="nowrap">
        <PriceOrLink stock={stock} />
        <Badge color="green" variant="light" size="sm">
          {stock.exchange || "N/A"}
        </Badge>
      </Group>
    </Group>
  );
}

function CardMetrics({ stock }: { stock: StockProfile }) {
  const hasRow4 = stock.ocf != null || stock.currentRatio != null || stock.grossMargin != null;

  return (
    <SimpleGrid cols={3} spacing="xs" verticalSpacing={8}>
      {/* Row 1 */}
      <Metric label="Fiscal Year" value={stock.fiscalYear ? `FY${stock.fiscalYear}` : null} />
      <Metric label="Revenue" value={fmtUsd(stock.revenue)} color={valColor(stock.revenue)} />
      <Metric label="Net Income" value={fmtUsd(stock.netIncome)} color={valColor(stock.netIncome)} />

      {/* Separator */}
      <Box
        my={4}
        style={{
          gridColumn: "1 / -1",
          borderBottom: "1px solid var(--mantine-color-dark-6)",
        }}
      />

      {/* Row 2 */}
      <Metric label="Gross Profit" value={fmtUsd(stock.grossProfit)} color={valColor(stock.grossProfit)} />
      <Metric label="Operating Inc." value={fmtUsd(stock.operatingIncome)} color={valColor(stock.operatingIncome)} />
      <Metric label="Profit Margin" value={stock.profitMargin} color={marginColor(stock.profitMargin)} />

      {/* Row 3 */}
      <Metric label="Total Assets" value={fmtUsd(stock.totalAssets)} />
      <Metric label="Cash" value={fmtUsd(stock.cash)} />
      <Metric label="EPS" value={stock.epsD != null ? `$${stock.epsD.toFixed(2)}` : null} color={valColor(stock.epsD)} />

      {/* Row 4 (conditional) */}
      {hasRow4 && (
        <>
          <Box
            my={4}
            style={{
              gridColumn: "1 / -1",
              borderBottom: "1px solid var(--mantine-color-dark-6)",
            }}
          />
          <Metric label="OCF" value={fmtUsd(stock.ocf)} color={valColor(stock.ocf)} />
          <Metric label="Current Ratio" value={stock.currentRatio} />
          <Metric label="Gross Margin" value={stock.grossMargin} color={marginColor(stock.grossMargin)} />
        </>
      )}
    </SimpleGrid>
  );
}

function CardReasoning({ reason }: { reason?: string }) {
  if (!reason) return null;
  return (
    <Box
      mt="sm"
      pt="xs"
      pl="sm"
      style={{
        borderTop: "1px solid var(--mantine-color-dark-5)",
        borderLeft: "3px solid var(--mantine-color-stockragGreen-7)",
      }}
    >
      <Text fz={10} c="dimmed" fw={700} tt="uppercase" mb={2}>
        Why it fits
      </Text>
      <Text size="xs" c="gray.3" lh={1.4}>
        {reason}
      </Text>
    </Box>
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
      style={{ borderColor: "var(--mantine-color-dark-5)" }}
    >
      <CardHeader stock={stock} />
      <CardMetrics stock={stock} />
      <CardReasoning reason={stock.whyFits} />
    </Card>
  );
}
