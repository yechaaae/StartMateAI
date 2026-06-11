package com.kakao.backend.chat.dto;

import java.util.List;
import java.util.Map;

public record ChatAgentProgressPayload(
        String requestId,
        String status,
        String targetFeature,
        String eventType,
        String type,
        String viewType,
        String orchestrator,
        Integer sequence,
        String message,
        ChatAgentDescriptorPayload agent,
        List<ChatAgentDescriptorPayload> selectedAgents,
        Map<String, Object> detail
) {
}
