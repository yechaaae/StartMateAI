package com.kakao.backend.aichat.dto;

import java.util.Map;

public record AiChatResultPayload(
        String targetFeature,
        String resultType,
        String resultTitle,
        boolean shouldCreateResult,
        String routeKey,
        Long referenceId,
        Map<String, Object> payload
) {
}
