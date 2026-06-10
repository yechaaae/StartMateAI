package com.kakao.backend.internal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import com.kakao.backend.commercialarea.service.CommercialAreaService;
import com.kakao.backend.policy.dto.RecommendedProgramResponse;
import com.kakao.backend.policy.dto.SupportProgramRecommendationRequest;
import com.kakao.backend.policy.dto.SupportProgramSyncResponse;
import com.kakao.backend.policy.service.SupportProgramService;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class InternalAiToolControllerTest {

    private static final String TOKEN = "test-token";

    @Mock
    private SupportProgramService supportProgramService;

    @Mock
    private CommercialAreaService commercialAreaService;

    @Test
    void rejectsRequestWithoutValidInternalToken() {
        InternalAiToolController controller = controller();
        SupportProgramRecommendationRequest request = supportRequest();

        assertThatThrownBy(() -> controller.recommendSupportPrograms(null, request))
                .isInstanceOfSatisfying(ResponseStatusException.class, exception ->
                        assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED));

        assertThatThrownBy(() -> controller.recommendSupportPrograms("wrong-token", request))
                .isInstanceOfSatisfying(ResponseStatusException.class, exception ->
                        assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED));
    }

    @Test
    void returnsSupportRecommendationsWithValidInternalToken() {
        InternalAiToolController controller = controller();
        SupportProgramRecommendationRequest request = supportRequest();
        List<RecommendedProgramResponse> expected = List.of(new RecommendedProgramResponse(
                1L,
                "청년 예비창업 패키지",
                "kstartup",
                "사업화 자금과 멘토링 지원",
                92,
                List.of("청년 연령 조건에 맞을 가능성이 높습니다."),
                List.of(),
                LocalDate.of(2026, 6, 30),
                "https://example.com/apply"
        ));
        when(supportProgramService.recommendWithDemoFallback(request)).thenReturn(expected);

        List<RecommendedProgramResponse> actual = controller.recommendSupportPrograms(TOKEN, request);

        assertThat(actual).isEqualTo(expected);
        verify(supportProgramService).recommendWithDemoFallback(request);
    }

    @Test
    void syncsSupportProgramsWithValidInternalToken() {
        InternalAiToolController controller = controller();
        SupportProgramSyncResponse expected = new SupportProgramSyncResponse(Map.of("demo", 4), 4);
        when(supportProgramService.sync("all")).thenReturn(expected);

        SupportProgramSyncResponse actual = controller.syncSupportPrograms(TOKEN, "all");

        assertThat(actual).isEqualTo(expected);
        verify(supportProgramService).sync("all");
    }

    @Test
    void analyzesCommercialAreaWithValidInternalToken() {
        InternalAiToolController controller = controller();
        CommercialAreaRequest request = new CommercialAreaRequest(
                "서울",
                "마포구",
                "연남동",
                null,
                null,
                null,
                "음식점업",
                "커피점/카페",
                "카페"
        );
        CommercialAreaResponse expected = new CommercialAreaResponse(
                "서울 마포구 연남동",
                "음식점업 > 커피점/카페 > 카페",
                7,
                5,
                1,
                "low",
                List.of("정확한 임대료/매출은 별도 데이터 필요")
        );
        when(commercialAreaService.analyze(request)).thenReturn(expected);

        CommercialAreaResponse actual = controller.analyzeCommercialArea(TOKEN, request);

        assertThat(actual).isEqualTo(expected);
        verify(commercialAreaService).analyze(request);
    }

    private InternalAiToolController controller() {
        return new InternalAiToolController(
                new InternalToolAuthService(TOKEN),
                supportProgramService,
                commercialAreaService
        );
    }

    private SupportProgramRecommendationRequest supportRequest() {
        return new SupportProgramRecommendationRequest(
                27,
                "서울",
                "서울",
                "마포구",
                "pre_founder",
                false,
                null,
                "idea",
                "음식점업",
                "커피점/카페",
                "카페",
                30_000_000L,
                List.of("grant", "education", "mentoring", "space")
        );
    }
}
