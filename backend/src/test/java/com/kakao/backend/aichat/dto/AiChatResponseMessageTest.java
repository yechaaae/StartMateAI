package com.kakao.backend.aichat.dto;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class AiChatResponseMessageTest {

    @Test
    void keepsLegacyAndFlexibleEnvelopeFieldsTogether() {
        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-321",
                10L,
                "idea",
                "IdeaAgent",
                "summary",
                java.util.Map.of(),
                java.util.List.of(),
                java.util.List.of(),
                null,
                "v1",
                "CHAT_RESPONSE",
                2L,
                "IDEA",
                "COMPLETED",
                java.util.Map.of(
                        "result", java.util.Map.of(
                                "targetFeature", "IDEA",
                                "resultType", "BUSINESS_IDEA_RESULT",
                                "resultTitle", "idea report",
                                "shouldCreateResult", true,
                                "routeKey", "idea-report",
                                "referenceId", 44,
                                "payload", java.util.Map.of("score", 87)
                        )
                )
        );

        assertThat(response.version()).isEqualTo("v1");
        assertThat(response.messageType()).isEqualTo("CHAT_RESPONSE");
        assertThat(response.status()).isEqualTo("COMPLETED");
        assertThat(((java.util.Map<?, ?>) response.payload().get("result")).get("resultType"))
                .isEqualTo("BUSINESS_IDEA_RESULT");
    }
}

