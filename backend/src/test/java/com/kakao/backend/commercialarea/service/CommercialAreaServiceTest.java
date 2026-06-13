package com.kakao.backend.commercialarea.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.kakao.backend.commercialarea.repository.CommercialAreaMetricRepository;
import com.kakao.backend.commercialarea.repository.StoreRepository;
import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class CommercialAreaServiceTest {

    @Autowired
    private CommercialAreaService commercialAreaService;

    @Autowired
    private StoreRepository storeRepository;

    @Autowired
    private CommercialAreaMetricRepository metricRepository;

    @BeforeEach
    void cleanDatabase() {
        metricRepository.deleteAll();
        storeRepository.deleteAll();
    }

    @Test
    void analyzesDirectCompetitorsFromCsvStores() throws Exception {
        importFixtureStores();

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
        assertThat(response.notes()).anyMatch(note -> note.contains("CSV"));
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

    @Test
    void matchesCommercialStoreCategoriesAcrossTaxonomyDepths() throws Exception {
        Path csv = Files.createTempFile("commercial-stores-taxonomy", ".csv");
        Files.writeString(
                csv,
                """
                        상가업소번호,상호명,상권업종대분류명,상권업종중분류명,상권업종소분류명,시도명,시군구명,행정동명,도로명주소,지번주소,경도,위도
                        csv-001,연남카페,음식,비알코올,카페,서울,마포구,연남동,서울 마포구 연남동,서울 마포구 연남동,126.91,37.55
                        """
        );

        commercialAreaService.importCsv(csv.toString(), "서울");

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

        assertThat(response.totalStores()).isEqualTo(1);
        assertThat(response.directCompetitors()).isEqualTo(1);
    }

    @Test
    void doesNotCountAllStoresAsDirectCompetitorsWhenIndustryIsMissing() throws Exception {
        importFixtureStores();

        CommercialAreaResponse response = commercialAreaService.analyze(new CommercialAreaRequest(
                "서울",
                "마포구",
                "연남동",
                null,
                null,
                null,
                null,
                null,
                null
        ));

        assertThat(response.totalStores()).isEqualTo(7);
        assertThat(response.directCompetitors()).isZero();
        assertThat(response.similarCompetitors()).isZero();
        assertThat(response.competitionLevel()).isEqualTo("unknown");
        assertThat(response.notes()).anyMatch(note -> note.contains("업종 조건"));
    }

    @Test
    void broadensToSigunguDataWhenDongHasNoMatchingStores() throws Exception {
        importFixtureStores();

        CommercialAreaResponse response = commercialAreaService.analyze(new CommercialAreaRequest(
                "서울",
                "마포구",
                "없는동",
                null,
                null,
                null,
                "음식점업",
                "커피점/카페",
                "카페"
        ));

        assertThat(response.totalStores()).isEqualTo(8);
        assertThat(response.directCompetitors()).isEqualTo(6);
        assertThat(response.notes()).anyMatch(note -> note.contains("시군구 전체"));
    }

    private void importFixtureStores() throws Exception {
        Path csv = Files.createTempFile("commercial-stores-fixture", ".csv");
        Files.writeString(
                csv,
                """
                        상가업소번호,상호명,상권업종대분류명,상권업종중분류명,상권업종소분류명,시도명,시군구명,행정동명,도로명주소,지번주소,경도,위도
                        csv-001,연남브루잉,음식점업,커피점/카페,카페,서울,마포구,연남동,서울 마포구 연남동,서울 마포구 연남동,126.923,37.562
                        csv-002,연남라떼,음식점업,커피점/카페,카페,서울,마포구,연남동,서울 마포구 연남동,서울 마포구 연남동,126.923,37.562
                        csv-003,홍대입구 커피,음식점업,커피점/카페,카페,서울,마포구,연남동,서울 마포구 연남동,서울 마포구 연남동,126.923,37.562
                        csv-004,골목 에스프레소,음식점업,커피점/카페,카페,서울,마포구,연남동,서울 마포구 연남동,서울 마포구 연남동,126.923,37.562
                        csv-005,연남 베이커리카페,음식점업,커피점/카페,카페,서울,마포구,연남동,서울 마포구 연남동,서울 마포구 연남동,126.923,37.562
                        csv-006,연남 디저트,음식점업,제과제빵떡케익,디저트,서울,마포구,연남동,서울 마포구 연남동,서울 마포구 연남동,126.923,37.562
                        csv-007,연남 분식,음식점업,분식,분식,서울,마포구,연남동,서울 마포구 연남동,서울 마포구 연남동,126.923,37.562
                        csv-008,상수 카페,음식점업,커피점/카페,카페,서울,마포구,상수동,서울 마포구 상수동,서울 마포구 상수동,126.923,37.562
                        """
        );
        commercialAreaService.importCsv(csv.toString(), "서울");
    }
}
