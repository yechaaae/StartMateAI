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

    @Test
    void penalizesProgramWhenExplicitRegionDoesNotMatchDesiredRegion() {
        SupportProgram program = matchingProgram("경북");
        SupportProgramRecommendationRequest profile = seoulPreFounderCafeProfile();

        RecommendedProgramResponse response = matcher.match(program, profile);

        assertThat(response.matchScore()).isLessThan(80);
        assertThat(response.cautionReasons()).anyMatch(reason -> reason.contains("희망 지역과 공고 지역 조건이 다릅니다."));
    }

    @Test
    void doesNotTreatMissingRegionAsNationwide() {
        SupportProgram program = matchingProgram(null);
        SupportProgramRecommendationRequest profile = seoulPreFounderCafeProfile();

        RecommendedProgramResponse response = matcher.match(program, profile);

        assertThat(response.matchScore()).isLessThan(90);
        assertThat(response.matchReasons()).noneMatch(reason -> reason.contains("전국"));
        assertThat(response.cautionReasons()).anyMatch(reason -> reason.contains("지역 조건 데이터"));
    }

    @Test
    void penalizesNonCapitalAreaProgramForSeoulProfile() {
        SupportProgram program = matchingProgram("비수도권");
        SupportProgramRecommendationRequest profile = seoulPreFounderCafeProfile();

        RecommendedProgramResponse response = matcher.match(program, profile);

        assertThat(response.matchScore()).isLessThan(80);
        assertThat(response.cautionReasons()).anyMatch(reason -> reason.contains("비수도권"));
    }

    private SupportProgram matchingProgram(String regionCondition) {
        SupportProgram program = SupportProgram.create();
        program.setId(2L);
        program.setSource("bizinfo");
        program.setTitle("청년 예비창업 사업화 지원");
        program.setSummary("사업화 자금과 멘토링 지원");
        program.setSupportType("grant");
        program.setTarget("만 19세 이상 39세 이하 청년 예비창업자");
        program.setAgeCondition("youth_19_39");
        program.setRegionCondition(regionCondition);
        program.setBusinessStageCondition("idea,preparing,pre_founder");
        program.setIndustryCondition("음식점업");
        program.setStatus("open");
        program.setApplicationEndDate(LocalDate.now().plusDays(10));
        return program;
    }

    private SupportProgramRecommendationRequest seoulPreFounderCafeProfile() {
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
                "카페",
                null,
                30_000_000L,
                List.of("grant", "education", "mentoring", "space")
        );
    }
}
