function timestamp(value) {
  if (!value) return null;
  const date = new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export default function MessageList({ messages, loading }) {
  return (
    <div id="message-list">
      {messages.length === 0 && !loading && (
        <div className="empty-state"><span className="empty-spark" aria-hidden="true">✦</span><h2>What’s on your mind?</h2><p>Ask a question, explore an idea, or just say hello.</p></div>
      )}
      {messages.map((m) => (
        <div key={m.id} className={`message-item ${m.role}`}>
          <div className="avatar" aria-label={m.role === "user" ? "You" : "Assistant"}>{m.role === "user" ? "U" : "✦"}</div>
          <div className="message-body"><div className="message-bubble">
          {m.content}
          {m.failed && <span className="muted-text"> (Not sent)</span>}
          {m.streaming && (
            <span role="status" aria-label="Assistant is typing">
              {!m.content && <span className="thinking-text">Thinking...</span>}
              <span className="streaming-cursor" aria-hidden="true">▍</span>
            </span>
          )}
          {m.interrupted && <span className="muted-text"> (Reply interrupted)</span>}
          </div>{timestamp(m.created_at) && <time className="message-time" dateTime={m.created_at}>{timestamp(m.created_at)}</time>}</div>
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
