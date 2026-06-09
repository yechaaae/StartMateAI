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
}
