"""Shape C — sanitized orchestrator handoff and read-only investigators."""

from __future__ import annotations

import sqlite3

from lab8 import durability
from lab8.db import connect
from lab8.handoff import make_handoff
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes import common
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace

INVESTIGATOR_TOOLS = [
    "lookup_order",
    "lookup_policy",
    "lookup_refund_history",
    "compute_compensation",
]


def _finish(
    conn: sqlite3.Connection,
    *,
    claim_id: str,
    seed: int,
    budget: Budget,
    trace: Trace,
    status: str,
    proposal_amount: int = 0,
    error_reason: str | None = None,
) -> RunResult:
    return common.finish(
        conn,
        shape="orchestrator",
        claim_id=claim_id,
        seed=seed,
        status=status,
        proposal_amount=proposal_amount,
        budget=budget,
        trace=trace,
        error_reason=error_reason,
    )


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    run_id = make_run_id("orchestrator", claim_id, seed)
    trace = Trace(run_id)
    budget = Budget()
    conn = connect(store_path)

    try:
        claim = get_claim_view(conn, claim_id)
        budget.add_tool(tool_cost())
        claim_context = {
            key: claim[key]
            for key in ("order_id", "principal_id")
            if key in claim
        }
        trace.add(
            "claim_view",
            common.safe_dump(
                {
                    "found": bool(claim.get("found")),
                    "has_order": bool(claim_context.get("order_id")),
                }
            ),
        )
        if not claim.get("found"):
            return _finish(
                conn,
                claim_id=claim_id,
                seed=seed,
                budget=budget,
                trace=trace,
                status="failed",
                error_reason="unknown_claim",
            )

        if not claim_context.get("order_id"):
            return _finish(
                conn,
                claim_id=claim_id,
                seed=seed,
                budget=budget,
                trace=trace,
                status="needs_info",
                error_reason="missing_order_id",
            )

        handoff = make_handoff(
            request_id=f"REQ-{claim_id}",
            claim_id=claim_id,
            task="verify_order_and_compute_entitlement",
            facts={},
            allowed_tools=INVESTIGATOR_TOOLS,
        )
        trace.add("handoff", common.safe_dump(handoff))
        investigation = run_readonly_investigators(
            conn,
            budget,
            handoff,
            principal_id=claim_context["principal_id"],
        )
        tools = investigation["tools"]
        order_view = tools.get("lookup_order") or {}
        trace.add(
            "investigation",
            common.safe_dump(
                {
                    "order_visible": bool(order_view.get("visible")),
                    "order_reason": order_view.get("reason"),
                    "policy_count": len((tools.get("lookup_policy") or {}).get("policies") or []),
                    "refund_history_visible": bool(
                        (tools.get("lookup_refund_history") or {}).get("visible")
                    ),
                }
            ),
        )
        if not order_view.get("visible"):
            return _finish(
                conn,
                claim_id=claim_id,
                seed=seed,
                budget=budget,
                trace=trace,
                status="escalated",
                error_reason=order_view.get("reason"),
            )

        history = tools.get("lookup_refund_history") or {}
        if not history.get("visible"):
            return _finish(
                conn,
                claim_id=claim_id,
                seed=seed,
                budget=budget,
                trace=trace,
                status="escalated",
                error_reason=history.get("reason", "refund_history_not_visible"),
            )

        quote = tools.get("compute_compensation")
        if not isinstance(quote, dict):
            return _finish(
                conn,
                claim_id=claim_id,
                seed=seed,
                budget=budget,
                trace=trace,
                status="failed",
                error_reason="missing_quote",
            )
        amount = int(quote["amount_vnd"])
        reason = quote.get("reason")
        trace.add(
            "quote",
            common.safe_dump({"amount_vnd": amount, "reason": reason}),
        )
        if amount <= 0:
            return _finish(
                conn,
                claim_id=claim_id,
                seed=seed,
                budget=budget,
                trace=trace,
                status="denied",
                error_reason=reason,
            )

        trace.add("host_issue_refund", {"amount_vnd": amount})
        trace.write()
        refund = durability.issue_refund(
            conn,
            claim_id,
            amount,
            crash_at=crash_at,
        )
        trace.add(
            "refund_result",
            common.safe_dump(
                {
                    "ok": bool(refund["ok"]),
                    "reason": refund["reason"],
                    "conflict": bool(refund["conflict"]),
                }
            ),
        )
        if not refund["ok"]:
            return _finish(
                conn,
                claim_id=claim_id,
                seed=seed,
                budget=budget,
                trace=trace,
                status="failed" if refund["conflict"] else "denied",
                proposal_amount=amount,
                error_reason=refund["reason"],
            )

        return _finish(
            conn,
            claim_id=claim_id,
            seed=seed,
            budget=budget,
            trace=trace,
            status="resolved",
            proposal_amount=amount,
        )
    finally:
        conn.close()
