package com.kakao.backend.aichat.application;

import static org.assertj.core.api.Assertions.assertThat;

import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.startupProfile.model.StartupProfile;
import com.kakao.backend.user.model.User;
import com.kakao.backend.workspace.domain.Workspace;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AiChatPromptContextAssemblerTest {

    private final AiChatPromptContextAssembler assembler =
            new AiChatPromptContextAssembler(
                    new com.fasterxml.jackson.databind.ObjectMapper(),
                    new AiChatFeaturePayloadResolver()
            );

    @Test
    void assemblesFeatureChatPayloadWithFeatureSpecificContext() {
        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(1L);

        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        StartupProfile startupProfile = StartupProfile.create();
        startupProfile.setUser(user);

        ChatRoom room = ChatRoom.create(workspace, "support chat", "FEATURE_DISCUSSION", "SUPPORT");
        room.setId(10L);

        ChatMessage message = ChatMessage.userMessage(room, user, "지원사업 추천해줘", null);
        message.setId(100L);

        ChatMessage previous = ChatMessage.userMessage(room, user, "이전 대화", null);
        previous.setId(99L);

        AiChatDispatchCommand command = new AiChatDispatchCommand(
                "req-123",
                workspace,
                room,
                user,
                startupProfile,
                message,
                "auto",
                "FEATURE_CHAT",
                "SUPPORT_REPORT",
                null,
                12L,
                List.of("PolicyAgent", "PlanAgent"),
                List.of(previous),
                Map.of(
                        "supportSearchMode", "PROFILE_IDEA",
                        "selectedSupportProgram", Map.of("title", "청년 창업 지원"),
                        "recommendations", List.of(Map.of("title", "청년 창업 지원"))
                ),
                Map.of("referenceId", 55L)
        );

        Map<String, Object> payload = assembler.assemble(command);

        assertThat(payload).containsKeys("common", "conversation", "resultContext", "options", "featureContext");

        Map<?, ?> conversation = (Map<?, ?>) payload.get("conversation");
        Map<?, ?> options = (Map<?, ?>) payload.get("options");
        Map<?, ?> featureContext = (Map<?, ?>) payload.get("featureContext");

        assertThat(conversation.get("sessionType")).isEqualTo("FEATURE_CHAT");
        assertThat(conversation.get("targetFeature")).isEqualTo("SUPPORT");
        assertThat((List<?>) conversation.get("recentMessages")).hasSize(1);

        assertThat(options.get("intent")).isEqualTo("auto");
        assertThat(options.get("candidateAgents")).isEqualTo(List.of("PolicyAgent", "PlanAgent"));

        assertThat(featureContext.get("featureKey")).isEqualTo("SUPPORT");
        assertThat(featureContext.get("currentResultType")).isEqualTo("SUPPORT_REPORT");
        assertThat(featureContext.get("selectedIdeaId")).isEqualTo(12L);
        assertThat(featureContext.get("currentResult")).isEqualTo(command.currentResult());
    }

    @Test
    void assemblesOperationFeatureWithBusinessAndReferenceContext() {
        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(1L);

        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        ChatRoom room = ChatRoom.create(workspace, "operation chat", "FEATURE_DISCUSSION", "OPERATION");
        room.setId(10L);

        ChatMessage message = ChatMessage.userMessage(room, user, "광고 효율 좀 봐줘", null);
        message.setId(100L);

        AiChatDispatchCommand command = new AiChatDispatchCommand(
                "req-456",
                workspace,
                room,
                user,
                null,
                message,
                "analyze",
                "FEATURE_CHAT",
                "OPERATION_REPORT",
                77L,
                null,
                List.of("OperationAgent", "MarketingAgent"),
                List.of(),
                Map.of(
                        "businessContext", Map.of("selectedIdea", Map.of("title", "쿠키 브랜드")),
                        "operationInput", Map.of("period", "2026-06"),
                        "operationReport", Map.of("selectedSuggestion", Map.of("title", "광고 전환율 개선")),
                        "contextPriority", List.of("operationInput", "operationReport", "businessContext", "startupProfile")
                ),
                Map.of("savedResult", Map.of("resultId", 77L))
        );

        Map<String, Object> payload = assembler.assemble(command);

        Map<?, ?> featureContext = (Map<?, ?>) payload.get("featureContext");
        Map<String, Object> reference = (Map<String, Object>) payload.get("reference");

        assertThat(featureContext.get("featureKey")).isEqualTo("OPERATION");
        assertThat(featureContext.get("currentResultId")).isEqualTo(77L);
        assertThat(featureContext.get("currentResult")).isEqualTo(command.currentResult());
        assertThat(reference).containsEntry("savedResult", Map.of("resultId", 77L));
    }
}
