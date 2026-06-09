package com.kakao.backend.aichat.dto;

public record AiRecentMessagePayload(
        Long messageId,
        String senderType,
        Long userId,
        Long agentId,
        String content
) {
}
