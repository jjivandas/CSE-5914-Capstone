import { Box, Stack } from "@mantine/core";
import { useAutoScroll } from "../../hooks/useAutoScroll";
import { ChatMessage } from "./ChatMessage";
import { LoadingSkeleton } from "../ui/LoadingSkeleton";
import type { ChatMessage as IChatMessage } from "../../api/types";

// --- Main Component ---

interface MessageListProps {
  messages: IChatMessage[];
  isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const scrollRef = useAutoScroll([messages, isLoading]);

  return (
    <Box flex={1} style={{ overflowY: "auto" }} p="md">
      <Stack gap="xl">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {isLoading && <LoadingSkeleton />}
        <div ref={scrollRef} />
      </Stack>
    </Box>
  );
}
