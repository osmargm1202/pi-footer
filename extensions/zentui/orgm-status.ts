export const PI_CAVEMAN_STATE_KEY = "pi-caveman:state";
export const PI_CAVEMAN_STATE_EVENT = "pi-caveman:state";
export const SESSION_TITLE_ENTRY_TYPE = "session-title";
export const TITLE_STATE_EVENT = "title:state-changed";

export const OBSERVED_CAVEMAN_LEVELS = [
	"lite",
	"full",
	"ultra",
	"wenyan-lite",
	"wenyan-full",
	"wenyan-ultra",
] as const;

export type ObservedCavemanLevel = (typeof OBSERVED_CAVEMAN_LEVELS)[number];

export interface ObservedCavemanState {
	schemaVersion: 1;
	packageName: "pi-caveman";
	enabled: boolean;
	level: ObservedCavemanLevel | null;
	defaultLevel: ObservedCavemanLevel;
	autoEnable: boolean;
	source: "startup" | "command" | "input" | "config";
	updatedAt: number;
}

export interface OrgmStatusState {
	title: string;
	caveman: ObservedCavemanState | null;
}

type SessionEntryLike = { type?: string; customType?: string; data?: unknown };

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isObservedCavemanLevel(value: unknown): value is ObservedCavemanLevel {
	return (
		typeof value === "string" && (OBSERVED_CAVEMAN_LEVELS as readonly string[]).includes(value)
	);
}

function isObservedSource(value: unknown): value is ObservedCavemanState["source"] {
	return value === "startup" || value === "command" || value === "input" || value === "config";
}

function sanitizeTitle(value: unknown): string {
	if (typeof value !== "string") return "";
	return value.replace(/\s+/g, " ").trim();
}

export function normalizeObservedCavemanState(value: unknown): ObservedCavemanState | null {
	if (!isRecord(value)) return null;
	if (value.schemaVersion !== 1) return null;
	if (value.packageName !== "pi-caveman") return null;
	if (typeof value.enabled !== "boolean") return null;
	if (!isObservedCavemanLevel(value.defaultLevel)) return null;
	if (typeof value.autoEnable !== "boolean") return null;
	if (!isObservedSource(value.source)) return null;
	if (typeof value.updatedAt !== "number" || !Number.isFinite(value.updatedAt)) return null;
	if (value.level !== null && !isObservedCavemanLevel(value.level)) return null;

	return {
		schemaVersion: 1,
		packageName: "pi-caveman",
		enabled: value.enabled,
		level: value.level,
		defaultLevel: value.defaultLevel,
		autoEnable: value.autoEnable,
		source: value.source,
		updatedAt: value.updatedAt,
	};
}

export function formatObservedCavemanStatus(state: ObservedCavemanState): string {
	return state.enabled && state.level ? `caveman:${state.level}` : "caveman:off";
}

export function restoreOrgmStatusState(entries: readonly SessionEntryLike[]): OrgmStatusState {
	let title = "";
	let caveman: ObservedCavemanState | null = null;

	for (const entry of entries) {
		if (entry.type !== "custom") continue;
		if (entry.customType === SESSION_TITLE_ENTRY_TYPE && isRecord(entry.data)) {
			title = sanitizeTitle(entry.data.title);
			continue;
		}
		if (entry.customType === PI_CAVEMAN_STATE_KEY) {
			const normalized = normalizeObservedCavemanState(entry.data);
			if (normalized) caveman = normalized;
		}
	}

	return { title, caveman };
}

export function applyTitleState(state: OrgmStatusState, value: unknown): void {
	if (!isRecord(value)) {
		state.title = "";
		return;
	}
	state.title = sanitizeTitle(value.title);
}

export function applyCavemanState(state: OrgmStatusState, value: unknown): boolean {
	const normalized = normalizeObservedCavemanState(value);
	if (!normalized) return false;
	state.caveman = normalized;
	return true;
}

export function formatOrgmStatusLine(state: OrgmStatusState): string {
	const parts = [state.title, state.caveman ? formatObservedCavemanStatus(state.caveman) : ""];
	return parts.filter(Boolean).join(" · ");
}
