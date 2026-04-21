import { ActionIcon, Box, Text, Textarea, Group } from "@mantine/core";
import { IconSend } from "@tabler/icons-react";
import { useChatInput } from "../../hooks/useChatInput";

interface ChatInputProps {
  onSend: (text: string) => void;
  isLoading?: boolean;
}

export function ChatInput(props: ChatInputProps) {
  const { value, setValue, handleSend, handleKeyDown } = useChatInput(props);

  return (
    <Box>
      <Group align="flex-end" gap="xs">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about stocks, sectors, or financials..."
          autosize
          minRows={1}
          maxRows={4}
          flex={1}
          radius="md"
          size="md"
          disabled={props.isLoading}
          styles={{
            input: {
              transition: "border-color 0.2s ease, box-shadow 0.2s ease",
              "&:focus": {
                borderColor: "var(--mantine-color-stockragGreen-6)",
                boxShadow: "0 0 0 2px rgba(16, 185, 129, 0.15)",
              },
            },
          }}
        />
        <ActionIcon
          size="lg"
          radius="xl"
          variant="filled"
          color="stockragGreen"
          onClick={handleSend}
          disabled={!value.trim() || props.isLoading}
          mb={4}
        >
          <IconSend size={18} />
        </ActionIcon>
      </Group>
      <Text size="10px" c="dimmed" mt={4} ta="center">
        Press Enter to send &middot; Shift+Enter for new line
      </Text>
    </Box>
  );
}
