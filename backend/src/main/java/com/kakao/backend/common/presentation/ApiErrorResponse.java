package com.kakao.backend.common.presentation;

// API 에러 응답에서 클라이언트에게 보여줄 메시지를 담습니다.
public record ApiErrorResponse(String message) {
}
