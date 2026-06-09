package com.kakao.backend.startupProfile.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

// 창업 프로필에서 희망 창업 형태를 제한된 값으로 관리합니다.
public enum PreferredBusinessType {

    ONLINE("ONLINE", "온라인"),
    OFFLINE("OFFLINE", "오프라인"),
    PLATFORM("PLATFORM", "플랫폼"),
    LOCAL_STORE("LOCAL_STORE", "소상공인 매장"),
    HYBRID("HYBRID", "온오프라인 병행"),
    UNDECIDED("UNDECIDED", "미정");

    private final String code;
    private final String label;

    PreferredBusinessType(String code, String label) {
        this.code = code;
        this.label = label;
    }

    @JsonCreator
    public static PreferredBusinessType from(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }

        String normalizedValue = value.trim();
        return Arrays.stream(values())
                .filter(type -> type.code.equalsIgnoreCase(normalizedValue)
                        || type.name().equalsIgnoreCase(normalizedValue)
                        || type.label.equals(normalizedValue))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("지원하지 않는 희망 창업 형태입니다: " + value));
    }

    @JsonValue
    public String getCode() {
        return code;
    }

    public String getLabel() {
        return label;
    }
}
