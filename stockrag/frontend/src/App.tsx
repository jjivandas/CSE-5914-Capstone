import { Box, MantineProvider } from "@mantine/core";
import { theme } from "./styles/theme";
import { MainLayout } from "./components/layout/MainLayout";
import { MessageList } from "./components/chat/MessageList";
import { WelcomeScreen } from "./components/chat/WelcomeScreen";
import { ChatInput } from "./components/chat/ChatInput";
import { useChat } from "./hooks/useChat";
import "@mantine/core/styles.css";
import "./styles/global.css";

function App() {
  const { messages, isLoading, sendMessage } = useChat();

  return (
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <Box
        h="100vh"
        bg="dark.9"
        p="md"
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Box w="100%" maw={1400} h="90vh">
          <MainLayout
            footer={<ChatInput onSend={sendMessage} isLoading={isLoading} />}
          >
            {messages.length === 0 ? (
              <WelcomeScreen onChipClick={sendMessage} />
            ) : (
              <MessageList messages={messages} isLoading={isLoading} />
            )}
          </MainLayout>
        </Box>
      </Box>
    </MantineProvider>
  );
}

export default App;