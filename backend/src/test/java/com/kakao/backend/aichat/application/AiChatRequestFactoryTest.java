package com.kakao.backend.aichat.application;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.aichat.dto.AiChatRequestMessage;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.startupProfile.model.PreferredBusinessType;
import com.kakao.backend.startupProfile.model.StartupProfile;
import com.kakao.backend.user.model.User;
import com.kakao.backend.workspace.domain.Workspace;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AiChatRequestFactoryTest {

    private final AiChatRequestFactory factory = new AiChatRequestFactory(new ObjectMapper());

    @Test
    void buildsFlexibleAiChatRequestEnvelope() {
        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(1L);

        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        StartupProfile profile = StartupProfile.create();
        profile.setMajor("planner");
        profile.setCareer("cafe,SNS");
        profile.setInterestField("food,local");
        profile.setBusinessRegion("busan");
        profile.setInitialBudget(1_000_000);
        profile.setPreferredBusinessType(PreferredBusinessType.OFFLINE);
        profile.setDiagnosisSummary("good fit");
        profile.setStrengthTags("brand,content");

        ChatRoom room = ChatRoom.create(workspace, "idea chat", "FEATURE", "IDEA");
        room.setId(10L);

        ChatMessage message = ChatMessage.userMessage(room, user, "Recommend ideas", "{\"source\":\"workspace\"}");
        message.setId(100L);

        ChatMessage previous = ChatMessage.userMessage(room, user, "Previous context", null);
        previous.setId(99L);

        AiChatDispatchCommand command = new AiChatDispatchCommand(
                "req-123",
                workspace,
                room,
                user,
                profile,
                message,
                "idea",
                "FEATURE_CHAT",
                "BUSINESS_IDEA_RESULT",
                44L,
                9L,
                List.of("IdeaAgent", "FinanceAgent", "PolicyAgent"),
                List.of(previous),
                Map.of("title", "idea report"),
                Map.of("referenceType", "BUSINESS_IDEA_RESULT", "referenceId", 44L, "title", "idea report")
        );

        AiChatRequestMessage request = factory.create(command);

        assertThat(request.version()).isEqualTo("v1");
        assertThat(request.messageType()).isEqualTo("CHAT_REQUEST");
        assertThat(request.requestId()).isEqualTo("req-123");
        assertThat(request.roomId()).isEqualTo(10L);
        assertThat(request.userId()).isEqualTo(2L);
        assertThat(request.targetFeature()).isEqualTo("IDEA");
        assertThat(request.intent()).isEqualTo("idea");
        assertThat(request.payload().path("common").path("message").asText()).isEqualTo("Recommend ideas");
        assertThat(request.payload().path("profile").path("major").asText()).isEqualTo("planner");
        assertThat(request.payload().path("profile").path("budgetKrw").asInt()).isEqualTo(1_000_000);
        assertThat(request.payload().path("conversation").path("recentMessages")).hasSize(1);
        assertThat(request.payload().path("resultContext").path("currentResultType").asText()).isEqualTo("BUSINESS_IDEA_RESULT");
        assertThat(request.payload().path("resultContext").path("currentResultId").asLong()).isEqualTo(44L);
        assertThat(request.payload().path("options").path("candidateAgents")).hasSize(3);
        assertThat(request.payload().path("reference").path("referenceId").asLong()).isEqualTo(44L);
    }
}
