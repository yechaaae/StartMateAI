package com.kakao.backend.chat.dto;

public record ChatRequestStatusPayload(
        String requestId,
        Long messageId,
        String status,
        String errorMessage,
        String updatedAt
) {
}
