package com.kakao.backend.aichat.application;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import org.junit.jupiter.api.Test;

class AiChatResultSupportServiceTest {

    private final AiChatResultSupportService supportService =
            new AiChatResultSupportService(new AiChatResponsePayloadReader(new ObjectMapper()));
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void extractsPromotableResultFromPayload() {
        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-777",
                15L,
                "idea",
                "IdeaAgent",
                null,
                java.util.Map.of(),
                java.util.List.of(),
                java.util.List.of(),
                null,
                "v1",
                "CHAT_RESPONSE",
                2L,
                "IDEA",
                "COMPLETED",
                objectMapper.valueToTree(java.util.Map.of(
                        "result", java.util.Map.of(
                                "targetFeature", "IDEA",
                                "resultType", "BUSINESS_IDEA_RESULT",
                                "resultTitle", "idea report",
                                "shouldCreateResult", true,
                                "routeKey", "idea-report",
                                "referenceId", 44,
                                "payload", java.util.Map.of("score", 87)
                        )
                ))
        );

        AiChatPromotedResult promotedResult = supportService.extract(response).orElseThrow();

        assertThat(promotedResult.roomId()).isEqualTo(15L);
        assertThat(promotedResult.targetFeature()).isEqualTo("IDEA");
        assertThat(promotedResult.resultType()).isEqualTo("BUSINESS_IDEA_RESULT");
        assertThat(promotedResult.routeKey()).isEqualTo("idea-report");
        assertThat(promotedResult.referenceId()).isEqualTo(44L);
        assertThat(promotedResult.payload()).containsEntry("score", 87);
    }

    @Test
    void ignoresNonPromotableResponses() {
        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-778",
                16L,
                "free",
                "FreeChatAgent",
                "chat note",
                java.util.Map.of(),
                java.util.List.of(),
                java.util.List.of(),
                null,
                "v1",
                "CHAT_RESPONSE",
                2L,
                "FREE_DISCUSSION",
                "COMPLETED",
                objectMapper.valueToTree(java.util.Map.of(
                        "result", java.util.Map.of(
                                "targetFeature", "FREE_DISCUSSION",
                                "resultType", "FREE_CHAT_NOTE",
                                "resultTitle", "chat note",
                                "shouldCreateResult", false,
                                "payload", java.util.Map.of()
                        )
                ))
        );

        assertThat(supportService.extract(response)).isEmpty();
    }
}
