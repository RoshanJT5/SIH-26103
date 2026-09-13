from dataclasses import dataclass
from decimal import Decimal
import logging
import re
from time import perf_counter
from typing import Any, Callable, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models import Dataset, Project, ProjectSnapshot, RiskExplanation, RiskPrediction

logger = logging.getLogger(__name__)

Intent = Literal["rank_projects", "explain_project", "summarize_group", "compare_peers"]


@dataclass(frozen=True)
class ParsedIntent:
    intent: Intent
    project_term: str | None = None
    group_term: str | None = None


@dataclass(frozen=True)
class Retrieval:
    context: str
    answer: str
    sources: list[dict[str, str]]
    dataset_id: int | None
    caveats: list[str]


def parse_intent(question: str) -> ParsedIntent:
    normalized = " ".join(question.lower().split())
    if any(term in normalized for term in ("compare", "compared with", "peer", "similar project")):
        intent: Intent = "compare_peers"
    elif any(term in normalized for term in ("explain", "why", "reason", "risk of", "drivers")):
        intent = "explain_project"
    elif any(term in normalized for term in ("sector", "ministry", "portfolio", "summarize", "summary")) and not any(term in normalized for term in ("highest", "top", "rank")):
        intent = "summarize_group"
    else:
        intent = "rank_projects"

    project_term = None
    quoted = re.search(r'["\']([^"\']{2,120})["\']', question)
    if quoted:
        project_term = quoted.group(1).strip()
    elif intent in {"explain_project", "compare_peers"}:
        match = re.search(r"(?:project|for)\s+([A-Za-z0-9][A-Za-z0-9 ._/-]{1,100})", question, re.IGNORECASE)
        if match:
            project_term = match.group(1).strip(" .?!")

    group_term = None
    group_match = re.search(r"(?:sector|ministry)\s*[:=]?\s*([A-Za-z][A-Za-z0-9 &-]{1,100})", question, re.IGNORECASE)
    if group_match:
        group_term = group_match.group(1).strip(" .?!")
    return ParsedIntent(intent, project_term, group_term)


def _latest_prediction(session: Session, snapshot_id: int) -> RiskPrediction | None:
    return session.scalar(
        select(RiskPrediction).where(RiskPrediction.snapshot_id == snapshot_id).order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc()).limit(1)
    )


def _completed_snapshots(session: Session, dataset_id: int | None) -> list[ProjectSnapshot]:
    conditions = [Dataset.status == "completed"]
    if dataset_id is not None:
        conditions.append(ProjectSnapshot.dataset_id == dataset_id)
    return session.scalars(select(ProjectSnapshot).join(ProjectSnapshot.dataset).where(*conditions).order_by(ProjectSnapshot.id.asc())).all()


def _project_matches(snapshot: ProjectSnapshot, term: str) -> bool:
    value = f"{snapshot.project.project_code} {snapshot.project_name}".lower()
    return term.lower() in value


def _resolve_project(session: Session, term: str | None, dataset_id: int | None) -> tuple[ProjectSnapshot | None, list[ProjectSnapshot]]:
    snapshots = _completed_snapshots(session, dataset_id)
    if not term:
        return None, snapshots
    matches = [snapshot for snapshot in snapshots if _project_matches(snapshot, term)]
    return (matches[0] if len(matches) == 1 else None), matches


def _source(source_type: str, source_id: int | str, label: str) -> dict[str, str]:
    return {"source_type": source_type, "source_id": str(source_id), "label": label}


def _score_text(prediction: RiskPrediction | None) -> str:
    if prediction is None or prediction.overall_score is None:
        return "risk unavailable"
    return f"{prediction.overall_score:.1f}/100 ({prediction.risk_band or 'unavailable'})"


def retrieve_context(session: Session, parsed: ParsedIntent, dataset_id: int | None) -> Retrieval:
    snapshots = _completed_snapshots(session, dataset_id)
    if not snapshots:
        return Retrieval("No completed dataset records were found.", "No completed project data is available for this query.", [], dataset_id, ["Import a completed dataset before asking project questions."])
    sources: list[dict[str, str]] = []
    caveats = ["Results are grounded in stored snapshot data and model outputs."]

    if parsed.intent == "rank_projects":
        scored = [(snapshot, _latest_prediction(session, snapshot.id)) for snapshot in snapshots]
        scored.sort(key=lambda pair: pair[1].overall_score if pair[1] and pair[1].overall_score is not None else Decimal("-1"), reverse=True)
        rows = [(snapshot, prediction) for snapshot, prediction in scored[:10]]
        for snapshot, prediction in rows:
            sources.append(_source("project", snapshot.project_id, snapshot.project.project_code))
        lines = [f"{index}. {snapshot.project.project_code} - {snapshot.project_name}: {_score_text(prediction)}" for index, (snapshot, prediction) in enumerate(rows, 1)]
        answer = "Highest stored risk projects:\n" + "\n".join(lines)
        context = "\n".join(lines)
    elif parsed.intent == "summarize_group":
        term = parsed.group_term
        if term and "ministry" in " ".join([term.lower()]):
            group_field = "ministry"
        else:
            group_field = "sector"
        selected = [snapshot for snapshot in snapshots if term is None or term.lower() in getattr(snapshot, group_field).lower()]
        if not selected:
            return Retrieval("No matching group records were found.", f"I could not find a completed {group_field} matching '{term}'.", [], dataset_id, caveats)
        predictions = [_latest_prediction(session, snapshot.id) for snapshot in selected]
        scores = [prediction.overall_score for prediction in predictions if prediction and prediction.overall_score is not None]
        average = sum(scores) / len(scores) if scores else None
        high = sum(prediction is not None and prediction.risk_band in {"high", "critical"} for prediction in predictions)
        label = term or "the selected portfolio"
        answer = f"{label}: {len(selected)} projects, {high} high or critical stored risks, and an average overall score of {average:.1f}/100." if average is not None else f"{label}: {len(selected)} projects were found, but stored overall risk scores are unavailable."
        context = answer
        sources.extend(_source("snapshot", snapshot.id, snapshot.project.project_code) for snapshot in selected[:10])
    else:
        subject, matches = _resolve_project(session, parsed.project_term, dataset_id)
        if subject is None:
            if not matches:
                message = f"I could not find a unique project matching '{parsed.project_term}'." if parsed.project_term else "Name a project code or project name so I can identify the subject."
            else:
                message = f"I found {len(matches)} projects matching '{parsed.project_term}'. Please use the project code or a more specific name."
            return Retrieval("Project resolution failed.", message, [], dataset_id, caveats)
        prediction = _latest_prediction(session, subject.id)
        sources.append(_source("project", subject.project_id, subject.project.project_code))
        if parsed.intent == "explain_project":
            explanations = session.scalars(select(RiskExplanation).where(RiskExplanation.prediction_id == prediction.id).order_by(RiskExplanation.shap_contribution.desc()).limit(5)).all() if prediction else []
            drivers = ", ".join(f"{item.feature_name} ({item.shap_contribution:+.3f})" for item in explanations) or "no stored SHAP drivers"
            answer = f"{subject.project.project_code} has {_score_text(prediction)}. Stored model drivers: {drivers}."
            context = answer
            if prediction:
                sources.append(_source("prediction", prediction.id, f"risk prediction for {subject.project.project_code}"))
            caveats.append("SHAP contributions describe the component model output, not a percentage-point contribution to the blended score.")
        else:
            peers = [peer for peer in snapshots if peer.id != subject.id and peer.sector == subject.sector and peer.ministry == subject.ministry]
            peer_predictions = [_latest_prediction(session, peer.id) for peer in peers]
            peer_scores = [prediction.overall_score for prediction in peer_predictions if prediction and prediction.overall_score is not None]
            answer = f"{subject.project.project_code} has {_score_text(prediction)}. Its comparable cohort contains {len(peers)} other projects."
            if peer_scores and prediction and prediction.overall_score is not None:
                answer += f" The peer average stored score is {sum(peer_scores) / len(peer_scores):.1f}/100."
            else:
                caveats.append("A comparable peer score is unavailable because the cohort is sparse or unscored.")
            context = answer
            sources.extend(_source("project", peer.project_id, peer.project.project_code) for peer in peers[:10])

    return Retrieval(context, answer, sources, dataset_id or snapshots[0].dataset_id, caveats)


def _groq_answer(question: str, retrieval: Retrieval) -> str:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_groq import ChatGroq

    settings = get_settings()
    model = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0, timeout=10, max_retries=1)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer only from the supplied context. Do not invent project facts, scores, actions, or sources. Keep the answer concise and distinguish observations from estimates."),
        ("human", "Question: {question}\nContext: {context}"),
    ])
    response = (prompt | model).invoke({"question": question, "context": retrieval.context})
    return str(response.content)


def answer_question(session: Session, question: str, dataset_id: int | None, provider: Callable[[str, Retrieval], str] | None = None) -> tuple[Retrieval, str, str, str | None]:
    started_at = perf_counter()
    parsed = parse_intent(question)
    retrieval = retrieve_context(session, parsed, dataset_id)
    settings = get_settings()

    def finish(result: Retrieval, answer: str, status: str, model: str | None) -> tuple[Retrieval, str, str, str | None]:
        logger.info(
            "assistant_request intent=%s provider_status=%s model=%s dataset_id=%s latency_ms=%.1f",
            parsed.intent,
            status,
            model or "none",
            result.dataset_id or "none",
            (perf_counter() - started_at) * 1000,
        )
        return result, answer, status, model

    if provider is not None:
        return finish(retrieval, provider(question, retrieval), "groq", settings.groq_model)
    if not settings.assistant_enabled:
        return finish(retrieval, retrieval.answer, "disabled", None)
    try:
        return finish(retrieval, _groq_answer(question, retrieval), "groq", settings.groq_model)
    except Exception:
        retrieval = Retrieval(retrieval.context, retrieval.answer, retrieval.sources, retrieval.dataset_id, retrieval.caveats + ["Groq was unavailable; this response is the deterministic retrieved summary."])
        return finish(retrieval, retrieval.answer, "fallback", settings.groq_model)