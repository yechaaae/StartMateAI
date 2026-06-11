package com.kakao.backend.policy.normalize;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.policy.domain.SupportProgram;
import java.time.LocalDate;
import java.util.Map;
import org.junit.jupiter.api.Test;

class SupportProgramNormalizerTest {

    private final SupportProgramNormalizer normalizer = new SupportProgramNormalizer(new ObjectMapper(), new DateNormalizer());

    @Test
    void normalizesKstartupLikeAnnouncement() {
        SupportProgram program = normalizer.normalize("kstartup", Map.of(
                "pbancSn", "K-001",
                "bizPbancNm", "청년 예비창업 사업화 지원",
                "bizPbancCn", "청년 창업자를 위한 사업화 자금 지원",
                "aplyTrgt", "만 19세 이상 39세 이하 예비창업자",
                "suptRegin", "전국",
                "rqutPrdCn", "2026.06.01 ~ 2026.06.30",
                "sprvInstNm", "창업진흥원",
                "aplyUrl", "https://www.k-startup.go.kr"
        ));

        assertThat(program.getSource()).isEqualTo("kstartup");
        assertThat(program.getSourceId()).isEqualTo("K-001");
        assertThat(program.getTitle()).isEqualTo("청년 예비창업 사업화 지원");
        assertThat(program.getSupportType()).isEqualTo("grant");
        assertThat(program.getAgeCondition()).isEqualTo("youth_19_39");
        assertThat(program.getApplicationStartDate()).isEqualTo(LocalDate.of(2026, 6, 1));
        assertThat(program.getApplicationEndDate()).isEqualTo(LocalDate.of(2026, 6, 30));
    }

    @Test
    void infersRegionFromBracketedTitleWhenRegionFieldIsMissing() {
        SupportProgram program = normalizer.normalize("bizinfo", Map.of(
                "pblancId", "B-001",
                "pblancNm", "[경북] 청년 창업기업 사업화 지원",
                "bsnsSumryCn", "지역 청년 창업자를 위한 사업화 자금 지원"
        ));

        assertThat(program.getRegionCondition()).isEqualTo("경북");
    }

    @Test
    void infersNonCapitalAreaRegionConditionBeforeCapitalAreaText() {
        SupportProgram program = normalizer.normalize("bizinfo", Map.of(
                "pblancId", "B-002",
                "pblancNm", "[비수도권] 창업기업 성장 지원",
                "bsnsSumryCn", "수도권 외 지역 기업을 우대합니다."
        ));

        assertThat(program.getRegionCondition()).isEqualTo("비수도권");
    }

    @Test
    void titleRegionOverridesNationwideFieldWhenTitleHasStrongRegionMarker() {
        SupportProgram program = normalizer.normalize("kstartup", Map.of(
                "pbancSn", "K-002",
                "bizPbancNm", "2026년 전북 농식품 테크 예비창업기업 모집",
                "bizPbancCn", "농식품 기술 창업자를 위한 사업화 지원",
                "suptRegin", "전국"
        ));

        assertThat(program.getRegionCondition()).isEqualTo("전북");
    }

    @Test
    void doesNotTreatBrandLikeAttachedCityNameAsRegionRestriction() {
        SupportProgram program = normalizer.normalize("bizinfo", Map.of(
                "pblancId", "B-003",
                "pblancNm", "2026년 서울뷰티위크 비즈니스 밋업 참가기업 모집",
                "bsnsSumryCn", "공고일 기준 전국 예비 창업자 및 초기기업 지원"
        ));

        assertThat(program.getRegionCondition()).isEqualTo("전국");
    }
}
