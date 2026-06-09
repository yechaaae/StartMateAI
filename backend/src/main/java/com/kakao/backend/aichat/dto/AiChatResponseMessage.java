package com.kakao.backend.aichat.dto;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;
import java.util.Map;

public record AiChatResponseMessage(
        String requestId,
        Long roomId,
        String intent,
        String agent,
        String summary,
        Map<String, Object> data,
        List<String> nextActions,
        List<String> warnings,
        AiChatResultPayload result,
        String version,
        String messageType,
        Long userId,
        String targetFeature,
        String status,
        JsonNode payload
) {

    public AiChatResponseMessage(
            String requestId,
            Long roomId,
            String intent,
            String agent,
            String summary,
            Map<String, Object> data,
            List<String> nextActions,
            List<String> warnings,
            AiChatResultPayload result
    ) {
        this(
                requestId,
                roomId,
                intent,
                agent,
                summary,
                data,
                nextActions,
                warnings,
                result,
                "v1",
                "CHAT_RESPONSE",
                null,
                null,
                null,
                null
        );
    }
}
