package com.kakao.backend.policy.matcher;

import static org.assertj.core.api.Assertions.assertThat;

import com.kakao.backend.policy.domain.SupportProgram;
import com.kakao.backend.policy.dto.RecommendedProgramResponse;
import com.kakao.backend.policy.dto.SupportProgramRecommendationRequest;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;

class SupportProgramMatcherTest {

    private final SupportProgramMatcher matcher = new SupportProgramMatcher();

    @Test
    void ranksYouthPreFounderOpenProgramWithPositiveReasons() {
        SupportProgram program = SupportProgram.create();
        program.setId(1L);
        program.setSource("demo");
        program.setTitle("청년 예비창업 패키지");
        program.setSummary("사업화 자금과 멘토링 지원");
        program.setSupportType("grant");
        program.setTarget("만 19세 이상 39세 이하 청년 예비창업자");
        program.setAgeCondition("youth_19_39");
        program.setRegionCondition("서울");
        program.setBusinessStageCondition("idea,preparing,pre_founder");
        program.setIndustryCondition("음식점업");
        program.setStatus("open");
        program.setApplicationEndDate(LocalDate.now().plusDays(10));

        SupportProgramRecommendationRequest profile = new SupportProgramRecommendationRequest(
                27,
                "서울",
                "서울",
                "마포구",
                "pre_founder",
                false,
                null,
                "idea",
                "음식점업",
                "카페",
                null,
                30_000_000L,
                List.of("grant", "education", "mentoring", "space")
        );

        RecommendedProgramResponse response = matcher.match(program, profile);

        assertThat(response.matchScore()).isGreaterThanOrEqualTo(90);
        assertThat(response.matchReasons()).anyMatch(reason -> reason.contains("청년"));
        assertThat(response.cautionReasons()).isEmpty();
    }
}
