package com.kakao.backend.chat.dto;

public record ChatStreamEventResponse(
        String eventId,
        String eventType,
        Long roomId,
        String occurredAt,
        ChatStreamMessagePayload message,
        ChatRequestStatusPayload status,
        ChatAgentProgressPayload agentProgress
) {
}
