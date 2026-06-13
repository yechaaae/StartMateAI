package com.kakao.backend.startupProfile.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

// 사용자가 창업 전(예비창업자)인지 창업 후(운영 중)인지를 구분합니다.
public enum StartupStage {

    PRE_STARTUP("PRE_STARTUP", "창업 전"),
    POST_STARTUP("POST_STARTUP", "창업 후");

    private final String code;
    private final String label;

    StartupStage(String code, String label) {
        this.code = code;
        this.label = label;
    }

    @JsonCreator
    public static StartupStage from(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }

        String normalizedValue = value.trim();
        return Arrays.stream(values())
                .filter(stage -> stage.code.equalsIgnoreCase(normalizedValue)
                        || stage.name().equalsIgnoreCase(normalizedValue)
                        || stage.label.equals(normalizedValue))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("지원하지 않는 창업 단계입니다: " + value));
    }

    @JsonValue
    public String getCode() {
        return code;
    }

    public String getLabel() {
        return label;
    }
}
