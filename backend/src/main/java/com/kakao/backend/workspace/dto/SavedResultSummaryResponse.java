package com.kakao.backend.workspace.dto;

public record SavedResultSummaryResponse(
        Long id,
        Long workspaceId,
        String sourceFeature,
        String resultType,
        Long referenceId,
        String title,
        String summary,
        String createdAt
) {
}
