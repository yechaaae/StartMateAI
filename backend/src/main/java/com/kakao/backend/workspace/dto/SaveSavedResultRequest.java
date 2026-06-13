package com.kakao.backend.workspace.dto;

import java.util.Map;

public record SaveSavedResultRequest(
        Long workspaceId,
        String sourceFeature,
        String resultType,
        Long referenceId,
        String title,
        String summary,
        Map<String, Object> payload
) {
}
