package com.kakao.backend.operation.dto;

public record OperationFeedbackResponse(
        Long id,
        Long workspaceId,
        Long savedResultId,
        boolean savedResultCreated
) {
}
