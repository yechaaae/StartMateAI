package com.kakao.backend.common.presentation;

import com.kakao.backend.auth.service.AuthException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
// 컨트롤러에서 발생한 예외를 일관된 API 에러 응답으로 변환합니다.
public class GlobalExceptionHandler {

    // 인증 관련 예외의 HTTP 상태와 메시지를 그대로 응답합니다.
    @ExceptionHandler(AuthException.class)
    public ResponseEntity<ApiErrorResponse> handleAuthException(AuthException exception) {
        return ResponseEntity
                .status(exception.getStatus())
                .body(new ApiErrorResponse(exception.getMessage()));
    }
}
