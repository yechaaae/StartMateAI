package com.kakao.backend.internal;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class InternalToolAuthService {

    private final String expectedToken;

    public InternalToolAuthService(
            @Value("${startmate.internal-tool-token:${STARTMATE_INTERNAL_TOOL_TOKEN:startmate-local-internal-token}}")
            String expectedToken
    ) {
        this.expectedToken = expectedToken;
    }

    public void verify(String token) {
        if (expectedToken == null || expectedToken.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Internal tool token is not configured.");
        }
        if (token == null || token.isBlank() || !expectedToken.equals(token)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid internal tool token.");
        }
    }
}
