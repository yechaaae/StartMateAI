package com.kakao.backend.policy.dto;

import java.util.Map;

public record SupportProgramSyncResponse(
        Map<String, Integer> upsertedBySource,
        int totalPrograms
) {
}
