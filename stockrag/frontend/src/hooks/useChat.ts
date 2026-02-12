import { useState, useCallback } from "react";
import { fetchRecommendations } from "../api/client";
import type {
  ChatMessage,
  RecommendationResponse,
  Role,
} from "../api/types";

// --- Helpers ---

function generateId(): string {
  return crypto.randomUUID();
}

function createMsg(
  role: Role,
  text: string,
  status: ChatMessage["status"] = "sent",
): ChatMessage {
  return {
    id: generateId(),
    role,
    text,
    createdAt: Date.now(),
    status,
  };
}

function createAssistantMsg(response: RecommendationResponse): ChatMessage {
  return {
    id: generateId(),
    role: "assistant",
    createdAt: Date.now(),
    content: {
      text: response.message,
      stocks: response.recommendations,
    },
  };
}

// --- Hook ---

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addMessage = (msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  };

  const markMessageSent = (id: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, status: "sent" } : m)),
    );
  };

  const markMessageError = (id: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, status: "error" } : m)),
    );
  };

  const handleSuccess = useCallback(
    (userMsgId: string, resp: RecommendationResponse) => {
      markMessageSent(userMsgId);
      addMessage(createAssistantMsg(resp));
      setError(null);
    },
    [],
  );

  const handleFailure = useCallback((userMsgId: string) => {
    markMessageError(userMsgId);
    setError("Failed to fetch recommendations. Please try again.");
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const userMsg = createMsg("user", text, "sending");
      addMessage(userMsg);
      setIsLoading(true);

      try {
        const resp = await fetchRecommendations({ query: text });
        handleSuccess(userMsg.id, resp);
      } catch {
        handleFailure(userMsg.id);
      } finally {
        setIsLoading(false);
      }
    },
    [handleSuccess, handleFailure],
  );

  return {
    messages,
    isLoading,
    error,
    sendMessage,
  };
}
