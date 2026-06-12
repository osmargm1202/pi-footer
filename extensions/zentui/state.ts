import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import {
	buildContextLabel,
	buildCostLabel,
	buildTokenLabel,
	formatProviderLabel,
	getUsageTotals,
} from "./format";
import type { GitStatusSummary } from "./git";
import type { OrgmStatusState } from "./orgm-status";
import type { RuntimeInfo } from "./runtime";
import type { SkillStatus } from "./skill-status";

export type FooterState = GitStatusSummary & {
	modelLabel: string;
	providerLabel: string;
	contextLabel: string;
	tokenLabel: string;
	costLabel: string;
	runtime?: RuntimeInfo;
	orgmStatus: OrgmStatusState;
	timerLabel: string;
	skillStatuses: Map<string, SkillStatus>;
};

export function createInitialState(gitDefaults: GitStatusSummary): FooterState {
	return {
		modelLabel: "no-model",
		providerLabel: "Unknown",
		contextLabel: "--",
		tokenLabel: "↑0 ↓0",
		costLabel: "$0.000",
		runtime: undefined,
		orgmStatus: { title: "", caveman: null },
		timerLabel: "",
		skillStatuses: new Map<string, SkillStatus>(),
		...gitDefaults,
	};
}

export function syncState(state: FooterState, ctx: ExtensionContext, cacheHitIcon: string): void {
	const totals = getUsageTotals(ctx);
	state.modelLabel = ctx.model?.id ?? "no-model";
	state.providerLabel = formatProviderLabel(ctx.model?.provider);
	state.contextLabel = buildContextLabel(ctx);
	state.tokenLabel = buildTokenLabel(totals, cacheHitIcon);
	state.costLabel = buildCostLabel(totals);
}
