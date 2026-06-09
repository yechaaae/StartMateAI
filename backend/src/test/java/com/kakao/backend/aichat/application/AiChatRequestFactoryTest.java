package com.kakao.backend.aichat.application;

import static org.assertj.core.api.Assertions.assertThat;

import com.kakao.backend.aichat.dto.AiChatContextPayload;
import com.kakao.backend.aichat.dto.AiChatRequestMessage;
import com.kakao.backend.domain.ChatMessage;
import com.kakao.backend.domain.ChatRoom;
import com.kakao.backend.domain.StartupProfile;
import com.kakao.backend.domain.User;
import com.kakao.backend.domain.Workspace;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AiChatRequestFactoryTest {

    private final AiChatRequestFactory factory = new AiChatRequestFactory();

    @Test
    void buildsAiChatRequestFromChatDomainContext() {
        Workspace workspace = Workspace.create("워크스페이스", "ACTIVE");
        workspace.setId(1L);

        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        StartupProfile profile = StartupProfile.create();
        profile.setMajor("디자인");
        profile.setCareer("카페 아르바이트, SNS 콘텐츠 제작");
        profile.setInterestField("카페, 로컬");
        profile.setBusinessRegion("부산");
        profile.setInitialBudget(1_000_000);
        profile.setPreferredBusinessType("오프라인");
        profile.setDiagnosisSummary("소자본 창업에 적합");
        profile.setStrengthTags("브랜딩, 콘텐츠");

        ChatRoom room = ChatRoom.create(workspace, "아이템 추천 채팅", "FEATURE", "IDEA");
        room.setId(10L);

        ChatMessage message = ChatMessage.userMessage(room, user, "초기 자금 100만원 기준으로 다시 추천해줘", "{\"source\":\"workspace\"}");
        message.setId(100L);

        ChatMessage previous = ChatMessage.userMessage(room, user, "부산에서 소자본 창업 추천해줘", null);
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
                Map.of("title", "부산 소자본 창업 추천", "options", List.of("로컬 SNS 콘텐츠 스튜디오"))
        );

        AiChatRequestMessage request = factory.create(command);

        assertThat(request.requestId()).isEqualTo("req-123");
        assertThat(request.roomId()).isEqualTo(10L);
        assertThat(request.userId()).isEqualTo(2L);
        assertThat(request.targetFeature()).isEqualTo("IDEA");
        assertThat(request.intent()).isEqualTo("idea");
        assertThat(request.profile().major()).isEqualTo("디자인");
        assertThat(request.profile().region()).isEqualTo("부산");
        assertThat(request.profile().budgetKrw()).isEqualTo(1_000_000);
        assertThat(request.profile().experiences()).contains("카페 아르바이트", "SNS 콘텐츠 제작", "브랜딩", "콘텐츠");
        assertThat(request.profile().interests()).contains("카페", "로컬");

        AiChatContextPayload context = request.context();
        assertThat(context.currentResultType()).isEqualTo("BUSINESS_IDEA_RESULT");
        assertThat(context.currentResultId()).isEqualTo(44L);
        assertThat(context.selectedIdeaId()).isEqualTo(9L);
        assertThat(context.candidateAgents()).containsExactly("IdeaAgent", "FinanceAgent", "PolicyAgent");
        assertThat(context.recentMessages()).hasSize(1);
        assertThat(context.recentMessages().getFirst().content()).isEqualTo("부산에서 소자본 창업 추천해줘");
    }
}
