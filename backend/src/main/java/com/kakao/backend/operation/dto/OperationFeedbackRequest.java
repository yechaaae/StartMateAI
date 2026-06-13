package com.kakao.backend.operation.dto;

import java.math.BigDecimal;
import java.util.List;

public record OperationFeedbackRequest(
        String period,
        List<KpiRequest> kpis,
        List<ProductShareRequest> products,
        List<List<String>> channels,
        String notes,
        List<SuggestionRequest> suggestions,
        String selectedSuggestionTitle
) {

    public record KpiRequest(
            String key,
            String label,
            String unit,
            BigDecimal current,
            BigDecimal previous
    ) {
    }

    public record ProductShareRequest(
            String name,
            BigDecimal share,
            Boolean locked
    ) {
        public boolean isLocked() {
            return Boolean.TRUE.equals(locked);
        }
    }

    public record SuggestionRequest(
            String title,
            String body,
            String link
    ) {
    }
}
