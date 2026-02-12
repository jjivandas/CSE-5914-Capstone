import { Box, Stack } from "@mantine/core";
import { useAutoScroll } from "../../hooks/useAutoScroll";
import { ChatMessage } from "./ChatMessage";
import type { ChatMessage as IChatMessage } from "../../api/types";

// --- Main Component ---

interface MessageListProps {
  messages: IChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const scrollRef = useAutoScroll([messages]);

  return (
    <Box flex={1} style={{ overflowY: "auto" }} p="md">
      <Stack gap="xl">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={scrollRef} />
      </Stack>
    </Box>
  );
}
