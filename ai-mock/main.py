import json
import logging
import os
import time
from typing import Any

import pika


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


RABBITMQ_HOST = os.getenv("SPRING_RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("SPRING_RABBITMQ_PORT", "5672"))
RABBITMQ_USERNAME = os.getenv("SPRING_RABBITMQ_USERNAME", "startmate")
RABBITMQ_PASSWORD = os.getenv("SPRING_RABBITMQ_PASSWORD", "startmate")
REQUEST_QUEUE = os.getenv("STARTMATE_AI_CHAT_REQUEST_QUEUE", "chat.request")
RESPONSE_QUEUE = os.getenv("STARTMATE_AI_CHAT_RESPONSE_QUEUE", "chat.response")
EVENT_DELAY_SECONDS = float(os.getenv("AI_MOCK_EVENT_DELAY_SECONDS", "0.35"))


FEATURE_AGENT_PRESETS: dict[str, list[dict[str, str]]] = {
    "IDEA": [
        {"agentKey": "idea_agent", "label": "Idea Agent", "role": "Idea exploration"},
        {"agentKey": "market_agent", "label": "Market Agent", "role": "Market validation"},
        {"agentKey": "finance_agent", "label": "Finance Agent", "role": "Budget feasibility"},
    ],
    "POLICY": [
        {"agentKey": "policy_agent", "label": "Policy Agent", "role": "Support program discovery"},
        {"agentKey": "fit_agent", "label": "Fit Agent", "role": "Eligibility review"},
    ],
    "OPERATION": [
        {"agentKey": "ops_agent", "label": "Operations Agent", "role": "Operational diagnosis"},
        {"agentKey": "cx_agent", "label": "CX Agent", "role": "Customer feedback review"},
    ],
    "SIMULATION": [
        {"agentKey": "simulation_agent", "label": "Simulation Agent", "role": "Scenario simulation"},
        {"agentKey": "risk_agent", "label": "Risk Agent", "role": "Risk estimation"},
    ],
    "MARKETING": [
        {"agentKey": "marketing_agent", "label": "Marketing Agent", "role": "Campaign planning"},
        {"agentKey": "copy_agent", "label": "Copy Agent", "role": "Message drafting"},
    ],
    "FREE_DISCUSSION": [
        {"agentKey": "intent_agent", "label": "Intent Agent", "role": "Intent routing"},
        {"agentKey": "policy_agent", "label": "Policy Agent", "role": "Support program discovery"},
        {"agentKey": "summary_agent", "label": "Summary Agent", "role": "Answer synthesis"},
    ],
}


def first_non_blank(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def choose_agent(request: dict[str, Any]) -> str:
    payload = request.get("payload") or {}
    candidates = nested(payload, "options", "candidateAgents") or []
    if candidates:
        return str(candidates[0])

    target_feature = (request.get("targetFeature") or "").upper()
    return {
        "IDEA": "IdeaAgent",
        "POLICY": "PolicyAgent",
        "OPERATION": "OperationAgent",
        "SIMULATION": "SimulationAgent",
        "MARKETING": "MarketingAgent",
    }.get(target_feature, "FreeChatAgent")


def selected_agents(request: dict[str, Any]) -> list[dict[str, str]]:
    payload = request.get("payload") or {}
    candidates = nested(payload, "options", "candidateAgents") or []
    if candidates:
        return [
            {
                "agentKey": str(candidate).lower(),
                "label": str(candidate),
                "role": "Specialized analysis",
            }
            for candidate in candidates
        ]

    target_feature = (request.get("targetFeature") or "FREE_DISCUSSION").upper()
    return FEATURE_AGENT_PRESETS.get(target_feature, FEATURE_AGENT_PRESETS["FREE_DISCUSSION"])


def infer_result_spec(request: dict[str, Any]) -> dict[str, Any] | None:
    target_feature = (request.get("targetFeature") or "").upper()
    session_type = (request.get("sessionType") or "").upper()

    if target_feature == "IDEA":
        return {
            "targetFeature": "IDEA",
            "resultType": "BUSINESS_IDEA_RESULT",
            "resultTitle": "Business idea report",
            "routeKey": "idea-report",
        }
    if target_feature == "POLICY":
        return {
            "targetFeature": "POLICY",
            "resultType": "SUPPORT_PROGRAM_MATCH",
            "resultTitle": "Support program report",
            "routeKey": "support-report",
        }
    if target_feature == "OPERATION":
        return {
            "targetFeature": "OPERATION",
            "resultType": "OPERATION_FEEDBACK",
            "resultTitle": "Operation feedback report",
            "routeKey": "operation-feedback",
        }
    if target_feature == "SIMULATION":
        return {
            "targetFeature": "SIMULATION",
            "resultType": "SIMULATION_RESULT",
            "resultTitle": "Simulation report",
            "routeKey": "simulation-report",
        }
    if target_feature == "MARKETING":
        return {
            "targetFeature": "MARKETING",
            "resultType": "MARKETING_COPY_RESULT",
            "resultTitle": "Marketing copy draft",
            "routeKey": "marketing-copy",
        }
    if session_type == "FEATURE_CHAT":
        return {
            "targetFeature": request.get("targetFeature"),
            "resultType": "FEATURE_CHAT_RESULT",
            "resultTitle": "Feature chat result",
            "routeKey": "feature-chat-result",
        }
    return None


def build_summary(request: dict[str, Any]) -> str:
    payload = request.get("payload") or {}
    message = first_non_blank(
        nested(payload, "common", "message"),
        request.get("message"),
        "Question received.",
    )
    target_feature = (request.get("targetFeature") or "").upper()
    reference = payload.get("reference") or {}
    reference_title = reference.get("title")

    if target_feature == "IDEA":
        return f"[MOCK] Building an idea-focused answer for: {message}"
    if target_feature == "POLICY":
        return f"[MOCK] Checking support programs for: {message}"
    if target_feature == "OPERATION":
        return f"[MOCK] Reviewing operations feedback for: {message}"
    if target_feature == "SIMULATION":
        return f"[MOCK] Running a simple scenario review for: {message}"
    if target_feature == "MARKETING":
        return f"[MOCK] Drafting a marketing-style answer for: {message}"
    if reference_title:
        return f"[MOCK] Continuing from '{reference_title}': {message}"
    return f"[MOCK] Free discussion answer: {message}"


def build_response(request: dict[str, Any]) -> dict[str, Any]:
    payload = request.get("payload") or {}
    summary = build_summary(request)
    agent = choose_agent(request)
    result_spec = infer_result_spec(request)
    result_payload = None

    if result_spec is not None:
        result_payload = {
            "targetFeature": result_spec["targetFeature"],
            "resultType": result_spec["resultType"],
            "resultTitle": result_spec["resultTitle"],
            "shouldCreateResult": True,
            "routeKey": result_spec["routeKey"],
            "referenceId": request.get("roomId"),
            "payload": {
                "mock": True,
                "sourceMessage": nested(payload, "common", "message"),
                "reference": payload.get("reference") or {},
            },
        }

    return {
        "requestId": request.get("requestId"),
        "roomId": request.get("roomId"),
        "intent": request.get("intent"),
        "agent": agent,
        "summary": summary,
        "data": {
            "mock": True,
            "agentContractVersion": "mock-v2",
        },
        "nextActions": [
            "Review the feature page result",
            "Continue with a follow-up question",
        ],
        "warnings": [],
        "result": result_payload,
        "version": "v1",
        "messageType": "CHAT_RESPONSE",
        "userId": request.get("userId"),
        "targetFeature": request.get("targetFeature"),
        "status": "COMPLETED",
        "payload": {
            "common": {
                "message": summary,
                "agent": agent,
                "intent": request.get("intent"),
            },
            "result": result_payload,
            "meta": {
                "mock": True,
            },
        },
    }


def publish_json(channel: pika.adapters.blocking_connection.BlockingChannel, message: dict[str, Any]) -> None:
    channel.basic_publish(
        exchange="",
        routing_key=RESPONSE_QUEUE,
        body=json.dumps(message, ensure_ascii=False).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
        ),
    )


def build_agent_event(
    request: dict[str, Any],
    event_type: str,
    sequence: int,
    message: str,
    selected: list[dict[str, str]],
    current_agent: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "requestId": request.get("requestId"),
        "roomId": request.get("roomId"),
        "intent": request.get("intent"),
        "agent": current_agent.get("label") if current_agent else None,
        "summary": message,
        "data": {"mock": True},
        "nextActions": [],
        "warnings": [],
        "result": None,
        "version": "v1",
        "messageType": "AGENT_EVENT",
        "userId": request.get("userId"),
        "targetFeature": request.get("targetFeature"),
        "status": "PROCESSING",
        "payload": {
            "eventType": event_type,
            "orchestrator": "FreeDiscussionOrchestrator",
            "sequence": sequence,
            "message": message,
            "selectedAgents": selected,
            "agent": current_agent,
            "meta": {
                "mock": True,
            },
        },
    }


def emit_agent_progress(channel: pika.adapters.blocking_connection.BlockingChannel, request: dict[str, Any]) -> None:
    selected = selected_agents(request)
    request_message = first_non_blank(
        nested(request.get("payload") or {}, "common", "message"),
        "the user question",
    )

    publish_json(
        channel,
        build_agent_event(
            request,
            "ORCHESTRATION_STARTED",
            1,
            f"Orchestrator is analyzing: {request_message}",
            selected,
        ),
    )
    time.sleep(EVENT_DELAY_SECONDS)

    publish_json(
        channel,
        build_agent_event(
            request,
            "AGENT_SELECTED",
            2,
            f"Selected {len(selected)} agents for this request.",
            selected,
        ),
    )
    time.sleep(EVENT_DELAY_SECONDS)

    sequence = 3
    for index, agent in enumerate(selected[:3], start=1):
        running_agent = {**agent, "status": "running"}
        publish_json(
            channel,
            build_agent_event(
                request,
                "AGENT_STARTED",
                sequence,
                f"{agent['label']} started work.",
                selected,
                running_agent,
            ),
        )
        time.sleep(EVENT_DELAY_SECONDS)
        sequence += 1

        completed_agent = {**agent, "status": "completed"}
        publish_json(
            channel,
            build_agent_event(
                request,
                "AGENT_COMPLETED",
                sequence,
                f"{agent['label']} finished step {index}.",
                selected,
                completed_agent,
            ),
        )
        time.sleep(EVENT_DELAY_SECONDS)
        sequence += 1


def on_message(channel, method, properties, body):
    try:
        request = json.loads(body.decode("utf-8"))
        emit_agent_progress(channel, request)
        response = build_response(request)
        publish_json(channel, response)
        logging.info(
            "Mock response published requestId=%s roomId=%s",
            request.get("requestId"),
            request.get("roomId"),
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:  # noqa: BLE001
        logging.exception("Failed to process mock AI request: %s", exc)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def connect() -> pika.BlockingConnection:
    credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=30,
    )
    return pika.BlockingConnection(parameters)


def serve_forever() -> None:
    while True:
        try:
            connection = connect()
            channel = connection.channel()
            channel.queue_declare(queue=REQUEST_QUEUE, durable=True)
            channel.queue_declare(queue=RESPONSE_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=REQUEST_QUEUE, on_message_callback=on_message)
            logging.info(
                "AI mock connected host=%s requestQueue=%s responseQueue=%s",
                RABBITMQ_HOST,
                REQUEST_QUEUE,
                RESPONSE_QUEUE,
            )
            channel.start_consuming()
        except KeyboardInterrupt:
            logging.info("AI mock stopped")
            return
        except Exception as exc:  # noqa: BLE001
            logging.exception("AI mock connection failed, retrying: %s", exc)
            time.sleep(5)


if __name__ == "__main__":
    serve_forever()