package com.kakao.backend.commercialarea.normalize;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.commercialarea.domain.Store;
import java.util.Map;
import org.junit.jupiter.api.Test;

class StoreNormalizerTest {

    private final StoreNormalizer normalizer = new StoreNormalizer(new ObjectMapper());

    @Test
    void normalizesSbizApiStoreFields() {
        Store store = normalizer.normalizeApiRow(Map.ofEntries(
                Map.entry("bizesId", "api-001"),
                Map.entry("bizesNm", "연남 테스트 카페"),
                Map.entry("indsLclsNm", "음식점업"),
                Map.entry("indsMclsNm", "커피점/카페"),
                Map.entry("indsSclsNm", "카페"),
                Map.entry("ctprvnNm", "서울특별시"),
                Map.entry("signguNm", "마포구"),
                Map.entry("adongNm", "연남동"),
                Map.entry("rdnmAdr", "서울 마포구 연남동"),
                Map.entry("lon", "126.923"),
                Map.entry("lat", "37.562")
        ));

        assertThat(store.getSource()).isEqualTo("sbiz_api");
        assertThat(store.getSourceStoreId()).isEqualTo("api-001");
        assertThat(store.getSido()).isEqualTo("서울");
        assertThat(store.getSigungu()).isEqualTo("마포구");
        assertThat(store.getDong()).isEqualTo("연남동");
        assertThat(store.getCategorySmall()).isEqualTo("카페");
        assertThat(store.getLongitude()).isEqualTo(126.923);
        assertThat(store.getLatitude()).isEqualTo(37.562);
    }
}
