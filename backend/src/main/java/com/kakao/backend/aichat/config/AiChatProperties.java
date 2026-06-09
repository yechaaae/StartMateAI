package com.kakao.backend.aichat.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "startmate.ai.chat")
public record AiChatProperties(
        String requestQueue,
        String responseQueue
) {

    public AiChatProperties {
        requestQueue = requestQueue == null || requestQueue.isBlank() ? "chat.request" : requestQueue;
        responseQueue = responseQueue == null || responseQueue.isBlank() ? "chat.response" : responseQueue;
    }
}
