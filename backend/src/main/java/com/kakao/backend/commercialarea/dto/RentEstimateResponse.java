package com.kakao.backend.commercialarea.dto;

import java.math.BigDecimal;

public record RentEstimateResponse(
        String sido,
        String regionDepth2,
        String regionDepth3,
        String commercialType,
        Integer baseYear,
        Integer baseQuarter,
        BigDecimal rentPerM2Thousand,
        Double areaM2,
        Integer estimatedMonthlyRent,
        String matchLevel,
        String source
) {
}
