import { UserMessage, AssistantMessage } from "./ChatBubbles";
import type { ChatMessage as IChatMessage } from "../../api/types";

export function ChatMessage({ message }: { message: IChatMessage }) {
  if (message.role === "user") {
    return <UserMessage text={message.text} />;
  }
  return <AssistantMessage content={message.content} />;
}
