package com.kakao.backend.commercialarea.dto;

public record RentReferenceImportRequest(
        String filePath,
        String commercialType,
        String source
) {
}
