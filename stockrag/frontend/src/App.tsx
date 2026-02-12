import { Center, MantineProvider } from "@mantine/core";
import { theme } from "./styles/theme";
import { MainLayout } from "./components/layout/MainLayout";
import { MessageList } from "./components/chat/MessageList";
import { ChatInput } from "./components/chat/ChatInput";
import { useChat } from "./hooks/useChat";
import "@mantine/core/styles.css";
import "./styles/global.css";

function App() {
  const { messages, isLoading, sendMessage } = useChat();

  return (
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <Center h="100vh" bg="dark.9" p="md">
        <MainLayout
          footer={<ChatInput onSend={sendMessage} isLoading={isLoading} />}
        >
          <MessageList messages={messages} />
        </MainLayout>
      </Center>
    </MantineProvider>
  );
}

export default App;