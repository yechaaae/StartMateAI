from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

try:
    import aio_pika
except ModuleNotFoundError:  # pragma: no cover - exercised only when worker deps are missing locally.
    aio_pika = None

from app.core.config import get_settings
from app.schemas import ChatRequest, StartupProfile


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def request_from_envelope(envelope: dict[str, Any]) -> ChatRequest:
    payload = envelope.get("payload") or {}
    common = payload.get("common") or {}
    reference = payload.get("reference") or {}
    feature_context = payload.get("featureContext") or {}
    conversation = payload.get("conversation") or {}
    result_context = payload.get("resultContext") or {}
    request_metadata = _request_metadata(envelope)

    message = str(common.get("message") or "")
    context = {
        "reference": reference,
        "featureContext": feature_context,
        "conversation": conversation,
        "resultContext": result_context,
        "requestMetadata": request_metadata,
        "rabbitmq": {
            "requestId": envelope.get("requestId"),
            "roomId": envelope.get("roomId"),
            "messageId": envelope.get("messageId"),
            "targetFeature": envelope.get("targetFeature"),
        },
    }
    context.update(feature_context if isinstance(feature_context, dict) else {})

    return ChatRequest(
        message=message,
        profile=_profile_from_payload(payload.get("profile") or {}),
        intent=_intent_from_envelope(envelope, message, reference),
        context=context,
    )


def response_to_envelope(request_envelope: dict[str, Any], response) -> dict[str, Any]:
    request_metadata = _request_metadata(request_envelope)
    result = response.result
    return {
        "requestId": request_envelope.get("requestId"),
        "roomId": request_envelope.get("roomId"),
        "type": "final",
        "intent": response.intent,
        "agent": response.agent,
        "summary": response.summary,
        "data": response.data,
        "nextActions": response.next_actions,
        "warnings": response.warnings,
        "result": result,
        "version": "v1",
        "messageType": "CHAT_RESPONSE",
        "userId": request_envelope.get("userId"),
        "targetFeature": request_envelope.get("targetFeature"),
        "status": "COMPLETED",
        "payload": {
            "common": {
                "message": response.summary,
                "intent": response.intent,
                "agent": response.agent,
                "type": "final",
            },
            "type": "final",
            "summary": response.summary,
            "intent": response.intent,
            "agent": response.agent,
            "data": response.data,
            "sources": [source.model_dump() for source in response.sources],
            "result": result,
            "requestMetadata": request_metadata,
        },
    }


def _request_metadata(request_envelope: dict[str, Any]) -> dict[str, Any]:
    payload = request_envelope.get("payload") or {}
    common = payload.get("common") or {}
    metadata = common.get("metadata")
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str) and metadata.strip():
        try:
            parsed = json.loads(metadata)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def progress_event_to_envelope(
    request_envelope: dict[str, Any],
    event: dict[str, Any],
    sequence: int,
) -> dict[str, Any]:
    view_type = str(event.get("type") or event.get("viewType") or _event_view_type(event))
    payload = {
        "eventType": event.get("eventType"),
        "type": view_type,
        "viewType": view_type,
        "orchestrator": event.get("orchestrator") or "OrchestratorAgent",
        "sequence": sequence,
        "message": event.get("message"),
        "agent": event.get("agent"),
        "selectedAgents": event.get("selectedAgents", []),
        "detail": event.get("detail") or {},
    }
    status = str(event.get("status") or "PROCESSING")
    agent_payload = payload.get("agent") if isinstance(payload.get("agent"), dict) else {}
    agent_name = str(agent_payload.get("agentKey") or "OrchestratorAgent")
    message = str(payload.get("message") or "")

    return {
        "requestId": request_envelope.get("requestId"),
        "roomId": request_envelope.get("roomId"),
        "type": view_type,
        "intent": request_envelope.get("intent") or "auto",
        "agent": agent_name,
        "summary": message,
        "data": {},
        "nextActions": [],
        "warnings": [],
        "result": None,
        "version": "v1",
        "messageType": "AGENT_EVENT",
        "userId": request_envelope.get("userId"),
        "targetFeature": request_envelope.get("targetFeature"),
        "status": status,
        "payload": payload,
    }


def _event_view_type(event: dict[str, Any]) -> str:
    event_type = str(event.get("eventType") or "")
    agent = event.get("agent") if isinstance(event.get("agent"), dict) else {}
    agent_status = str(agent.get("status") or "")
    if event_type in {"orchestrator.started", "agents.selected", "agent.started", "orchestrator.completed"}:
        return "status"
    if event_type == "agent.completed":
        return "result"
    if event_type == "agent.argument":
        return "argument"
    if event_type == "agent.challenge":
        return "challenge"
    if event_type == "agent.revision":
        return "revision"
    if event_type == "orchestrator.consensus":
        return "consensus"
    if event_type == "orchestrator.synthesizing":
        return "discussion"
    if event_type == "agent.failed" or agent_status == "failed":
        return "status"
    return "discussion"


def failed_response_envelope(request_envelope: dict[str, Any], error: Exception) -> dict[str, Any]:
    message = f"AI worker failed: {error.__class__.__name__}"
    return {
        "requestId": request_envelope.get("requestId"),
        "roomId": request_envelope.get("roomId"),
        "intent": request_envelope.get("intent") or "auto",
        "agent": "AiWorker",
        "summary": message,
        "data": {},
        "nextActions": [],
        "warnings": [str(error)[:500]],
        "result": None,
        "version": "v1",
        "messageType": "CHAT_RESPONSE",
        "userId": request_envelope.get("userId"),
        "targetFeature": request_envelope.get("targetFeature"),
        "status": "FAILED",
        "payload": {
            "message": message,
            "error": {"message": str(error)[:500]},
        },
    }


async def handle_message(message, response_exchange, response_queue_name: str) -> None:
    async with message.process(requeue=False):
        request_envelope: dict[str, Any] = {}
        try:
            request_envelope = json.loads(message.body.decode("utf-8"))
            chat_request = request_from_envelope(request_envelope)
            from app.api.routes import orchestrator

            sequence_lock = asyncio.Lock()
            sequence = 0

            async def publish_progress(event: dict[str, Any]) -> None:
                nonlocal sequence
                async with sequence_lock:
                    sequence += 1
                    current_sequence = sequence
                outgoing_progress = progress_event_to_envelope(request_envelope, event, current_sequence)
                await response_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(outgoing_progress, ensure_ascii=False).encode("utf-8"),
                        content_type="application/json",
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=response_queue_name,
                )

            await publish_progress(
                {
                    "eventType": "orchestrator.started",
                    "orchestrator": "OrchestratorAgent",
                    "status": "PROCESSING",
                    "message": "질문을 분석해서 필요한 Agent를 고르는 중입니다.",
                    "agent": {
                        "agentKey": "OrchestratorAgent",
                        "label": "Orchestrator",
                        "role": "Agent 의견 조율",
                        "status": "running",
                    },
                    "selectedAgents": [],
                }
            )
            response = await orchestrator.run(chat_request, progress_callback=publish_progress)
            outgoing = response_to_envelope(request_envelope, response)
        except Exception as error:  # noqa: BLE001
            logging.exception("Failed to process AI request")
            outgoing = failed_response_envelope(request_envelope, error)

        await response_exchange.publish(
            aio_pika.Message(
                body=json.dumps(outgoing, ensure_ascii=False).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=response_queue_name,
        )


async def serve() -> None:
    if aio_pika is None:
        raise RuntimeError("aio-pika is required to run the RabbitMQ worker. Install ai/requirements.txt first.")

    settings = get_settings()
    connection = await aio_pika.connect_robust(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        login=settings.rabbitmq_username,
        password=settings.rabbitmq_password,
    )
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        request_queue = await channel.declare_queue(settings.ai_chat_request_queue, durable=True)
        await channel.declare_queue(settings.ai_chat_response_queue, durable=True)

        logging.info(
            "AI worker connected host=%s requestQueue=%s responseQueue=%s",
            settings.rabbitmq_host,
            settings.ai_chat_request_queue,
            settings.ai_chat_response_queue,
        )
        await request_queue.consume(
            lambda message: handle_message(message, channel.default_exchange, settings.ai_chat_response_queue)
        )
        await asyncio.Future()


def _profile_from_payload(profile: dict[str, Any]) -> StartupProfile:
    return StartupProfile(
        major=profile.get("major"),
        experiences=list(profile.get("experiences") or []),
        region=profile.get("region"),
        budget_krw=profile.get("budgetKrw") or profile.get("budget_krw"),
        interests=list(profile.get("interests") or []),
        preferred_channels=list(profile.get("preferredChannels") or profile.get("preferred_channels") or []),
        startup_stage=profile.get("startupStage") or profile.get("startup_stage") or "예비창업",
        risk_tolerance=profile.get("riskTolerance") or profile.get("risk_tolerance") or "medium",
        memo=profile.get("memo"),
    )


def _intent_from_envelope(envelope: dict[str, Any], message: str, reference: dict[str, Any]) -> str:
    external_data = reference.get("externalData") if isinstance(reference, dict) else {}
    text = message.lower()
    requested_intent = str(envelope.get("intent") or "auto").strip().lower()
    feature_intent = _intent_from_target_feature(envelope.get("targetFeature"))

    if requested_intent not in {"", "auto"}:
        return requested_intent
    if feature_intent:
        return feature_intent
    if isinstance(external_data, dict) and external_data.get("commercialArea"):
        if external_data.get("supportPrograms") or any(keyword in text for keyword in ["지원사업", "공고", "정책"]):
            return "auto"
        return "commercial_area"
    if any(keyword in text for keyword in ["상권", "입지", "경쟁점", "주변 점포", "주변 가게", "연남동", "마포구", "구미", "인동동"]):
        return "commercial_area"
    return "auto"


def _intent_from_target_feature(target_feature: Any) -> str:
    feature = str(target_feature or "").strip().upper()
    return {
        "ITEM": "idea",
        "SIMULATOR": "simulation",
        "SUPPORT": "policy",
        "PLAN": "plan",
        "OPERATION": "operation",
        "SNS": "marketing",
        "COMMERCIAL_AREA": "commercial_area",
    }.get(feature, "")


if __name__ == "__main__":
    asyncio.run(serve())
