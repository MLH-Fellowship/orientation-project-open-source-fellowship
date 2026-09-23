import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import React from "react";
import { act, create } from "react-test-renderer";
import { createServer } from "vite";

let server;
let App;
before(async () => {
  server = await createServer({
    server: { middlewareMode: true },
    appType: "custom",
    optimizeDeps: { noDiscovery: true, include: [] },
  });
  ({ default: App } = await server.ssrLoadModule("/src/App.jsx"));
});
after(async () => server?.close());

const json = (data) => new Response(JSON.stringify(data));
const deferred = () => {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
};

async function mount(t, request) {
  t.mock.method(globalThis, "fetch", async (url, options) => {
    if (url === "/api/conversations" && !options) {
      return json({ items: [{ id: "other", title: "Other chat" }] });
    }
    return request(url, options);
  });
  const previousDocument = globalThis.document;
  const previousStorage = globalThis.localStorage;
  globalThis.document = {
    documentElement: { getAttribute: () => "light", setAttribute() {} },
  };
  globalThis.localStorage = { setItem() {} };
  t.after(() => {
    globalThis.document = previousDocument;
    globalThis.localStorage = previousStorage;
  });
  let view;
  await act(async () => { view = create(React.createElement(App)); });
  t.after(async () => { await act(async () => view.unmount()); });
  return view;
}

function component(view, name) {
  return view.root.find((node) => node.type?.name === name);
}

test("loading history shows a loading status without suggesting an assistant reply", async (t) => {
  const pending = deferred();
  const view = await mount(t, async () => pending.promise);
  let selecting;
  await act(async () => { selecting = component(view, "Sidebar").props.onSelectConversation("other"); });
  const loadingView = JSON.stringify(view.toJSON());
  assert.match(loadingView, /Loading conversation/);
  assert.doesNotMatch(loadingView, /Thinking|Assistant is typing|Say hello/);
  assert.equal(component(view, "MessageInput").props.disabled, true);
  await act(async () => {
    pending.resolve(json({ id: "other", messages: [{ id: "old", role: "user", content: "Previous message" }] }));
    await selecting;
  });
  assert.doesNotMatch(JSON.stringify(view.toJSON()), /Loading conversation/);
  assert.equal(component(view, "MessageList").props.messages[0].content, "Previous message");
  assert.equal(component(view, "MessageInput").props.disabled, false);
});

test("selecting the current chat keeps its reply streaming", async (t) => {
  let stream;
  let signal;
  let historyRequests = 0;
  const view = await mount(t, async (url, options) => {
    if (url === "/api/conversations") return json({ id: "chat", title: "New" });
    if (!options) {
      historyRequests += 1;
      return json({ id: "chat", messages: [] });
    }
    signal = options.signal;
    return new Response(new ReadableStream({ start(controller) { stream = controller; } }));
  });
  let sending;
  await act(async () => { sending = component(view, "MessageInput").props.onSend("Hello"); });
  await act(async () => component(view, "Sidebar").props.onSelectConversation("chat"));
  assert.equal(signal.aborted, false);
  assert.equal(historyRequests, 0);
  assert.equal(component(view, "MessageInput").props.disabled, true);
  await act(async () => {
    stream.enqueue(new TextEncoder().encode('event: done\ndata: {"id":"saved","role":"assistant","content":"Hello back"}\n\n'));
    await sending;
  });
  assert.equal(component(view, "MessageList").props.messages.at(-1).content, "Hello back");
});

test("HTTP rejection marks the user message unsent without an interrupted reply", async (t) => {
  const view = await mount(t, async (url) => url === "/api/conversations"
    ? json({ id: "chat", title: "New" })
    : new Response('{"error":{"code":422,"message":"Request validation failed"}}', { status: 422 }));
  await act(async () => component(view, "MessageInput").props.onSend("x".repeat(10001)));
  const messages = component(view, "MessageList").props.messages;
  assert.equal(messages.length, 1);
  assert.equal(messages[0].role, "user");
  assert.equal(messages[0].failed, true);
  assert.equal(messages[0].content.length, 10001);
  assert.equal(component(view, "MessageInput").props.disabled, false);
  assert.match(JSON.stringify(view.toJSON()), /Not sent/);
  assert.doesNotMatch(JSON.stringify(view.toJSON()), /Reply interrupted/);
});

test("SSE quota errors do not mark an accepted user message unsent", async (t) => {
  const view = await mount(t, async (url) => url === "/api/conversations"
    ? json({ id: "chat", title: "New" })
    : new Response('event: error\ndata: {"error":{"code":429,"message":"Quota exceeded"}}\n\n'));
  await act(async () => component(view, "MessageInput").props.onSend("Hello"));
  const messages = component(view, "MessageList").props.messages;
  assert.equal(messages[0].failed, undefined);
  assert.equal(messages[1].interrupted, true);
});

test("deleting a streaming chat cancels its request and ignores late completion", async (t) => {
  let stream;
  let signal;
  const view = await mount(t, async (url, options) => {
    if (options?.method === "DELETE") return new Response(null, { status: 204 });
    if (url === "/api/conversations") return json({ id: "chat", title: "New" });
    signal = options.signal;
    return new Response(new ReadableStream({ start(controller) { stream = controller; } }));
  });
  let sending;
  await act(async () => { sending = component(view, "MessageInput").props.onSend("Hello"); });
  await act(async () => component(view, "Sidebar").props.onDeleteConversation("chat"));
  assert.equal(signal.aborted, true);
  await act(async () => {
    stream.enqueue(new TextEncoder().encode('event: done\ndata: {"id":"saved","role":"assistant","content":"Late"}\n\n'));
    await sending;
  });
  assert.deepEqual(component(view, "MessageList").props.messages, []);
  assert.equal(component(view, "MessageInput").props.disabled, false);
  assert.equal(component(view, "Sidebar").props.selectedConversationId, null);
});

test("renaming a conversation updates the sidebar", async (t) => {
  const view = await mount(t, async (url, options) => {
    assert.equal(url, "/api/conversations/other");
    assert.equal(options.method, "PATCH");
    assert.deepEqual(JSON.parse(options.body), { title: "Renamed" });
    return json({ id: "other", title: "Renamed" });
  });
  await act(async () => component(view, "Sidebar").props.onRenameConversation("other", "Renamed"));
  assert.equal(component(view, "Sidebar").props.conversations[0].title, "Renamed");
});

test("renders tokens before completion and replaces the cursor with the saved reply", async (t) => {
  let stream;
  const view = await mount(t, async (url) => {
    if (url === "/api/conversations") return json({ id: "chat", title: "New" });
    return new Response(new ReadableStream({ start(controller) { stream = controller; } }));
  });
  let sending;
  await act(async () => { sending = component(view, "MessageInput").props.onSend("Hello"); });
  assert.equal(component(view, "MessageInput").props.disabled, true);
  await act(async () => stream.enqueue(new TextEncoder().encode('event: token\ndata: {"content":"First"}\n\n')));
  let messages = component(view, "MessageList").props.messages;
  assert.equal(messages.at(-1).content, "First");
  assert.equal(messages.at(-1).streaming, true);
  assert.equal(view.root.findAllByProps({ "aria-label": "Assistant is typing" }).length, 1);
  await act(async () => {
    stream.enqueue(new TextEncoder().encode('event: done\ndata: {"id":"saved","role":"assistant","content":"First reply"}\n\n'));
    await sending;
  });
  messages = component(view, "MessageList").props.messages;
  assert.equal(messages.at(-1).id, "saved");
  assert.equal(component(view, "MessageInput").props.disabled, false);
  assert.equal(view.root.findAllByProps({ "aria-label": "Assistant is typing" }).length, 0);
});

test("switching chats ignores late tokens and completion", async (t) => {
  let stream;
  let signal;
  const view = await mount(t, async (url, options) => {
    if (url === "/api/conversations") return json({ id: "chat", title: "New" });
    if (url === "/api/conversations/other") return json({ id: "other", messages: [] });
    signal = options.signal;
    // Deliberately deliver data even after abort to exercise the stale-result guard.
    return new Response(new ReadableStream({ start(controller) { stream = controller; } }));
  });
  let sending;
  await act(async () => { sending = component(view, "MessageInput").props.onSend("Hello"); });
  await act(async () => component(view, "Sidebar").props.onSelectConversation("other"));
  assert.equal(signal.aborted, true);
  await act(async () => {
    stream.enqueue(new TextEncoder().encode('event: token\ndata: {"content":"Wrong chat"}\n\nevent: done\ndata: {"id":"saved","role":"assistant","content":"Wrong chat"}\n\n'));
    await sending;
  });
  assert.deepEqual(component(view, "MessageList").props.messages, []);
  assert.equal(component(view, "Sidebar").props.selectedConversationId, "other");
});

test("failed creation removes unsent history and offers retry", async (t) => {
  let fail = true;
  const view = await mount(t, async (url) => {
    if (fail) return new Response('{"detail":"Unavailable"}', { status: 503 });
    if (url === "/api/conversations") return json({ id: "chat", title: "New" });
    return new Response('event: done\ndata: {"id":"saved","role":"assistant","content":"Hello back"}\n\n');
  });
  await act(async () => component(view, "MessageInput").props.onSend("Hello"));
  assert.deepEqual(component(view, "MessageList").props.messages, []);
  assert.equal(component(view, "MessageInput").props.disabled, false);
  assert.equal(typeof component(view, "ErrorBanner").props.onRetry, "function");
  fail = false;
  await act(async () => component(view, "ErrorBanner").props.onRetry());
  assert.deepEqual(component(view, "MessageList").props.messages.map((m) => m.content), ["Hello", "Hello back"]);
});

test("partial stream failure preserves text, removes typing, and does not offer resend", async (t) => {
  const view = await mount(t, async (url) => url === "/api/conversations"
    ? json({ id: "chat", title: "New" })
    : new Response('event: token\ndata: {"content":"Partial"}\n\nevent: error\ndata: {"error":{"message":"Could not generate reply"}}\n\n'));
  await act(async () => component(view, "MessageInput").props.onSend("Hello"));
  const reply = component(view, "MessageList").props.messages.at(-1);
  assert.equal(reply.content, "Partial");
  assert.equal(reply.interrupted, true);
  assert.equal(reply.streaming, false);
  assert.equal(component(view, "MessageInput").props.disabled, false);
  assert.equal(component(view, "ErrorBanner").props.onRetry, undefined);
});

test("starting a new chat during creation prevents a late send", async (t) => {
  const pending = deferred();
  let streamRequests = 0;
  const view = await mount(t, async (url) => {
    if (url === "/api/conversations") return pending.promise;
    streamRequests += 1;
    throw new Error("Unexpected send");
  });
  let sending;
  await act(async () => { sending = component(view, "MessageInput").props.onSend("Hello"); });
  await act(async () => component(view, "Sidebar").props.onNewConversation());
  await act(async () => {
    pending.resolve(json({ id: "late", title: "Late" }));
    await sending;
  });
  assert.equal(streamRequests, 0);
  assert.deepEqual(component(view, "MessageList").props.messages, []);
  assert.equal(component(view, "Sidebar").props.selectedConversationId, null);
});

test("failed history load disables sending until retry succeeds", async (t) => {
  let fail = true;
  const view = await mount(t, async () => fail
    ? new Response('{"detail":"Unavailable"}', { status: 503 })
    : json({ id: "other", messages: [{ id: "old", role: "user", content: "History" }] }));
  await act(async () => component(view, "Sidebar").props.onSelectConversation("other"));
  assert.equal(component(view, "MessageInput").props.disabled, true);
  fail = false;
  await act(async () => component(view, "ErrorBanner").props.onRetry());
  assert.equal(component(view, "MessageInput").props.disabled, false);
  assert.equal(component(view, "MessageList").props.messages[0].content, "History");
});

test("late history responses cannot overwrite the selected conversation", async (t) => {
  const pending = deferred();
  const view = await mount(t, async (url) => url.endsWith("/slow")
    ? pending.promise : json({ id: "other", messages: [] }));
  let selecting;
  await act(async () => { selecting = component(view, "Sidebar").props.onSelectConversation("slow"); });
  await act(async () => component(view, "Sidebar").props.onSelectConversation("other"));
  await act(async () => {
    pending.resolve(json({ id: "slow", messages: [] }));
    await selecting;
  });
  assert.equal(component(view, "Sidebar").props.selectedConversationId, "other");
});
