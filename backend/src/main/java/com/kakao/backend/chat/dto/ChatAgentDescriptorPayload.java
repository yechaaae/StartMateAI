package com.kakao.backend.chat.dto;

public record ChatAgentDescriptorPayload(
        String agentKey,
        String label,
        String role,
        String status
) {
}
