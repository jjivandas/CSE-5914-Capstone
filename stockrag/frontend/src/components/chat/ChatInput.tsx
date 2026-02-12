import { ActionIcon, Textarea, Group } from "@mantine/core";
import { IconSend } from "@tabler/icons-react";
import { useState, KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (text: string) => void;
  isLoading?: boolean;
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    if (!value.trim() || isLoading) return;
    onSend(value);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Group align="flex-end" gap="xs">
      <Textarea
        value={value}
        onChange={(e) => setValue(e.currentTarget.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about a stock..."
        autosize
        minRows={1}
        maxRows={4}
        flex={1}
        radius="md"
        size="md"
        disabled={isLoading}
      />
      <ActionIcon
        size="lg"
        radius="xl"
        variant="filled"
        color="blue"
        onClick={handleSend}
        disabled={!value.trim() || isLoading}
        mb={4}
      >
        <IconSend size={18} />
      </ActionIcon>
    </Group>
  );
}
