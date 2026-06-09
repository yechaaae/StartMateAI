package com.kakao.backend.chat.dto;

import java.time.LocalDateTime;

public record ChatMessageResponse(
        Long id,
        Long roomId,
        Long userId,
        Long agentId,
        String senderType,
        String content,
        String metadata,
        LocalDateTime createdAt
) {
}
