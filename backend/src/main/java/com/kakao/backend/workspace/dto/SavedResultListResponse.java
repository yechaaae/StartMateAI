package com.kakao.backend.workspace.dto;

import java.util.List;

public record SavedResultListResponse(
        List<SavedResultSummaryResponse> results
) {
}
