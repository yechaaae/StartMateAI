package com.kakao.backend.aichat.dto;

public record AiChatRequestMessage(
        String requestId,
        Long workspaceId,
        Long roomId,
        Long messageId,
        Long userId,
        String roomType,
        String targetFeature,
        String sessionType,
        String intent,
        String message,
        AiChatUserProfilePayload profile,
        AiChatContextPayload context
) {
}
