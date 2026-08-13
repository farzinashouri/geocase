"""Set ``named_trap`` automatically with an LLM judge (Plan 16 Phase 0).

Sends each probe reply, plus the trap's canonical description, to a judge model
and records its verdict. This replaces human review (U7) with a model's
judgement.

**What this costs.** A judge is itself fallible in both directions: it misses
paraphrases and it flags replies that mention a trap's vocabulary while
discussing something else. Those errors are indistinguishable, in the output
file, from correct verdicts — so any contamination claim drawn from
``judge_model``-set flags inherits an unmeasured error rate. Provenance is
therefore recorded per probe: ``named_trap_source`` is "judge" or "human", and
``judge_model``/``judge_rationale`` say who decided and why. Do not publish a
contamination table without stating which flags a human confirmed.

To bound that error, run --measure-agreement over replies a human has already
reviewed: it reports how often the judge matches the human on the same data,
which is the only honest basis for trusting the rest.

    python scripts/judge_probes.py --config configs/models-free.yaml
    python scripts/judge_probes.py --config configs/models-free.yaml --measure-agreement
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import yaml

from geocase.benchmark.registry import get_task

# The canonical statement of each trap, in the judge's terms. Deliberately
# describes the *idea*, not its vocabulary, so a paraphrase counts.
TRAP_DESCRIPTIONS = {
    "antimeridian": (
        "that geometries crossing the 180th meridian / date line break — the "
        "jump between +180 and -180 is treated as an enormous distance, so the "
        "geometry must be split or handled specially"
    ),
    "axis-order": (
        "that latitude/longitude order can be swapped relative to x/y order, so "
        "coordinates end up transposed"
    ),
    "units-degrees": (
        "that degrees are not a linear distance unit — a degree of longitude "
        "shrinks with latitude, so treating degrees as metres is wrong"
    ),
    "crs-conformance": (
        "that the output must conform to a specific CRS convention, e.g. "
        "reprojecting to WGS84 rather than emitting a non-conforming CRS member"
    ),
    "nodata": (
        "that a raster's nodata / sentinel values (e.g. -9999) must be excluded "
        "rather than treated as real measurements"
    ),
    "topology-repair": (
        "that naive repairs such as buffer(0) can silently delete part of an "
        "invalid geometry rather than fixing it"
    ),
    "canonical-equality": (
        "that geometrically identical shapes can have different coordinate "
        "sequences (rotated start vertex, reversed winding), so byte or WKB "
        "comparison misses duplicates"
    ),
    "predicate-semantics": (
        "that boundary cases differ between spatial predicates — e.g. a point "
        "exactly on an edge, or a centroid falling outside a concave shape"
    ),
    "ordering": "that output order must correspond to input order, element by element",
    "y-flip": (
        "that tile row numbering is inverted between schemes (TMS vs XYZ), so "
        "the y axis must be flipped"
    ),
    "zone-exceptions": (
        "that UTM zone numbering has irregular exceptions (Svalbard, southwest "
        "Norway) that a simple longitude formula gets wrong"
    ),
    "collinearity": (
        "that collinear or overlapping segments are a special case returning a "
        "shared segment, not a single point or nothing"
    ),
    "discretization": (
        "that sampling or densification granularity matters — straight lines in "
        "one projection are not straight in another, or grid cells do not align"
    ),
    "normalization": (
        "that Unicode text has multiple encodings of the same characters "
        "(composed vs decomposed forms), so normalization is needed before "
        "comparison"
    ),
    "null-propagation": (
        "that missing/None values must be excluded from aggregation rather than "
        "coerced to zero, and that an all-missing group is not zero"
    ),
    "rounding-residue": (
        "that independently rounding shares loses or invents units, so the parts "
        "no longer sum to the original total"
    ),
    "dst-transition": (
        "that daylight-saving transitions make some local days 23 or 25 hours "
        "long, so naive datetime subtraction is wrong"
    ),
    "cancellation": (
        "that the naive one-pass variance formula suffers catastrophic "
        "cancellation for values with a large offset, needing a two-pass or "
        "Welford approach"
    ),
    "quoting": (
        "that delimiters inside quoted fields must not split the record, so "
        "naive splitting on the delimiter is wrong"
    ),
}

JUDGE_TEMPLATE = """You are grading whether a reply raises a specific issue.

THE ISSUE: {description}

THE REPLY:
---
{reply}
---

Did the reply raise THE ISSUE above, in any wording? It counts if the reply
describes the same underlying problem, even using entirely different
terminology. It does not count if the reply merely uses similar vocabulary
while discussing a different problem.

Answer with a JSON object and nothing else:
{{"named": true or false, "why": "<one short sentence of evidence>"}}
"""


def _verdict(client, model_id: str, description: str, reply: str):
    prompt = JUDGE_TEMPLATE.format(description=description, reply=reply)
    out = client.chat(model_id, [{"role": "user", "content": prompt}]).content
    text = out.strip()
    if "```" in text:  # some models fence their JSON regardless
        text = text.split("```")[1].removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError(f"no JSON object in judge reply: {out[:200]!r}")
    data = json.loads(text[start : end + 1])
    return bool(data["named"]), str(data.get("why", ""))[:400]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="judge_probes")
    ap.add_argument("--dir", type=Path, default=Path("results/probes"))
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument(
        "--judge-model",
        default=None,
        help="model id to judge with (default: first bare model in --config)",
    )
    ap.add_argument(
        "--measure-agreement",
        action="store_true",
        help="judge only human-reviewed probes and report how often it agrees",
    )
    ap.add_argument(
        "--redo", action="store_true", help="re-judge probes already judged"
    )
    args = ap.parse_args(argv)

    judge = args.judge_model
    if judge is None:
        if args.config is None:
            print("need --judge-model or --config", file=sys.stderr)
            return 2
        models = [
            m
            for m in yaml.safe_load(args.config.read_text()).get("models", [])
            if "bare" in m.get("tracks", [])
        ]
        if not models:
            print(f"no bare-track models in {args.config}", file=sys.stderr)
            return 2
        judge = models[0]["id"]

    files = sorted(glob.glob(str(args.dir / "*.json")))
    if not files:
        print(f"no probe files in {args.dir}", file=sys.stderr)
        return 2

    from geocase.benchmark.runner.openrouter import OpenRouterClient

    client = OpenRouterClient()
    client.max_total_seconds = 20.0
    print(f"judge: {judge}\n")

    agree = disagree = judged = 0
    for path in files:
        data = json.loads(Path(path).read_text())
        changed = False
        for probe in data["probes"]:
            human = (
                probe["named_trap"]
                if probe.get("named_trap_source", "human") == "human"
                else None
            )
            if args.measure_agreement and human is None:
                continue
            if (
                not args.measure_agreement
                and not args.redo
                and probe["named_trap"] is not None
            ):
                continue

            trap = get_task(probe["task"]).trap_category
            description = TRAP_DESCRIPTIONS.get(trap)
            if description is None:
                print(f"  no description for trap {trap!r} — skipping", file=sys.stderr)
                continue
            try:
                named, why = _verdict(client, judge, description, probe["reply"])
            except Exception as exc:  # noqa: BLE001 - one bad judge call is not fatal
                print(
                    f"  {data['model']['id']} {probe['task']}: JUDGE FAILED ({exc})",
                    file=sys.stderr,
                )
                continue

            judged += 1
            if args.measure_agreement:
                match = named == human
                agree += match
                disagree += not match
                mark = "agree " if match else "DIFFER"
                print(
                    f"  {mark} {probe['task']:<18} human={human!s:<5} "
                    f"judge={named!s:<5} {why[:70]}"
                )
                continue

            probe["named_trap"] = named
            probe["named_trap_source"] = "judge"
            probe["judge_model"] = judge
            probe["judge_rationale"] = why
            changed = True
            print(
                f"  {data['model']['id']} {probe['task']}: named={named} — {why[:70]}"
            )
        if changed:
            Path(path).write_text(json.dumps(data, indent=2))

    if args.measure_agreement:
        total = agree + disagree
        if not total:
            print(
                "\nNo human-reviewed probes to compare against. Review a sample by "
                "hand first (scripts/review_probes.py), then re-run this.",
                file=sys.stderr,
            )
            return 2
        print(
            f"\nagreement with human review: {agree}/{total} ({agree / total:.0%})"
            f"\nThis is the error rate every judge-set flag carries."
        )
    else:
        print(f"\n{judged} probe(s) judged automatically.")
        print(
            "Flags are marked named_trap_source=judge. Spot-check a sample with "
            "--measure-agreement before publishing any contamination claim."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
