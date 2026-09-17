import { useEffect, useState } from "react";

import {
  createConversation,
  getConversation,
  listConversations,
  sendMessage,
} from "./api/client.js";
import MessageInput from "./components/MessageInput.jsx";
import MessageList from "./components/MessageList.jsx";
import Sidebar from "./components/Sidebar.jsx";

import "./app.css";

const initialState = {
  conversationId: null,
  messages: [],
  loading: false,
};

// Barebones single-conversation UI. There's no streaming yet -- those are fellow issues (see ISSUES.md).
export default function App() {
  const [conversationState, setConversationState] = useState(initialState);
  const [conversations, setConversations] = useState([]);

  useEffect(() => {
    async function fetchConversations() {
      const data = await listConversations();
      setConversations(data.items);
    }
    fetchConversations();
  }, []);

  async function createNewConversation() {
    const newConversation = await createConversation("New Conversation");
    setConversationState(() => ({
      ...initialState,
      conversationId: newConversation.id,
    }));
    setConversations((prev) => [
      { id: newConversation.id, title: newConversation.title },
      ...prev,
    ]);
    return newConversation;
  }

  async function handleSend(text) {
    let currentConversationId = conversationState.conversationId;

    if (!conversationState.conversationId) {
      const newConversation = await createNewConversation();
      currentConversationId = newConversation.id;
    }

    setConversationState((prev) => ({
      ...prev,
      messages: [...prev.messages, { role: "user", content: text }],
      loading: true,
    }));

    await sendMessage(currentConversationId, text);

    const full = await getConversation(currentConversationId);
    setConversationState((prev) => ({
      ...prev,
      messages: full.messages,
      loading: false,
    }));
  }

  async function handleSelectConversation(id) {
    const conversation = await getConversation(id);

    if (conversation.detail) {
      alert("Error fetching conversation: " + conversation.detail);
      return;
    }

    setConversationState(() => ({
      ...initialState,
      conversationId: conversation.id,
      messages: conversation.messages,
    }));
  }

  async function handleNewConversation() {
    setConversationState(initialState);
  }

  return (
    <>
      <div id="app-container">
        <aside>
          <h1>MLH LLM Fellowship Project</h1>
          <Sidebar
            conversations={conversations}
            onNewConversation={handleNewConversation}
            onSelectConversation={handleSelectConversation}
            selectedConversationId={conversationState.conversationId}
          />
        </aside>
        <main>
          <MessageList
            messages={conversationState.messages}
            loading={conversationState.loading}
          />
          <MessageInput
            onSend={handleSend}
            disabled={conversationState.loading}
          />
        </main>
      </div>
    </>
  );
}
