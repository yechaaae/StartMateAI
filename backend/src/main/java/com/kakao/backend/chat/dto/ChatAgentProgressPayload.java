package com.kakao.backend.chat.dto;

import java.util.List;

public record ChatAgentProgressPayload(
        String requestId,
        String status,
        String targetFeature,
        String eventType,
        String orchestrator,
        Integer sequence,
        String message,
        ChatAgentDescriptorPayload agent,
        List<ChatAgentDescriptorPayload> selectedAgents
) {
}
