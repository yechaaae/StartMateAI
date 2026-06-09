package com.kakao.backend.commercialarea.normalize;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.commercialarea.domain.Store;
import java.text.Normalizer;
import java.util.Map;
import java.util.Objects;
import org.springframework.stereotype.Component;

@Component
public class StoreNormalizer {

    private final ObjectMapper objectMapper;

    public StoreNormalizer(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public Store normalizeCsvRow(Map<String, String> row) {
        Store store = Store.create();
        store.setSource("sbiz_csv");
        store.setSourceStoreId(defaultSourceStoreId(row));
        store.setStoreName(first(row, "상호명", "store_name", "상가업소명"));
        store.setCategoryLarge(first(row, "상권업종대분류명", "category_large", "대분류명"));
        store.setCategoryMedium(first(row, "상권업종중분류명", "category_medium", "중분류명"));
        store.setCategorySmall(first(row, "상권업종소분류명", "category_small", "소분류명"));
        store.setIndustryCode(first(row, "표준산업분류코드", "industry_code"));
        store.setIndustryName(first(row, "표준산업분류명", "industry_name"));
        store.setSido(normalizeSido(first(row, "시도명", "sido")));
        store.setSigungu(first(row, "시군구명", "sigungu"));
        store.setDong(first(row, "행정동명", "법정동명", "dong"));
        store.setRoadAddress(first(row, "도로명주소", "road_address"));
        store.setJibunAddress(first(row, "지번주소", "jibun_address"));
        store.setLongitude(parseDouble(first(row, "경도", "longitude")));
        store.setLatitude(parseDouble(first(row, "위도", "latitude")));
        store.setRawPayload(toJson(row));
        return store;
    }

    public void copyInto(Store source, Store target) {
        target.setStoreName(source.getStoreName());
        target.setCategoryLarge(source.getCategoryLarge());
        target.setCategoryMedium(source.getCategoryMedium());
        target.setCategorySmall(source.getCategorySmall());
        target.setIndustryCode(source.getIndustryCode());
        target.setIndustryName(source.getIndustryName());
        target.setSido(source.getSido());
        target.setSigungu(source.getSigungu());
        target.setDong(source.getDong());
        target.setRoadAddress(source.getRoadAddress());
        target.setJibunAddress(source.getJibunAddress());
        target.setLongitude(source.getLongitude());
        target.setLatitude(source.getLatitude());
        target.setRawPayload(source.getRawPayload());
    }

    private String defaultSourceStoreId(Map<String, String> row) {
        String explicit = first(row, "상가업소번호", "상가업소ID", "source_store_id", "id");
        if (explicit != null && !explicit.isBlank()) {
            return explicit;
        }
        String basis = Objects.toString(first(row, "상호명"), "") + "|"
                + Objects.toString(first(row, "도로명주소", "지번주소"), "");
        return "generated-" + Integer.toUnsignedString(basis.hashCode());
    }

    private String first(Map<String, String> row, String... keys) {
        for (String key : keys) {
            String value = row.get(key);
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return null;
    }

    private Double parseDouble(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private String normalizeSido(String value) {
        if (value == null || value.isBlank()) {
            return value;
        }
        String normalized = Normalizer.normalize(value.trim(), Normalizer.Form.NFC);
        return switch (normalized) {
            case "서울특별시" -> "서울";
            case "부산광역시" -> "부산";
            case "대구광역시" -> "대구";
            case "인천광역시" -> "인천";
            case "광주광역시" -> "광주";
            case "대전광역시" -> "대전";
            case "울산광역시" -> "울산";
            case "세종특별자치시" -> "세종";
            case "경기도" -> "경기";
            case "강원특별자치도", "강원도" -> "강원";
            case "충청북도" -> "충북";
            case "충청남도" -> "충남";
            case "전북특별자치도", "전라북도" -> "전북";
            case "전라남도" -> "전남";
            case "경상북도" -> "경북";
            case "경상남도" -> "경남";
            case "제주특별자치도" -> "제주";
            default -> normalized;
        };
    }

    private String toJson(Map<String, String> row) {
        try {
            return objectMapper.writeValueAsString(row);
        } catch (JsonProcessingException ignored) {
            return "{}";
        }
    }
}
