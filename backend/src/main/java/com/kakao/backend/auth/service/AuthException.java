package com.kakao.backend.auth.service;

import lombok.Getter;
import org.springframework.http.HttpStatus;

// 인증 과정에서 클라이언트에게 전달할 HTTP 상태와 메시지를 함께 담는 예외입니다.
@Getter
public class AuthException extends RuntimeException {

    private final HttpStatus status;

    public AuthException(HttpStatus status, String message) {
        super(message);
        this.status = status;
    }

}
