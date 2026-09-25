import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import SyntaxHighlighter from "react-syntax-highlighter/dist/esm/prism-light";
import { dracula } from "react-syntax-highlighter/dist/esm/styles/prism";

import javascript from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";

SyntaxHighlighter.registerLanguage("javascript", javascript);
SyntaxHighlighter.registerLanguage("python", python);
SyntaxHighlighter.registerLanguage("bash", bash);
SyntaxHighlighter.registerLanguage("json", json);

function timestamp(value) {
  if (!value) return null;
  const date = new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export default function MessageList({ messages, loading }) {
  const containerRef = useRef(null);
  const isAtBottomRef = useRef(true);
  const prevLengthRef = useRef(messages.length);

  function handleScroll(e) {
    const el = e.currentTarget;
    isAtBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < 100;
  }

  useEffect(() => {
    const el = containerRef.current;
    const prevLength = prevLengthRef.current;
    prevLengthRef.current = messages.length;
    if (!el) return;

    // Always follow the user's own message; otherwise only autoscroll if
    // they haven't scrolled away from the bottom (e.g. to read history).
    const userJustSent =
      messages.length > prevLength && messages[prevLength]?.role === "user";

    if (userJustSent || isAtBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, loading]);

  return (
    <div id="message-list" ref={containerRef} onScroll={handleScroll}>
      {messages.length === 0 && !loading && (
        <div className="empty-state"><span className="empty-spark" aria-hidden="true">✦</span><h2>What’s on your mind?</h2><p>Ask a question, explore an idea, or just say hello.</p></div>
      )}
      {messages.map((m) => (
        <div key={m.id} className={`message-item ${m.role}`}>
          <div className="avatar" aria-label={m.role === "user" ? "You" : "Assistant"}>
            {m.role === "user" ? "U" : "✦"}
          </div>
          <div className="message-body">
            <div className="message-bubble">
              {m.role === "assistant" ? (
                <div className="markdown-body">
                  <ReactMarkdown
                    components={{
                      // eslint-disable-next-line no-unused-vars
                      code({ node, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || "");
                        return match ? (
                          <SyntaxHighlighter
                            {...props}
                            style={dracula}
                            language={match[1]}
                            PreTag="div"
                          >
                            {String(children).replace(/\n$/, "")}
                          </SyntaxHighlighter>
                        ) : (
                          <code {...props} className={className}>
                            {children}
                          </code>
                        );
                      },
                    }}
                  >
                    {m.content}
                  </ReactMarkdown>
                </div>
              ) : (
                m.content
              )}
              {m.failed && <span className="muted-text"> (Not sent)</span>}
              {m.streaming && (
                <span role="status" aria-label="Assistant is typing">
                  {!m.content && <span className="thinking-text">Thinking...</span>}
                  <span className="streaming-cursor" aria-hidden="true">▍</span>
                </span>
              )}
              {m.interrupted && <span className="muted-text"> (Reply interrupted)</span>}
            </div>
            {timestamp(m.created_at) && (
              <time className="message-time" dateTime={m.created_at}>
                {timestamp(m.created_at)}
              </time>
            )}
          </div>
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
