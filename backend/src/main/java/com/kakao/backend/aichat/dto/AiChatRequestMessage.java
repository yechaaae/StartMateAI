package com.kakao.backend.aichat.dto;

import java.util.Map;

public record AiChatRequestMessage(
        String version,
        String messageType,
        String requestId,
        Long workspaceId,
        Long roomId,
        Long messageId,
        Long userId,
        String roomType,
        String targetFeature,
        String sessionType,
        String intent,
        Map<String, Object> payload
) {
}