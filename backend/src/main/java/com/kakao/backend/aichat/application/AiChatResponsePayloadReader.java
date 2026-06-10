package com.kakao.backend.aichat.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.aichat.dto.AiChatResultPayload;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class AiChatResponsePayloadReader {

    private final ObjectMapper objectMapper;

    public AiChatResponsePayloadReader(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public String extractContent(AiChatResponseMessage response) {
        return firstNonBlank(
                textAt(response.payload(), "common", "message"),
                textAt(response.payload(), "message"),
                textAt(response.payload(), "summary"),
                response.summary(),
                "AI response received."
        );
    }

    public String extractIntent(AiChatResponseMessage response) {
        return firstNonBlank(
                response.intent(),
                textAt(response.payload(), "intent"),
                textAt(response.payload(), "common", "intent")
        );
    }

    public String extractAgent(AiChatResponseMessage response) {
        return firstNonBlank(
                response.agent(),
                textAt(response.payload(), "agent"),
                textAt(response.payload(), "common", "agent")
        );
    }

    public AiChatResultPayload extractResult(AiChatResponseMessage response) {
        if (response.result() != null) {
            return response.result();
        }

        Object resultNode = nodeAt(response.payload(), "result");
        if (!(resultNode instanceof Map<?, ?>)) {
            return null;
        }
        return objectMapper.convertValue(resultNode, AiChatResultPayload.class);
    }

    public String extractErrorMessage(AiChatResponseMessage response) {
        return firstNonBlank(
                textAt(response.payload(), "error", "message"),
                textAt(response.payload(), "message"),
                response.summary()
        );
    }

    @SuppressWarnings("unchecked")
    private Object nodeAt(Map<String, Object> root, String... path) {
        if (root == null) {
            return null;
        }
        Object current = root;
        for (String segment : path) {
            if (!(current instanceof Map<?, ?> currentMap)) {
                return null;
            }
            current = ((Map<String, Object>) currentMap).get(segment);
        }
        return current;
    }

    private String textAt(Map<String, Object> root, String... path) {
        Object node = nodeAt(root, path);
        if (node == null) {
            return null;
        }
        String text = String.valueOf(node);
        return text == null || text.isBlank() ? null : text;
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }
}