import { useEffect, useRef, useState } from "react";

const MAX_TITLE_LENGTH = 200;

export default function ConversationHistoryItem({
  id,
  title,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  isSelected,
}) {
  const [mode, setMode] = useState("view");
  const [draft, setDraft] = useState(title);
  const inputRef = useRef(null);
  const settledRef = useRef(false);

  useEffect(() => {
    if (mode === "rename" && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [mode]);

  function startRename() {
    settledRef.current = false;
    setDraft(title);
    setMode("rename");
  }

  function commitRename() {
    if (settledRef.current) return;
    settledRef.current = true;
    const next = draft.trim();
    setMode("view");
    if (next && next !== title) onRenameConversation(id, next);
  }

  function cancelRename() {
    settledRef.current = true;
    setMode("view");
  }

  function handleRenameKeyDown(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      commitRename();
    } else if (event.key === "Escape") {
      event.preventDefault();
      cancelRename();
    }
  }

  function confirmDelete() {
    setMode("view");
    onDeleteConversation(id);
  }

  if (mode === "rename") {
    return (
      <li>
        <input
          ref={inputRef}
          className="conversation-rename-input"
          type="text"
          aria-label="Conversation title"
          maxLength={MAX_TITLE_LENGTH}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleRenameKeyDown}
          onBlur={commitRename}
        />
      </li>
    );
  }

  if (mode === "confirm-delete") {
    return (
      <li className="conversation-delete-confirm" role="group" aria-label={`Delete ${title}`}>
        <span className="conversation-delete-prompt">Delete this conversation?</span>
        <span className="conversation-item-actions confirm">
          <button type="button" className="danger" onClick={confirmDelete}>
            Delete
          </button>
          <button type="button" onClick={() => setMode("view")}>
            Cancel
          </button>
        </span>
      </li>
    );
  }

  return (
    <li className="conversation-item">
      <button
        type="button"
        onClick={() => onSelectConversation(id)}
        className={`${isSelected ? "selected" : ""}`}
      >
        {title}
      </button>
      <span className="conversation-item-actions">
        <button type="button" aria-label={`Rename ${title}`} onClick={startRename}>
          Rename
        </button>
        <button
          type="button"
          className="danger"
          aria-label={`Delete ${title}`}
          onClick={() => setMode("confirm-delete")}
        >
          Delete
        </button>
      </span>
    </li>
  );
}
