export default function MessageList({ messages, loading }) {
  return (
    <div id="message-list">
      {messages.length === 0 && !loading && (
        <p className="muted-text">Say hello to start the conversation.</p>
      )}
      {messages.map((m) => (
        <div key={m.id} className="message-item">
          <strong>{m.role === "user" ? "You" : "Assistant"}:</strong>{" "}
          {m.content}
          {m.failed && <span className="muted-text"> (Not sent)</span>}
          {m.streaming && (
            <span role="status" aria-label="Assistant is typing">
              {!m.content && <span className="thinking-text">Thinking...</span>}
              <span className="streaming-cursor" aria-hidden="true">▍</span>
            </span>
          )}
          {m.interrupted && <span className="muted-text"> (Reply interrupted)</span>}
        </div>
      ))}
      {loading && !messages.some((m) => m.streaming) && (
        <div className="message-item muted-text" role="status">
          Loading conversation...
        </div>
      )}
    </div>
  );
}
