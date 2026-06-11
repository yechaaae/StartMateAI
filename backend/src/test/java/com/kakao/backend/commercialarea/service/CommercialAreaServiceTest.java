package com.kakao.backend.commercialarea.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
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

    @Test
    void importsKoreanCommercialStoreCsvWithMs949Encoding() throws Exception {
        Path csv = Files.createTempFile("commercial-stores", ".csv");
        Files.writeString(
                csv,
                """
                        상가업소번호,상호명,상권업종대분류명,상권업종중분류명,상권업종소분류명,시도명,시군구명,행정동명,도로명주소,지번주소,경도,위도
                        csv-001,테스트카페,음식점업,커피점/카페,카페,서울,마포구,합정동,서울 마포구 합정동,서울 마포구 합정동,126.91,37.55
                        """,
                Charset.forName("MS949")
        );

        commercialAreaService.importCsv(csv.toString(), "서울");

        CommercialAreaResponse response = commercialAreaService.analyze(new CommercialAreaRequest(
                "서울",
                "마포구",
                "합정동",
                null,
                null,
                null,
                "음식점업",
                "커피점/카페",
                "카페"
        ));

        assertThat(response.totalStores()).isGreaterThanOrEqualTo(1);
        assertThat(response.directCompetitors()).isGreaterThanOrEqualTo(1);
        assertThat(response.notes()).anyMatch(note -> note.contains("CSV"));
    }
}
