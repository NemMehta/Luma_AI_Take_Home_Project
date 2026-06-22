"""Unit tests for the evidence-sufficiency guard (app.diagnosis.ingest).

The guard is the gate that stops an empty/non-trace bundle from being forced
through the LLM. These tests build EvidenceBundle objects directly — no zip
crafting — and check the guard's status string.

pytest is not a project dependency, so this file also runs standalone:

    python -m app.tests.test_evidence_guard
"""

from __future__ import annotations

from app.diagnosis.ingest import (
    INSUFFICIENT_EVIDENCE,
    SUFFICIENT,
    evidence_sufficiency,
)
from app.diagnosis.schema import (
    Action,
    DomSnapshot,
    EvidenceBundle,
    FailureInfo,
    NetworkRequest,
    TraceMetadata,
)


def _bundle(**overrides) -> EvidenceBundle:
    """An otherwise-empty bundle (actions=[] network=[] failure=None
    dom_snapshot=None), overridable per field — mirrors what the extractor
    produces for a trace with no usable signal."""
    base = dict(source_path="upload.zip", status="passed", metadata=TraceMetadata())
    base.update(overrides)
    return EvidenceBundle(**base)


def test_empty_bundle_is_insufficient():
    # The core case: an empty evidence object -> insufficient_evidence.
    assert evidence_sufficiency(_bundle()) == INSUFFICIENT_EVIDENCE


def test_any_single_field_makes_it_sufficient():
    # AND, not OR: any one present signal is enough — a real trace may lack the
    # other three.
    assert evidence_sufficiency(_bundle(failure=FailureInfo(message="boom"))) == SUFFICIENT
    assert evidence_sufficiency(_bundle(actions=[Action(api_name="Locator.click")])) == SUFFICIENT
    assert evidence_sufficiency(_bundle(network=[NetworkRequest(url="https://x/api")])) == SUFFICIENT
    assert evidence_sufficiency(_bundle(dom_snapshot=DomSnapshot(text="- button \"Go\""))) == SUFFICIENT


def test_dom_snapshot_with_empty_text_is_not_evidence():
    # Field-type nuance: a DomSnapshot can exist with empty/whitespace .text.
    # That must count as "no DOM", not as a present signal.
    assert evidence_sufficiency(_bundle(dom_snapshot=DomSnapshot(text=""))) == INSUFFICIENT_EVIDENCE
    assert evidence_sufficiency(_bundle(dom_snapshot=DomSnapshot(text="   "))) == INSUFFICIENT_EVIDENCE
    assert evidence_sufficiency(_bundle(dom_snapshot=DomSnapshot(text=None))) == INSUFFICIENT_EVIDENCE


def test_empty_lists_are_not_evidence():
    # actions/network default to [] (never None) — explicit empty lists are empty.
    assert evidence_sufficiency(_bundle(actions=[], network=[])) == INSUFFICIENT_EVIDENCE


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {t.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    raise SystemExit(1 if failures else 0)
