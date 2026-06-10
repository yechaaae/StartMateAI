package com.kakao.backend.chat.dto;

public record ChatStreamMessagePayload(
        Long messageId,
        Long userId,
        Long agentId,
        String senderType,
        String content,
        String metadata,
        String createdAt
) {
}
