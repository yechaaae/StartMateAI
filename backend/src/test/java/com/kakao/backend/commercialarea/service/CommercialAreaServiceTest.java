package com.kakao.backend.commercialarea.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class CommercialAreaServiceTest {

    @Autowired
    private CommercialAreaService commercialAreaService;

    @Test
    void analyzesDirectCompetitorsFromDemoStores() {
        commercialAreaService.importDemoStores();

        CommercialAreaResponse response = commercialAreaService.analyze(new CommercialAreaRequest(
                "서울",
                "마포구",
                "연남동",
                null,
                null,
                null,
                "음식점업",
                "커피점/카페",
                "카페"
        ));

        assertThat(response.totalStores()).isEqualTo(7);
        assertThat(response.directCompetitors()).isEqualTo(5);
        assertThat(response.competitionLevel()).isEqualTo("low");
        assertThat(response.notes()).anyMatch(note -> note.contains("임대료"));
    }

}
