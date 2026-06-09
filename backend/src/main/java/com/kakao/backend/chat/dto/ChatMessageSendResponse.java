package com.kakao.backend.chat.dto;

public record ChatMessageSendResponse(
        String requestId,
        Long roomId,
        Long messageId,
        String senderType,
        String content
) {
}
