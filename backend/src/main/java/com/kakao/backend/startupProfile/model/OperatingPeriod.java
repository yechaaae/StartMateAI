package com.kakao.backend.startupProfile.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

// 창업 후 사용자의 현재 사업 운영 기간을 제한된 값으로 관리합니다.
public enum OperatingPeriod {

    UNDER_6M("UNDER_6M", "6개월 미만"),
    SIX_TO_12M("SIX_TO_12M", "6개월~1년"),
    ONE_TO_3Y("ONE_TO_3Y", "1~3년"),
    OVER_3Y("OVER_3Y", "3년 이상");

    private final String code;
    private final String label;

    OperatingPeriod(String code, String label) {
        this.code = code;
        this.label = label;
    }

    @JsonCreator
    public static OperatingPeriod from(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }

        String normalizedValue = value.trim();
        return Arrays.stream(values())
                .filter(period -> period.code.equalsIgnoreCase(normalizedValue)
                        || period.name().equalsIgnoreCase(normalizedValue)
                        || period.label.equals(normalizedValue))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("지원하지 않는 운영 기간입니다: " + value));
    }

    @JsonValue
    public String getCode() {
        return code;
    }

    public String getLabel() {
        return label;
    }
}
