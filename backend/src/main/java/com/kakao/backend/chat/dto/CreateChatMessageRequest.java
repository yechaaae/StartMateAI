package com.kakao.backend.chat.dto;

public record CreateChatMessageRequest(
        Long userId,
        String content,
        String metadata
) {
}
