package com.kakao.backend.aichat.application;

import java.util.Map;

public record AiChatPromotedResult(
        String requestId,
        Long roomId,
        String targetFeature,
        String resultType,
        String resultTitle,
        String routeKey,
        Long referenceId,
        Map<String, Object> payload
) {
}
