package com.kakao.backend.commercialarea.dto;

public record RentReferenceImportResponse(
        int imported,
        int baseYear,
        int baseQuarter,
        String commercialType
) {
}
