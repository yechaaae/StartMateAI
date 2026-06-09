package com.kakao.backend.commercialarea.dto;

public record StoreImportRequest(
        String filePath,
        String region
) {
}
