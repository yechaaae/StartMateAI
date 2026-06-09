package com.kakao.backend.common.external;

public record ExternalApiResult(
        boolean ok,
        String source,
        String body,
        Integer status,
        String errorMessage
) {

    public static ExternalApiResult ok(String source, String body, int status) {
        return new ExternalApiResult(true, source, body, status, null);
    }

    public static ExternalApiResult fail(String source, Integer status, String errorMessage) {
        return new ExternalApiResult(false, source, null, status, errorMessage);
    }
}
