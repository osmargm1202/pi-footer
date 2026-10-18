import type { ExtensionAPI, ExtensionContext, Theme } from "@earendil-works/pi-coding-agent";
import { afterEach, expect, it, vi } from "vitest";
import { emptyGitStatus, readGitStatus } from "../extensions/zentui/git";
import zentui from "../extensions/zentui/index";

vi.mock("../extensions/zentui/git", async (original) => ({
	...(await original<typeof import("../extensions/zentui/git")>()),
	readGitStatus: vi.fn(),
}));
vi.mock("../extensions/zentui/runtime", () => ({ readRuntimeInfo: vi.fn(async () => undefined) }));
vi.mock("../extensions/zentui/config", async (original) => {
	const config = await original<typeof import("../extensions/zentui/config")>();
	return {
		...config,
		ensureConfigExists: vi.fn(),
		loadConfig: () => ({
			...config.defaultConfig,
			features: { ...config.defaultConfig.features, editor: false },
		}),
	};
});

afterEach(() => vi.useRealTimers());

it("does not publish an old session's in-flight project refresh into its replacement", async () => {
	vi.useFakeTimers();
	type Handler = (event: unknown, ctx: ExtensionContext) => unknown;
	const handlers = new Map<string, Handler[]>();
	zentui({
		on(name: string, handler: Handler) {
			handlers.set(name, [...(handlers.get(name) ?? []), handler]);
		},
		registerCommand() {},
		getThinkingLevel: () => "off",
	} as unknown as ExtensionAPI);
	let resolveOld!: (status: ReturnType<typeof emptyGitStatus>) => void;
	vi.mocked(readGitStatus)
		.mockImplementationOnce(
			() =>
				new Promise((resolve) => {
					resolveOld = resolve;
				}),
		)
		.mockResolvedValue({ ...emptyGitStatus(), branch: "new-session-branch" });
	let footerFactory: Parameters<ExtensionContext["ui"]["setFooter"]>[0];
	const theme = {
		fg: (_token: string, text: string) => text,
		bold: (text: string) => text,
	} as Theme;
	const ctx = {
		mode: "tui",
		hasUI: true,
		cwd: "/tmp/project",
		sessionManager: { getBranch: () => [] },
		getContextUsage: () => undefined,
		ui: {
			theme,
			setFooter: (factory: typeof footerFactory) => {
				footerFactory = factory;
			},
			getEditorComponent: () => undefined,
			setEditorComponent() {},
		},
	} as unknown as ExtensionContext;
	const emit = async (name: string) => {
		for (const handler of handlers.get(name) ?? []) await handler({}, ctx);
	};
	try {
		await emit("session_start");
		await emit("session_shutdown");
		await emit("session_start");
		await vi.advanceTimersByTimeAsync(0);
		const footer = footerFactory?.({ requestRender() {} } as never, theme, {
			onBranchChange: () => () => {},
			getExtensionStatuses: () => new Map(),
		} as never);
		expect(footer?.render(200).join("\n")).toContain("new-session-branch");
		resolveOld({ ...emptyGitStatus(), branch: "stale-session-branch" });
		await vi.advanceTimersByTimeAsync(0);
		const rendered = footer?.render(200).join("\n");
		expect(rendered).toContain("new-session-branch");
		expect(rendered).not.toContain("stale-session-branch");
		footer?.dispose?.();
	} finally {
		await emit("session_shutdown");
	}
});
