import { useEffect, useState } from "react";

import {
  createConversation,
  getConversation,
  listConversations,
  sendMessage,
} from "./api/client.js";
import ErrorBanner from "./components/ErrorBanner.jsx";
import MessageInput from "./components/MessageInput.jsx";
import MessageList from "./components/MessageList.jsx";
import Sidebar from "./components/Sidebar.jsx";

import "./app.css";

const initialState = {
  conversationId: null,
  messages: [],
  loading: false,
};

function getInitialTheme() {
  if (typeof document !== "undefined") {
    const attr = document.documentElement.getAttribute("data-theme");
    if (attr === "light" || attr === "dark") return attr;
  }
  return "light";
}

// Barebones single-conversation UI. There's no streaming yet -- those are fellow issues (see ISSUES.md).
export default function App() {
  const [conversationState, setConversationState] = useState(initialState);
  const [conversations, setConversations] = useState([]);
  const [theme, setTheme] = useState(getInitialTheme);
  const [conversationsError, setConversationsError] = useState(null);
  const [mainError, setMainError] = useState(null);

  useEffect(() => {
    fetchConversations();
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("theme", theme);
    } catch (e) {
      console.debug("Unable to persist theme preference", e);
    }
  }, [theme]);

  function toggleTheme() {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }

  async function fetchConversations() {
    setConversationsError(null);
    try {
      const data = await listConversations();
      setConversations(data.items);
    } catch {
      setConversationsError("Couldn't load your conversations.");
    }
  }

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
    setMainError(null);
    let currentConversationId = conversationState.conversationId;
    let tempId = null;

    try {
      if (!currentConversationId) {
        const newConversation = await createNewConversation();
        currentConversationId = newConversation.id;
      }

      tempId = `pending-${Date.now()}`;
      setConversationState((prev) => ({
        ...prev,
        messages: [...prev.messages, { id: tempId, role: "user", content: text }],
        loading: true,
      }));

      await sendMessage(currentConversationId, text);
      const full = await getConversation(currentConversationId);
      setConversationState((prev) => ({
        ...prev,
        messages: full.messages,
        loading: false,
      }));
    } catch {
      setConversationState((prev) => ({
        ...prev,
        loading: false,
        messages: tempId
          ? prev.messages.filter((m) => m.id !== tempId)
          : prev.messages,
      }));
      setMainError({
        message: "Message failed to send.",
        retry: () => handleSend(text),
      });
    }
    
    fetchConversations()
  }

  async function handleSelectConversation(id) {
    setMainError(null);
    try {
      const conversation = await getConversation(id);
      setConversationState(() => ({
        ...initialState,
        conversationId: conversation.id,
        messages: conversation.messages,
      }));
    } catch {
      setMainError({
        message: "Couldn't load that conversation.",
        retry: () => handleSelectConversation(id),
      });
    }
  }

  async function handleNewConversation() {
    setMainError(null);
    setConversationState(initialState);
  }

  return (
    <>
      <div id="app-container">
        <aside>
          <div id="sidebar-header">
            <h1>MLH LLM Fellowship Project</h1>
            <button id="theme-toggle" onClick={toggleTheme}>
              {theme === "dark" ? "Light mode" : "Dark mode"}
            </button>
          </div>
          {conversationsError && (
            <ErrorBanner message={conversationsError} onRetry={fetchConversations} />
          )}
          <Sidebar
            conversations={conversations}
            onNewConversation={handleNewConversation}
            onSelectConversation={handleSelectConversation}
            selectedConversationId={conversationState.conversationId}
          />
        </aside>
        <main>
          {mainError && (
            <ErrorBanner message={mainError.message} onRetry={mainError.retry} />
          )}
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
