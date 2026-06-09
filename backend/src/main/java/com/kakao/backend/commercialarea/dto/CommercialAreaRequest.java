package com.kakao.backend.commercialarea.dto;

public record CommercialAreaRequest(
        String sido,
        String sigungu,
        String dong,
        Double latitude,
        Double longitude,
        Integer radiusMeters,
        String industryLarge,
        String industryMedium,
        String industrySmall
) {
}
