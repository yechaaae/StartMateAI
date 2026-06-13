package com.kakao.backend.aichat.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import com.kakao.backend.commercialarea.service.CommercialAreaService;
import com.kakao.backend.policy.dto.RecommendedProgramResponse;
import com.kakao.backend.policy.dto.SupportProgramRecommendationRequest;
import com.kakao.backend.policy.service.SupportProgramService;
import com.kakao.backend.startupProfile.model.StartupProfile;
import com.kakao.backend.user.model.User;
import com.kakao.backend.workspace.domain.Workspace;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AiChatExternalReferenceDataServiceTest {

    @Mock
    private SupportProgramService supportProgramService;

    @Mock
    private CommercialAreaService commercialAreaService;

    @InjectMocks
    private AiChatExternalReferenceDataService service;

    @Test
    void attachesRecommendedSupportProgramsForPolicyAgent() {
        when(supportProgramService.recommend(any(SupportProgramRecommendationRequest.class)))
                .thenReturn(List.of(new RecommendedProgramResponse(
                        1L,
                        "청년 예비창업 패키지",
                        "kstartup",
                        "사업화 자금과 멘토링 지원",
                        "전국",
                        "최대 5천만원",
                        "사업계획서,개인정보동의서",
                        "창업진흥원",
                        "grant",
                        "open",
                        92,
                        List.of("청년 연령 조건에 맞을 가능성이 높습니다."),
                        List.of(),
                        LocalDate.of(2026, 6, 30),
                        "https://example.com/apply"
                )));

        Map<String, Object> externalData = service.resolve(command(
                "서울 지원사업 추천해줘",
                "SUPPORT",
                List.of("PolicyAgent")
        ));

        assertThat(externalData).containsKey("supportPrograms");
        Map<?, ?> supportPrograms = (Map<?, ?>) externalData.get("supportPrograms");
        assertThat(supportPrograms.get("source")).isEqualTo("backend.support_programs");
        assertThat((List<?>) supportPrograms.get("items")).hasSize(1);
        Map<?, ?> firstItem = (Map<?, ?>) ((List<?>) supportPrograms.get("items")).getFirst();
        assertThat(firstItem.get("title")).isEqualTo("청년 예비창업 패키지");
        assertThat(firstItem.get("matchScore")).isEqualTo(92);

        ArgumentCaptor<SupportProgramRecommendationRequest> captor =
                ArgumentCaptor.forClass(SupportProgramRecommendationRequest.class);
        verify(supportProgramService).recommend(captor.capture());
        assertThat(captor.getValue().desiredSido()).isEqualTo("서울");
        assertThat(captor.getValue().desiredSigungu()).isEqualTo("마포구");
        assertThat(captor.getValue().industryMedium()).isEqualTo("커피점/카페");
    }

    @Test
    void attachesCommercialAreaAnalysisWhenMessageContainsCommercialAreaKeywords() {
        when(commercialAreaService.analyze(any(CommercialAreaRequest.class)))
                .thenReturn(new CommercialAreaResponse(
                        "서울 마포구 연남동",
                        "음식점업 > 커피점/카페 > 카페",
                        7,
                        5,
                        1,
                        "low",
                        List.of("정확한 임대료/매출/유동인구는 별도 데이터가 필요합니다.")
                ));

        Map<String, Object> externalData = service.resolve(command(
                "서울 마포구 연남동 카페 상권 경쟁 봐줘",
                null,
                List.of()
        ));

        assertThat(externalData).containsKey("commercialArea");
        Map<?, ?> commercialArea = (Map<?, ?>) externalData.get("commercialArea");
        assertThat(commercialArea.get("source")).isEqualTo("backend.commercial_area");
        assertThat(commercialArea.get("directCompetitors")).isEqualTo(5);
        assertThat(commercialArea.get("competitionLevel")).isEqualTo("low");

        ArgumentCaptor<CommercialAreaRequest> captor = ArgumentCaptor.forClass(CommercialAreaRequest.class);
        verify(commercialAreaService).analyze(captor.capture());
        assertThat(captor.getValue().sido()).isEqualTo("서울");
        assertThat(captor.getValue().sigungu()).isEqualTo("마포구");
        assertThat(captor.getValue().dong()).isEqualTo("연남동");
        assertThat(captor.getValue().industrySmall()).isEqualTo("카페");
    }

    private AiChatDispatchCommand command(String content, String targetFeature, List<String> candidateAgents) {
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(1L);
        workspace.setUser(user);

        StartupProfile profile = StartupProfile.create(user);
        profile.setBusinessRegion("서울 마포구 연남동");
        profile.setInterestField("카페");

        ChatRoom room = ChatRoom.create(workspace, "chat", "FEATURE_DISCUSSION", targetFeature);
        room.setId(10L);

        ChatMessage message = ChatMessage.userMessage(room, user, content, null);
        message.setId(100L);

        return new AiChatDispatchCommand(
                "req-123",
                workspace,
                room,
                user,
                profile,
                message,
                "auto",
                "FEATURE_CHAT",
                null,
                null,
                null,
                candidateAgents,
                List.of(),
                Map.of(),
                Map.of()
        );
    }
}
