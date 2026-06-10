package com.kakao.backend.chat.application;

public record ChatMessageSendResult(
        String requestId,
        Long roomId,
        Long messageId,
        String senderType,
        String content
) {
}
