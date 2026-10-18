import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const lock = JSON.parse(readFileSync(new URL("../package-lock.json", import.meta.url), "utf8")) as {
	packages: Record<string, { version?: string }>;
};

// Minimum patched releases from the advisories in the dependency audit. Check
// every copy, not just the hoisted package, so nested regressions also fail.
const patchedVersions = [
	["vitest", [4, 1, 11]],
	["@vitest/mocker", [4, 1, 11]],
	["nanoid", [3, 3, 18]],
	["postcss", [8, 5, 23]],
	["source-map-js", [1, 2, 2]],
] as const;

describe("development dependency security", () => {
	for (const [name, minimum] of patchedVersions) {
		it(`locks every ${name} copy to a patched release`, () => {
			const copies = Object.entries(lock.packages).filter(([path]) =>
				path.endsWith(`node_modules/${name}`),
			);
			expect(copies.length).toBeGreaterThan(0);
			for (const [path, pkg] of copies) {
				expect(pkg.version, path).toMatch(/^\d+\.\d+\.\d+$/);
				const version = (pkg.version ?? "").split(".").map(Number);
				const firstDifference = minimum.findIndex((part, index) => version[index] !== part);
				expect(
					firstDifference === -1 || version[firstDifference] > minimum[firstDifference],
					`${path}@${pkg.version} must be >=${minimum.join(".")}`,
				).toBe(true);
			}
		});
	}
});
