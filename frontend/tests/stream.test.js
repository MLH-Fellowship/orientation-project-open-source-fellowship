import assert from "node:assert/strict";
import { test } from "node:test";
import { streamMessage } from "../src/api/client.js";

function mockStream(t, text, size = 1) {
  const bytes = new TextEncoder().encode(text);
  let offset = 0;
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url, "/api/conversations/chat/messages/stream");
    assert.deepEqual(JSON.parse(options.body), { content: "Hello" });
    return new Response(new ReadableStream({
      pull(controller) {
        if (offset >= bytes.length) return controller.close();
        controller.enqueue(bytes.slice(offset, offset + size));
        offset += size;
      },
    }));
  });
}

for (const size of [1, 4096]) {
  test(`streams tokens across chunks of ${size} bytes`, async (t) => {
    mockStream(t, ': heartbeat\r\n\r\nevent: token\r\ndata: {"content":"Hi 🌍"}\r\n\r\n'
      + 'event: token\ndata: {"content":"!"}\n\n'
      + 'event: done\ndata: {"id":"saved","role":"assistant","content":"Hi 🌍!"}\n\n', size);
    const tokens = [];
    const result = await streamMessage("chat", "Hello", { onToken: (token) => tokens.push(token) });
    assert.deepEqual(tokens, ["Hi 🌍", "!"]);
    assert.equal(result.id, "saved");
  });
}

test("reports server stream errors after partial content", async (t) => {
  mockStream(t, 'event: token\ndata: {"content":"Partial"}\n\n'
    + 'event: error\ndata: {"error":{"message":"Could not generate reply"}}\n\n');
  const tokens = [];
  await assert.rejects(streamMessage("chat", "Hello", { onToken: (token) => tokens.push(token) }), /Could not generate reply/);
  assert.deepEqual(tokens, ["Partial"]);
});

test("rejects an incomplete stream", async (t) => {
  mockStream(t, 'event: token\ndata: {"content":"Partial"}\n\n');
  await assert.rejects(streamMessage("chat", "Hello", { onToken() {} }), /interrupted/);
});

test("reports HTTP errors", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response('{"detail":"Conversation not found"}', { status: 404 }));
  await assert.rejects(streamMessage("chat", "Hello", { onToken() {} }), /Conversation not found/);
});

test("passes cancellation to fetch", async (t) => {
  const controller = new AbortController();
  controller.abort();
  t.mock.method(globalThis, "fetch", async (_url, { signal }) => {
    assert.equal(signal, controller.signal);
    signal.throwIfAborted();
  });
  await assert.rejects(streamMessage("chat", "Hello", { signal: controller.signal, onToken() {} }), { name: "AbortError" });
});

test("shows the backend's standardized HTTP error message", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response('{"error":{"code":404,"message":"Conversation not found"}}', { status: 404 }));
  await assert.rejects(streamMessage("chat", "Hello", { onToken() {} }), /Conversation not found/);
});

for (const frame of [
  'event: token\ndata: {}\n\n',
  'event: done\ndata: {"id":"saved"}\n\n',
]) {
  test(`rejects malformed payload: ${frame.split("\n")[0]}`, async (t) => {
    mockStream(t, frame);
    await assert.rejects(streamMessage("chat", "Hello", { onToken() { assert.fail("Invalid token delivered"); } }), /invalid reply/);
  });
}
