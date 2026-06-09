package com.kakao.backend.chat.dto;

public record ChatMessageStreamResponse(
        Long roomId,
        Long messageId,
        String senderType,
        String content,
        String metadata
) {
}
