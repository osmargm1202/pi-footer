import { basename, dirname, extname, normalize } from "node:path";
import { truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";

export type SkillStatus = "loading" | "loaded" | "error";
export type SkillStyleKind =
	| "skillLoaded"
	| "skillLoading"
	| "skillError"
	| "skillBorder"
	| "skillGap";

function padToWidth(text: string, width: number): string {
	return text + " ".repeat(Math.max(0, width - visibleWidth(text)));
}

function sanitizeSkillName(name: string): string | undefined {
	const trimmed = name.trim();
	return trimmed ? trimmed : undefined;
}

export function getSkillNameFromPath(path: string): string | undefined {
	const normalizedPath = normalize(path).replace(/\\/g, "/");
	if (extname(normalizedPath).toLowerCase() !== ".md") return undefined;

	if (basename(normalizedPath) === "SKILL.md") {
		const skillName = basename(dirname(normalizedPath));
		if (skillName === "skills") return undefined;
		return sanitizeSkillName(skillName);
	}

	if (basename(dirname(normalizedPath)) !== "skills") return undefined;
	return sanitizeSkillName(basename(normalizedPath, extname(normalizedPath)));
}

export function renderSkillChip(
	name: string,
	status: SkillStatus,
	style: (kind: SkillStyleKind, text: string) => string,
): string {
	const suffix = status === "loading" ? "…" : status === "error" ? "!" : "";
	const label = `${name}${suffix}`;
	const labelKind =
		status === "loading" ? "skillLoading" : status === "error" ? "skillError" : "skillLoaded";
	return `${style("skillBorder", "▏")}${style(labelKind, label)}${style("skillBorder", "▕")}`;
}

export function renderSkillChipRows(
	skills: Map<string, SkillStatus>,
	width: number,
	style: (kind: SkillStyleKind, text: string) => string,
): string[] {
	if (width <= 0 || skills.size === 0) return [];
	const gap = style("skillGap", " ");
	const rows: string[] = [];
	let current = "";

	for (const [name, status] of skills.entries()) {
		const chip = renderSkillChip(name, status, style);
		const candidate = current ? `${current}${gap}${chip}` : chip;
		if (!current || visibleWidth(candidate) <= width) {
			current = candidate;
			continue;
		}
		rows.push(padToWidth(current, width));
		current = visibleWidth(chip) > width ? truncateToWidth(chip, width, "") : chip;
	}

	if (current) rows.push(padToWidth(current, width));
	return rows;
}
