from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.assistant import AssistantQueryRequest, AssistantQueryResponse, AssistantSource
from ..services.assistant import answer_question, parse_intent

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/query", response_model=AssistantQueryResponse)
def assistant_query(request: AssistantQueryRequest, db: Session = Depends(get_db)) -> AssistantQueryResponse:
    retrieval, answer, provider_status, model = answer_question(db, request.question, request.dataset_id)
    return AssistantQueryResponse(
        answer=answer,
        intent=parse_intent(request.question).intent,
        sources=[AssistantSource.model_validate(source) for source in retrieval.sources],
        dataset_id=retrieval.dataset_id,
        model=model,
        provider_status=provider_status,
        caveats=retrieval.caveats,
    )