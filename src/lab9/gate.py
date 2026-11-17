"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.graders import GRADERS
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded = {m["id"] for m in spec.get("metrics", []) if m["id"] in GRADERS}
    for name, report in (("PR", pr), ("baseline", base)):
        rows = report.get("rows", [])
        manifest = report.get("manifest", {})
        seeds = manifest.get("seeds", [])
        items = manifest.get("items", 0)
        if not seeds or len(set(seeds)) != len(seeds):
            problems.append(f"{name}: empty or duplicate manifest seeds")
        if not rows or len(rows) != items * len(seeds):
            problems.append(f"{name}: row count differs from items x seeds")
        pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
        if len(set(pairs)) != len(pairs):
            problems.append(f"{name}: duplicate item/seed rows")
        item_ids = {i for i, _ in pairs}
        if len(item_ids) != items or set(pairs) != {(i, seed) for i in item_ids for seed in seeds}:
            problems.append(f"{name}: incomplete item/seed coverage")
        if report.get("evaluator_failures"):
            problems.append(f"{name}: evaluator failures present")
        for mid, value in report.get("metrics", {}).items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                problems.append(f"{name}: invalid aggregate {mid}")
        for metric in spec.get("metrics", []):
            if metric["id"] not in report.get("metrics", {}):
                problems.append(f"{name}: missing aggregate {metric['id']}")
        for row in rows:
            for mid in graded:
                if type(row.get(mid)) is not bool:
                    problems.append(f"{name}: invalid row value {mid}")
            if "cost" in row and (not isinstance(row["cost"], (int, float)) or not math.isfinite(row["cost"]) or row["cost"] < 0):
                problems.append(f"{name}: invalid row cost")
        if rows and all(type(row.get(mid)) is bool for row in rows for mid in graded):
            for mid in graded:
                values = [row[mid] for row in rows]
                value = sum(values) if mid in {"secret_leak", "approval_bypass"} else round(sum(values)/len(values), 4)
                reported = report.get("metrics", {}).get(mid)
                if isinstance(reported, (int, float)) and not math.isclose(value, reported, abs_tol=1e-4):
                    problems.append(f"{name}: aggregate does not match rows: {mid}")
    pr_rows = {(r.get("item_id"), r.get("seed")): r for r in pr.get("rows", [])}
    base_rows = {(r.get("item_id"), r.get("seed")): r for r in base.get("rows", [])}
    if pr_rows.keys() != base_rows.keys():
        problems.append("PR item/seed set differs from baseline")
    for key in pr_rows.keys() & base_rows.keys():
        if set(pr_rows[key].get("slices") or []) != set(base_rows[key].get("slices") or []):
            problems.append(f"slice tags differ for {key}")
    for name, rows in (("PR", pr.get("rows", [])), ("baseline", base.get("rows", []))):
        tags = {}
        for row in rows:
            current = frozenset(row.get("slices") or [])
            if row["item_id"] in tags and tags[row["item_id"]] != current:
                problems.append(f"{name}: slice tags vary across seeds")
            tags[row["item_id"]] = current
    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        for section, key in (("metrics", "id"), ("slices", "name")):
            current = {(x[key], x.get("metric")) : x for x in spec.get(section, [])}
            for old in base_spec.get(section, []):
                new = current.get((old[key], old.get("metric")))
                if new is None:
                    problems.append(f"ratchet: removed {section} {old[key]}")
                    continue
                if old.get("blocking") and not new.get("blocking"):
                    problems.append(f"ratchet: disabled blocking {old[key]}")
                before = old.get("threshold", {}) if section == "metrics" else old
                after = new.get("threshold", {}) if section == "metrics" else new
                for limit in ("min", "max", "max_increase"):
                    if limit in before and (limit not in after or (after[limit] < before[limit] if limit == "min" else after[limit] > before[limit])):
                        problems.append(f"ratchet: loosened {old[key]}/{limit}")
                if before.get("no_significant_drop") and not after.get("no_significant_drop"):
                    problems.append(f"ratchet: dropped CI requirement {old[key]}")
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        current = per_item(pr, metric, slice_name=name)
        previous = per_item(base, metric, slice_name=name)
        keys = sorted(current.keys() & previous.keys())
        value = sum(current.values()) / len(current) if current else None
        failed = value is None or ("min" in entry and value < entry["min"])
        note = ""
        if entry.get("no_significant_drop"):
            if not keys:
                failed = True
            else:
                if len(keys) == 1:
                    delta = current[keys[0]] - previous[keys[0]]
                    lo = hi = delta
                else:
                    delta, lo, hi = stats.paired_bootstrap(
                        [current[k] for k in keys], [previous[k] for k in keys],
                        n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                        confidence=bs.get("confidence", 0.95))
                note = f"delta {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                failed = failed or hi < 0
        identifier = f"slice:{name}/{metric}"
        if failed and entry.get("blocking"):
            blocked.append(identifier)
        lines.append(f"  {identifier} {value} {note} {'BLOCK' if failed and entry.get('blocking') else 'warn' if failed else 'ok'}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027), confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
