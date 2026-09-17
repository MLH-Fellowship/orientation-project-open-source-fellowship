import { useState } from "react";

export default function MessageInput({ onSend, disabled }) {
  const [text, setText] = useState("");

  function handleSubmit() {
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
  }

  return (
    <div className="message-input">
      <input
        className="message-input-field"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        placeholder="Type a message..."
        disabled={disabled}
      />
      <button onClick={handleSubmit} disabled={disabled}>
        Send
      </button>
    </div>
  );
}
