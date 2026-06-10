package com.kakao.backend.chat.application;

public record ChatMessageHistoryItemResult(
        Long messageId,
        Long userId,
        Long agentId,
        String senderType,
        String content,
        String metadata,
        String createdAt
) {
}
