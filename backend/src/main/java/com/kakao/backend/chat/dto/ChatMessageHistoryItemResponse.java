package com.kakao.backend.chat.dto;

public record ChatMessageHistoryItemResponse(
        Long messageId,
        Long userId,
        Long agentId,
        String senderType,
        String content,
        String metadata,
        String createdAt
) {
}
