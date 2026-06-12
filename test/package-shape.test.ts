import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

describe("package shape", () => {
	it("ships ORGM skills through pi-footer", () => {
		const manifest = JSON.parse(readFileSync("package.json", "utf8"));

		expect(manifest.files).toContain("skills");
		expect(manifest.pi.skills).toEqual(["./skills"]);
		expect(existsSync(join("skills", "osmar-ai", "SKILL.md"))).toBe(true);
		expect(existsSync(join("skills", "presupuesto-orgm", "SKILL.md"))).toBe(true);
	});
});
