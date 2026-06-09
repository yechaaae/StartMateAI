package com.kakao.backend.commercialarea.dto;

import java.util.List;

public record CommercialAreaResponse(
        String areaLabel,
        String industryLabel,
        int totalStores,
        int directCompetitors,
        int similarCompetitors,
        String competitionLevel,
        List<String> notes
) {
}
