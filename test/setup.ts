import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll } from "vitest";

// Extension lifecycle tests create config on session_start. Never read/write the user's agent dir.
const agentDir = mkdtempSync(join(tmpdir(), "pi-footer-test-agent-"));
process.env.PI_CODING_AGENT_DIR = agentDir;
afterAll(() => rmSync(agentDir, { recursive: true, force: true }));
