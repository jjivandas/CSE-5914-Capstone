import { ActionIcon, Textarea, Group } from "@mantine/core";
import { IconSend } from "@tabler/icons-react";
import { useChatInput } from "../../hooks/useChatInput";

interface ChatInputProps {
  onSend: (text: string) => void;
  isLoading?: boolean;
}

export function ChatInput(props: ChatInputProps) {
  const { value, setValue, handleSend, handleKeyDown } = useChatInput(props);

  return (
    <Group align="flex-end" gap="xs">
      <Textarea
        value={value}
        onChange={(e) => setValue(e.currentTarget.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about a stock..."
        autosize minRows={1} maxRows={4} flex={1} radius="md" size="md" disabled={props.isLoading}
      />
      <ActionIcon size="lg" radius="xl" variant="filled" color="blue" onClick={handleSend} disabled={!value.trim() || props.isLoading} mb={4}>
        <IconSend size={18} />
      </ActionIcon>
    </Group>
  );
}
