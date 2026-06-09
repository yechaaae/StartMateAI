package com.kakao.backend.aichat.dto;

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
        List<String> warnings
) {
}
