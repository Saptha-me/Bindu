# Pebbling Architecture

## Phase 1: Agent Creation with Cookiecutter

This phase outlines the single-line command process for agent creation:

```
 Pebbling Agent                      Sheldon (CA)                      Hibiscus Registry
       │                                   │                                   │
       │                                   │                                   │
       ├─── 1. Generate key pair           │                                   │
       │                                   │                                   │
       ├─── 2. Create DID                  │                                   │
       │                                   │                                   │
       │                                   │                                   │
       ├───────────────────────────────────┼───────────────────┐               │
       │                                   │                   │               │
       │             3. Register DID with Hibiscus             │               │
       │───────────────────────────────────────────────────────>│               │
       │                                   │                   │               │
       │                                   │          4. Validate & register DID
       │                                   │                   │───────────────┤
       │                                   │                   │               │
       │<───────────────────────────────────────────────────────┤               │
       │                                   │                   │               │
       │        5. Generate CSR            │                   │               │
       │                                   │                   │               │
       │        6. Create JWT proof        │                   │               │
       │                                   │                   │               │
       ├─── 7. Send CSR & JWT proof ──────>│                   │               │
       │                                   │                   │               │
       │                                   │                   │               │
       │                                   ├─── 8. Verify DID ─────────────────>│
       │                                   │                   │               │
       │                                   │        9. Confirm DID validity     │
       │                                   │<───────────────────────────────────┤
       │                                   │                                   │
       │                                   │                                   │
       │                                   ├─── 10. Issue certificate           │
       │                                   │                                   │
       │<───── 11. Receive certificate ────┤                                   │
       │                                   │                                   │
       │                                   │                                   │
       ├─── 12. Deploy with certificate    │                                   │
       │                                   │                                   │
       ├─── 13. Obtain deployment URL      │                                   │
       │                                   │                                   │
       ├─── 14. Update DID doc & registry ─────────────────────────────────────>│
       │          (with URL endpoint)      │                                   │
       │                                   │                   ┌───────────────┤
       │                                   │                   │ 15. Update DID│
       │                                   │                   │  with URL     │
       │                                   │                   └───────────────┤
       │                                   │                                   │
       ├─── 16. Start accepting secured    │                                   │
       │        mTLS connections           │                                   │
       │                                   │                                   │
```

## Phase 2: Mutual TLS (mTLS) Connection Establishment

After deployment and DID update, agents establish secure communication through mutual authentication:

```
Agent A                                Agent B
   │                                      │
   │ 1. Initiate TLS handshake            │
   │─────────────────────────────────────>│
   │                                      │
   │ 2. Respond with server certificate   │
   │<─────────────────────────────────────│
   │                                      │
   │ 3. Verify server certificate         │
   │    (Against Sheldon CA & DID doc)    │
   │                                      │
   │ 4. Provide client certificate        │
   │─────────────────────────────────────>│
   │                                      │
   │ 5. Verify client certificate         │
   │    (Against Sheldon CA & DID doc)    │
   │                                      │
   │ 6. Establish secured session         │
   │<────────────────────────────────────>│
   │                                      │
```

## Phase 3: Agent-to-Agent Communication (Secured)

After successful mTLS handshake, agents can exchange messages securely:

```
Agent A                                   Agent B
   │                                         │
   │ 1. Send encrypted request/message       │
   │────────────────────────────────────────>│
   │                                         │
   │ 2. Decrypt and authenticate request     │
   │                                         │
   │ 3. Execute requested operation          │
   │                                         │
   │ 4. Encrypt response (signed)            │
   │<────────────────────────────────────────│
   │                                         │
   │ 5. Decrypt and authenticate response    │
   │                                         │
```

## Complete End-to-End Pebbling Flow with mTLS & Communication

```
┌───────────┐                 ┌───────────────────────────────────┐                    ┌───────────┐
│ Human     │                 │ Pebbling Agent A                  │                    │ Agent B   │
│ User      │                 │                                   │                    │           │
└─────┬─────┘                 └──────────────┬────────────────────┘                    └─────┬─────┘
      │                                      │                                               │
      │                                      │                                               │
      │── 1. Ask Question (Huma Port) ──────>│                                               │
      │    ("Summarize document X")          │                                               │
      │                                      │                                               │
      │                                      │                                               │
      │                                      ├─── 2. Determine additional data needed        │
      │                                      │                                               │
      │                                      ├─── 3. Initiate Pebble Port mTLS handshake ───>│
      │                                      │                                               │
      │                                      │<─── 4. Mutual certificate verification ──────>│
      │                                      │                                               │
      │                                      │─── 5. Secure request via Pebble Port ────────>│
      │                                      │    ("Provide context data for document X")    │
      │                                      │                                               │
      │                                      │<─── 6. Secure response via Pebble Port ───────│
      │                                      │    ("Context data provided")                  │
      │                                      │                                               │
      │                                      ├─── 7. Process & summarize document            │
      │                                      │                                               │
      │<─── 8. Response via Huma Port ───────│                                               │
      │    ("Here's the summary of document X")                                              │
```

### Detailed Example Steps

1. **Human User → Agent A (Huma Port)**
   - User requests: "Summarize document X."

2. **Agent A (internal logic)**
   - Recognizes additional context required from Agent B.

3. **Agent A → Agent B (Pebble Port)**
   - Initiates secure connection via mTLS.

4. **Agent B ↔ Agent A (Pebble Port)**
   - Agents mutually authenticate using certificates issued by Sheldon CA & DID verified through Hibiscus.

5. **Agent A → Agent B (Pebble Port)**
   - Sends encrypted request: "Provide context data for document X."

6. **Agent B → Agent A (Pebble Port)**
   - Responds securely with encrypted context data.

7. **Agent A (internal logic)**
   - Processes the response and generates a summary.

8. **Agent A → Human User (Huma Port)**
   - Returns summarized result to the human user.
