import { describe, expect, it } from "vitest";
import {
	type OrgmStatusState,
	PI_CAVEMAN_STATE_EVENT,
	PI_CAVEMAN_STATE_KEY,
	SESSION_TITLE_ENTRY_TYPE,
	TITLE_STATE_EVENT,
	formatOrgmStatusLine,
	normalizeObservedCavemanState,
	restoreOrgmStatusState,
} from "../extensions/zentui/orgm-status";

describe("ORGM status integration", () => {
	it("uses shared ORGM event and entry contracts", () => {
		expect(PI_CAVEMAN_STATE_KEY).toBe("pi-caveman:state");
		expect(PI_CAVEMAN_STATE_EVENT).toBe("pi-caveman:state");
		expect(SESSION_TITLE_ENTRY_TYPE).toBe("session-title");
		expect(TITLE_STATE_EVENT).toBe("title:state-changed");
	});

	it("formats title and active caveman level", () => {
		const state: OrgmStatusState = {
			title: "Implement footer",
			caveman: {
				schemaVersion: 1,
				packageName: "pi-caveman",
				enabled: true,
				level: "full",
				defaultLevel: "lite",
				autoEnable: true,
				source: "command",
				updatedAt: 1,
			},
		};

		expect(formatOrgmStatusLine(state)).toBe("Implement footer · caveman:full");
	});

	it("formats off caveman without title generation", () => {
		const state: OrgmStatusState = {
			title: "",
			caveman: {
				schemaVersion: 1,
				packageName: "pi-caveman",
				enabled: false,
				level: null,
				defaultLevel: "lite",
				autoEnable: false,
				source: "startup",
				updatedAt: 1,
			},
		};

		expect(formatOrgmStatusLine(state)).toBe("caveman:off");
	});

	it("restores latest title and caveman entries", () => {
		const state = restoreOrgmStatusState([
			{ type: "custom", customType: SESSION_TITLE_ENTRY_TYPE, data: { title: "Old" } },
			{
				type: "custom",
				customType: PI_CAVEMAN_STATE_KEY,
				data: {
					schemaVersion: 1,
					packageName: "pi-caveman",
					enabled: true,
					level: "ultra",
					defaultLevel: "full",
					autoEnable: true,
					source: "input",
					updatedAt: 2,
				},
			},
			{ type: "custom", customType: SESSION_TITLE_ENTRY_TYPE, data: { title: "New" } },
		]);

		expect(state.title).toBe("New");
		expect(state.caveman?.level).toBe("ultra");
	});

	it("rejects invalid caveman state", () => {
		expect(normalizeObservedCavemanState({ packageName: "pi-caveman" })).toBeNull();
		expect(formatOrgmStatusLine({ title: "Only title", caveman: null })).toBe("Only title");
		expect(formatOrgmStatusLine({ title: "", caveman: null })).toBe("");
	});
});
