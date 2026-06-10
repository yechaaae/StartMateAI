package com.kakao.backend.chat.application;

import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.chat.dto.ChatAgentDescriptorPayload;
import com.kakao.backend.chat.dto.ChatAgentProgressPayload;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class ChatAiAgentEventService {

    private final ChatSseService chatSseService;

    public ChatAiAgentEventService(ChatSseService chatSseService) {
        this.chatSseService = chatSseService;
    }

    public void handle(AiChatResponseMessage response) {
        if (response == null || response.roomId() == null) {
            return;
        }

        ChatAgentProgressPayload payload = new ChatAgentProgressPayload(
                response.requestId(),
                response.status(),
                response.targetFeature(),
                textAt(response.payload(), "eventType"),
                textAt(response.payload(), "orchestrator"),
                integerAt(response.payload(), "sequence"),
                textAt(response.payload(), "message"),
                descriptorAt(mapAt(response.payload(), "agent")),
                descriptorsAt(listAt(response.payload(), "selectedAgents"))
        );

        chatSseService.publishAgentProgress(response.roomId(), payload);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapAt(Map<String, Object> payload, String key) {
        if (payload == null) {
            return null;
        }
        Object value = payload.get(key);
        return value instanceof Map<?, ?> ? (Map<String, Object>) value : null;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> listAt(Map<String, Object> payload, String key) {
        if (payload == null) {
            return List.of();
        }
        Object value = payload.get(key);
        if (!(value instanceof List<?> list)) {
            return List.of();
        }

        List<Map<String, Object>> results = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                results.add((Map<String, Object>) map);
            }
        }
        return results;
    }

    private ChatAgentDescriptorPayload descriptorAt(Map<String, Object> payload) {
        if (payload == null || payload.isEmpty()) {
            return null;
        }
        return new ChatAgentDescriptorPayload(
                text(payload, "agentKey"),
                text(payload, "label"),
                text(payload, "role"),
                text(payload, "status")
        );
    }

    private List<ChatAgentDescriptorPayload> descriptorsAt(List<Map<String, Object>> payloads) {
        if (payloads == null || payloads.isEmpty()) {
            return List.of();
        }
        return payloads.stream()
                .map(this::descriptorAt)
                .filter(item -> item != null)
                .toList();
    }

    private String textAt(Map<String, Object> payload, String key) {
        return text(payload, key);
    }

    private String text(Map<String, Object> payload, String key) {
        if (payload == null) {
            return null;
        }
        Object value = payload.get(key);
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value);
        return text.isBlank() ? null : text;
    }

    private Integer integerAt(Map<String, Object> payload, String key) {
        if (payload == null) {
            return null;
        }
        Object value = payload.get(key);
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String text && !text.isBlank()) {
            try {
                return Integer.parseInt(text);
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }
}
