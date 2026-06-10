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
    "ITEM": [
        {"agentKey": "idea_agent", "label": "Idea Agent", "role": "Idea recommendation"},
        {"agentKey": "profile_agent", "label": "Profile Agent", "role": "Founder fit review"},
        {"agentKey": "finance_agent", "label": "Finance Agent", "role": "Early feasibility check"},
    ],
    "SIMULATOR": [
        {"agentKey": "simulation_agent", "label": "Simulation Agent", "role": "Scenario review"},
        {"agentKey": "risk_agent", "label": "Risk Agent", "role": "Risk estimate"},
    ],
    "SUPPORT": [
        {"agentKey": "policy_agent", "label": "Policy Agent", "role": "Support program search"},
        {"agentKey": "fit_agent", "label": "Fit Agent", "role": "Eligibility review"},
    ],
    "PLAN": [
        {"agentKey": "plan_agent", "label": "Plan Agent", "role": "Business plan drafting"},
        {"agentKey": "policy_agent", "label": "Policy Agent", "role": "Support alignment review"},
        {"agentKey": "idea_agent", "label": "Idea Agent", "role": "Value proposition refinement"},
    ],
    "OPERATION": [
        {"agentKey": "ops_agent", "label": "Operations Agent", "role": "Operational diagnosis"},
        {"agentKey": "finance_agent", "label": "Finance Agent", "role": "Unit economics review"},
        {"agentKey": "cx_agent", "label": "CX Agent", "role": "Customer feedback review"},
    ],
    "SNS": [
        {"agentKey": "marketing_agent", "label": "Marketing Agent", "role": "Campaign planning"},
        {"agentKey": "copy_agent", "label": "Copy Agent", "role": "Message drafting"},
        {"agentKey": "profile_agent", "label": "Profile Agent", "role": "Audience fit review"},
    ],
    "FREE_DISCUSSION": [
        {"agentKey": "intent_agent", "label": "Intent Agent", "role": "Intent routing"},
        {"agentKey": "policy_agent", "label": "Policy Agent", "role": "Support discovery"},
        {"agentKey": "summary_agent", "label": "Summary Agent", "role": "Answer synthesis"},
    ],
}


RESULT_PRESETS: dict[str, dict[str, str]] = {
    "ITEM": {
        "resultType": "BUSINESS_IDEA_RESULT",
        "resultTitle": "AI idea follow-up report",
        "routeKey": "idea-report",
    },
    "SIMULATOR": {
        "resultType": "SIMULATION_RESULT",
        "resultTitle": "Simulation insight report",
        "routeKey": "simulation-report",
    },
    "SUPPORT": {
        "resultType": "SUPPORT_PROGRAM_MATCH",
        "resultTitle": "Support program follow-up report",
        "routeKey": "support-report",
    },
    "PLAN": {
        "resultType": "PLAN_REPORT",
        "resultTitle": "Business plan refinement memo",
        "routeKey": "plan-report",
    },
    "OPERATION": {
        "resultType": "OPERATION_FEEDBACK",
        "resultTitle": "Operation follow-up report",
        "routeKey": "operation-feedback",
    },
    "SNS": {
        "resultType": "SNS_REPORT",
        "resultTitle": "SNS campaign refinement draft",
        "routeKey": "sns-report",
    },
}


def first_non_blank(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def normalize_feature(value: Any) -> str:
    if value is None:
        return "FREE_DISCUSSION"
    text = str(value).strip().upper()
    return text or "FREE_DISCUSSION"


def nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def feature_key(request: dict[str, Any]) -> str:
    payload = request.get("payload") or {}
    return normalize_feature(
        first_non_blank(
            nested(payload, "featureContext", "featureKey"),
            nested(payload, "conversation", "targetFeature"),
            request.get("targetFeature"),
        )
    )


def request_message(request: dict[str, Any]) -> str:
    payload = request.get("payload") or {}
    return first_non_blank(
        nested(payload, "common", "message"),
        request.get("message"),
        "Question received.",
    ) or "Question received."


def feature_context(request: dict[str, Any]) -> dict[str, Any]:
    payload = request.get("payload") or {}
    return as_dict(payload.get("featureContext"))


def result_context(request: dict[str, Any]) -> dict[str, Any]:
    payload = request.get("payload") or {}
    return as_dict(payload.get("resultContext"))


def profile_context(request: dict[str, Any]) -> dict[str, Any]:
    payload = request.get("payload") or {}
    return as_dict(payload.get("profile"))


def choose_agent(request: dict[str, Any]) -> str:
    payload = request.get("payload") or {}
    candidates = as_list(nested(payload, "options", "candidateAgents"))
    if candidates:
        return str(candidates[0])

    return {
        "ITEM": "IdeaAgent",
        "SIMULATOR": "SimulationAgent",
        "SUPPORT": "PolicyAgent",
        "PLAN": "PlanAgent",
        "OPERATION": "OperationAgent",
        "SNS": "MarketingAgent",
    }.get(feature_key(request), "FreeChatAgent")


def selected_agents(request: dict[str, Any]) -> list[dict[str, str]]:
    payload = request.get("payload") or {}
    candidates = as_list(nested(payload, "options", "candidateAgents"))
    if candidates:
        return [
            {
                "agentKey": str(candidate).lower(),
                "label": str(candidate),
                "role": "Specialized analysis",
            }
            for candidate in candidates
        ]

    return FEATURE_AGENT_PRESETS.get(feature_key(request), FEATURE_AGENT_PRESETS["FREE_DISCUSSION"])


def summarize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "major": profile.get("major"),
        "region": profile.get("region"),
        "budgetKrw": profile.get("budget_krw"),
        "interests": as_list(profile.get("interests"))[:3],
        "startupStage": profile.get("startup_stage"),
    }


def infer_result_spec(request: dict[str, Any]) -> dict[str, Any] | None:
    feature = feature_key(request)
    preset = RESULT_PRESETS.get(feature)
    if preset is None:
        return None

    return {
        "targetFeature": feature,
        "resultType": preset["resultType"],
        "resultTitle": preset["resultTitle"],
        "routeKey": preset["routeKey"],
    }


def support_details(context: dict[str, Any]) -> dict[str, Any]:
    support_context = as_dict(context.get("supportContext"))
    selection = as_dict(context.get("selection"))
    selected_program = as_dict(selection.get("selectedSupportProgram"))
    return {
        "supportSearchMode": support_context.get("supportSearchMode"),
        "userGoal": support_context.get("userGoal"),
        "selectedSupportProgram": selected_program,
    }


def plan_details(context: dict[str, Any]) -> dict[str, Any]:
    plan_context = as_dict(context.get("planContext"))
    selection = as_dict(context.get("selection"))
    focused_section = as_dict(plan_context.get("focusedSection"))
    return {
        "planGoal": plan_context.get("planGoal"),
        "focusedSection": focused_section,
        "selectedSupportProgram": as_dict(selection.get("selectedSupportProgram")),
    }


def operation_details(context: dict[str, Any]) -> dict[str, Any]:
    business_context = as_dict(context.get("businessContext"))
    operation_context = as_dict(context.get("operationContext"))
    operation_input = as_dict(operation_context.get("input"))
    operation_report = as_dict(operation_context.get("report"))
    return {
        "businessContext": business_context,
        "operationInput": operation_input,
        "operationReport": operation_report,
        "contextPriority": as_list(context.get("contextPriority")),
    }


def sns_details(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "campaignContext": as_dict(context.get("campaignContext")),
        "campaignDraft": as_dict(context.get("campaignDraft")),
        "contextPriority": as_list(context.get("contextPriority")),
    }


def item_details(context: dict[str, Any], result_ctx: dict[str, Any]) -> dict[str, Any]:
    selection = as_dict(context.get("selection"))
    current_result = as_dict(result_ctx.get("currentResult"))
    return {
        "selectedIdea": as_dict(selection.get("selectedIdea")) or as_dict(current_result.get("selectedIdea")),
        "currentResultType": context.get("currentResultType") or result_ctx.get("currentResultType"),
    }


def simulator_details(result_ctx: dict[str, Any]) -> dict[str, Any]:
    current_result = as_dict(result_ctx.get("currentResult"))
    return {
        "simulationInput": as_dict(current_result.get("simulationInput")),
        "ideaContext": as_dict(current_result.get("ideaContext")),
        "risks": as_list(current_result.get("risks")),
    }


def build_summary(request: dict[str, Any]) -> str:
    feature = feature_key(request)
    context = feature_context(request)
    result_ctx = result_context(request)
    message = request_message(request)

    if feature == "ITEM":
        selected_idea = as_dict(item_details(context, result_ctx).get("selectedIdea"))
        idea_title = first_non_blank(selected_idea.get("title"), "selected idea")
        return f"[MOCK] Refining the startup idea around {idea_title}: {message}"

    if feature == "SIMULATOR":
        details = simulator_details(result_ctx)
        simulation_input = as_dict(details.get("simulationInput"))
        item_name = first_non_blank(simulation_input.get("item"), "current simulation setup")
        return f"[MOCK] Reviewing the simulation for {item_name}: {message}"

    if feature == "SUPPORT":
        details = support_details(context)
        program = as_dict(details.get("selectedSupportProgram"))
        program_title = first_non_blank(program.get("title"), "support program candidates")
        mode = first_non_blank(details.get("supportSearchMode"), "PROFILE_IDEA")
        return f"[MOCK] Checking {program_title} with search mode {mode}: {message}"

    if feature == "PLAN":
        details = plan_details(context)
        section = as_dict(details.get("focusedSection"))
        section_title = first_non_blank(section.get("title"), "plan section")
        goal = first_non_blank(details.get("planGoal"), "ALIGN_SUPPORT")
        return f"[MOCK] Revising the {section_title} section for goal {goal}: {message}"

    if feature == "OPERATION":
        details = operation_details(context)
        operation_input = as_dict(details.get("operationInput"))
        operation_report = as_dict(details.get("operationReport"))
        selected_suggestion = as_dict(operation_report.get("selectedSuggestion"))
        period = first_non_blank(operation_input.get("period"), "recent period")
        suggestion = first_non_blank(selected_suggestion.get("title"), "key operation issue")
        return f"[MOCK] Reviewing {period} operations around {suggestion}: {message}"

    if feature == "SNS":
        details = sns_details(context)
        campaign_draft = as_dict(details.get("campaignDraft"))
        topic = first_non_blank(campaign_draft.get("topic"), "campaign topic")
        channel = first_non_blank(campaign_draft.get("channel"), "default channel")
        return f"[MOCK] Refining the {channel} campaign for {topic}: {message}"

    reference = as_dict((request.get("payload") or {}).get("reference"))
    reference_title = reference.get("title")
    if reference_title:
        return f"[MOCK] Continuing from '{reference_title}': {message}"
    return f"[MOCK] Free discussion answer: {message}"


def build_feature_payload(request: dict[str, Any]) -> dict[str, Any]:
    feature = feature_key(request)
    context = feature_context(request)
    result_ctx = result_context(request)
    profile = profile_context(request)

    if feature == "ITEM":
        return {
            "selectedIdea": item_details(context, result_ctx).get("selectedIdea"),
            "profileSummary": summarize_profile(profile),
        }
    if feature == "SIMULATOR":
        return {
            "simulationInput": simulator_details(result_ctx).get("simulationInput"),
            "ideaContext": simulator_details(result_ctx).get("ideaContext"),
        }
    if feature == "SUPPORT":
        return {
            **support_details(context),
            "profileSummary": summarize_profile(profile),
        }
    if feature == "PLAN":
        return {
            **plan_details(context),
            "profileSummary": summarize_profile(profile),
        }
    if feature == "OPERATION":
        return {
            **operation_details(context),
            "profileSummary": summarize_profile(profile),
        }
    if feature == "SNS":
        return {
            **sns_details(context),
            "profileSummary": summarize_profile(profile),
        }
    return {
        "profileSummary": summarize_profile(profile),
        "currentResult": result_ctx.get("currentResult"),
    }


def build_result_payload(request: dict[str, Any], result_spec: dict[str, Any] | None) -> dict[str, Any] | None:
    if result_spec is None:
        return None

    return {
        "targetFeature": result_spec["targetFeature"],
        "resultType": result_spec["resultType"],
        "resultTitle": result_spec["resultTitle"],
        "shouldCreateResult": True,
        "routeKey": result_spec["routeKey"],
        "referenceId": request.get("roomId"),
        "payload": {
            "mock": True,
            "sourceMessage": request_message(request),
            "featurePayload": build_feature_payload(request),
            "reference": as_dict((request.get("payload") or {}).get("reference")),
        },
    }


def build_response(request: dict[str, Any]) -> dict[str, Any]:
    summary = build_summary(request)
    agent = choose_agent(request)
    agents = selected_agents(request)
    result_spec = infer_result_spec(request)
    result_payload = build_result_payload(request, result_spec)
    feature = feature_key(request)

    return {
        "requestId": request.get("requestId"),
        "roomId": request.get("roomId"),
        "intent": request.get("intent"),
        "agent": agent,
        "summary": summary,
        "data": {
            "mock": True,
            "agentContractVersion": "mock-v3",
            "featureKey": feature,
            "featurePayload": build_feature_payload(request),
            "selectedAgents": agents,
            "usedMessage": request_message(request),
        },
        "nextActions": [
            "Review the generated follow-up result",
            "Ask a narrower follow-up question",
        ],
        "warnings": [],
        "result": result_payload,
        "version": "v1",
        "messageType": "CHAT_RESPONSE",
        "userId": request.get("userId"),
        "targetFeature": None if feature == "FREE_DISCUSSION" else feature,
        "status": "COMPLETED",
        "payload": {
            "common": {
                "message": summary,
                "agent": agent,
                "intent": request.get("intent"),
            },
            "featureKey": feature,
            "featurePayload": build_feature_payload(request),
            "result": result_payload,
            "meta": {
                "mock": True,
                "orchestrator": orchestrator_name(feature),
            },
        },
    }


def orchestrator_name(feature: str) -> str:
    return {
        "ITEM": "IdeaChatOrchestrator",
        "SIMULATOR": "SimulationChatOrchestrator",
        "SUPPORT": "SupportChatOrchestrator",
        "PLAN": "PlanChatOrchestrator",
        "OPERATION": "OperationChatOrchestrator",
        "SNS": "SnsChatOrchestrator",
    }.get(feature, "FreeDiscussionOrchestrator")


def build_event_message(request: dict[str, Any], event_type: str, agent: dict[str, str] | None = None) -> str:
    feature = feature_key(request)
    message = request_message(request)

    if event_type == "ORCHESTRATION_STARTED":
        return f"{orchestrator_name(feature)} is analyzing: {message}"
    if event_type == "AGENT_SELECTED":
        return f"Selected agents for {feature.lower()} chat."
    if event_type == "AGENT_STARTED" and agent is not None:
        return f"{agent['label']} started reviewing the current context."
    if event_type == "AGENT_COMPLETED" and agent is not None:
        return f"{agent['label']} finished its current review."
    return message


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
    selected: list[dict[str, str]],
    current_agent: dict[str, str] | None = None,
) -> dict[str, Any]:
    feature = feature_key(request)
    return {
        "requestId": request.get("requestId"),
        "roomId": request.get("roomId"),
        "intent": request.get("intent"),
        "agent": current_agent.get("label") if current_agent else None,
        "summary": build_event_message(request, event_type, current_agent),
        "data": {"mock": True},
        "nextActions": [],
        "warnings": [],
        "result": None,
        "version": "v1",
        "messageType": "AGENT_EVENT",
        "userId": request.get("userId"),
        "targetFeature": None if feature == "FREE_DISCUSSION" else feature,
        "status": "PROCESSING",
        "payload": {
            "eventType": event_type,
            "orchestrator": orchestrator_name(feature),
            "sequence": sequence,
            "message": build_event_message(request, event_type, current_agent),
            "selectedAgents": selected,
            "agent": current_agent,
            "meta": {
                "mock": True,
                "featureKey": feature,
            },
        },
    }


def emit_agent_progress(channel: pika.adapters.blocking_connection.BlockingChannel, request: dict[str, Any]) -> None:
    selected = selected_agents(request)

    publish_json(channel, build_agent_event(request, "ORCHESTRATION_STARTED", 1, selected))
    time.sleep(EVENT_DELAY_SECONDS)

    publish_json(channel, build_agent_event(request, "AGENT_SELECTED", 2, selected))
    time.sleep(EVENT_DELAY_SECONDS)

    sequence = 3
    for agent in selected[:3]:
        running_agent = {**agent, "status": "running"}
        publish_json(channel, build_agent_event(request, "AGENT_STARTED", sequence, selected, running_agent))
        time.sleep(EVENT_DELAY_SECONDS)
        sequence += 1

        completed_agent = {**agent, "status": "completed"}
        publish_json(channel, build_agent_event(request, "AGENT_COMPLETED", sequence, selected, completed_agent))
        time.sleep(EVENT_DELAY_SECONDS)
        sequence += 1


def on_message(channel, method, properties, body):
    try:
        request = json.loads(body.decode("utf-8"))
        emit_agent_progress(channel, request)
        response = build_response(request)
        publish_json(channel, response)
        logging.info(
            "Mock response published requestId=%s roomId=%s feature=%s",
            request.get("requestId"),
            request.get("roomId"),
            feature_key(request),
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
