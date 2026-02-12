import { useState, KeyboardEvent, useCallback } from "react";

interface UseChatInputProps {
  onSend: (text: string) => void;
  isLoading?: boolean;
}

export function useChatInput({ onSend, isLoading }: UseChatInputProps) {
  const [value, setValue] = useState("");

  const handleSend = useCallback(() => {
    if (!value.trim() || isLoading) return;
    onSend(value);
    setValue("");
  }, [value, isLoading, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return { value, setValue, handleSend, handleKeyDown };
}
