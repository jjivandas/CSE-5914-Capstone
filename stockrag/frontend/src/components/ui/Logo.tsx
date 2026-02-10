import { Box } from '@mantine/core';

export function Logo() {
  return (
    <Box
      w={40}
      h={40}
      style={{
        background: 'linear-gradient(135deg, var(--mantine-color-stockragGreen-5) 0%, var(--mantine-color-stockragGreen-6) 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontSize: 20,
        color: '#000',
      }}
      c="black"
      fw={700}
      fz={20}
      bg="stockragGreen.5"
      bgr={8}
    >
      SR
    </Box>
  );
}
