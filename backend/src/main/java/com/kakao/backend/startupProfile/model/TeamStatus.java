package com.kakao.backend.startupProfile.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

// 창업 프로필에서 팀 구성 상태를 제한된 값으로 관리합니다.
public enum TeamStatus {

    SOLO("SOLO", "개인"),
    HAS_TEAM("HAS_TEAM", "팀 있음"),
    LOOKING_FOR_TEAM("LOOKING_FOR_TEAM", "팀원 모집 중"),
    UNDECIDED("UNDECIDED", "미정");

    private final String code;
    private final String label;

    TeamStatus(String code, String label) {
        this.code = code;
        this.label = label;
    }

    @JsonCreator
    public static TeamStatus from(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }

        String normalizedValue = value.trim();
        return Arrays.stream(values())
                .filter(status -> status.code.equalsIgnoreCase(normalizedValue)
                        || status.name().equalsIgnoreCase(normalizedValue)
                        || status.label.equals(normalizedValue))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("지원하지 않는 팀 구성 상태입니다: " + value));
    }

    @JsonValue
    public String getCode() {
        return code;
    }

    public String getLabel() {
        return label;
    }
}
