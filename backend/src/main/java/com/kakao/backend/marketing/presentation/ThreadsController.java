package com.kakao.backend.marketing.presentation;

import com.kakao.backend.auth.service.AuthSession;
import com.kakao.backend.marketing.application.ThreadsPublishService;
import com.kakao.backend.marketing.dto.ThreadsAccountResponse;
import com.kakao.backend.marketing.dto.ThreadsConnectUrlResponse;
import com.kakao.backend.marketing.dto.ThreadsPublishLogsResponse;
import com.kakao.backend.marketing.dto.ThreadsPublishRequest;
import com.kakao.backend.marketing.dto.ThreadsPublishResponse;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/sns/threads")
@RequiredArgsConstructor
public class ThreadsController {

    private final ThreadsPublishService threadsPublishService;

    @Value("${app.frontend-url:${APP_FRONTEND_URL:http://localhost:5173}}")
    private String frontendUrl;

    @GetMapping("/account")
    public ThreadsAccountResponse account(HttpSession session) {
        return threadsPublishService.getAccount(currentUserId(session));
    }

    @GetMapping("/connect-url")
    public ThreadsConnectUrlResponse connectUrl(HttpSession session) {
        return new ThreadsConnectUrlResponse(
                threadsPublishService.createConnectUrl(currentUserId(session), session)
        );
    }

    @GetMapping(value = "/callback", produces = MediaType.TEXT_HTML_VALUE)
    public ResponseEntity<String> callback(
            @RequestParam(required = false) String code,
            @RequestParam(required = false) String state,
            HttpSession session
    ) {
        if (code == null || code.isBlank() || state == null || state.isBlank()) {
            return ResponseEntity.ok("""
                    <!doctype html>
                    <html lang="ko">
                    <head><meta charset="utf-8"><title>Threads callback</title></head>
                    <body>Threads OAuth callback endpoint is ready.</body>
                    </html>
                    """);
        }

        try {
            threadsPublishService.connect(code, state, session);
            String target = frontendUrl + "/features/sns?threads=connected";
            return ResponseEntity.status(302)
                    .header(HttpHeaders.LOCATION, target)
                    .body("""
                            <!doctype html>
                            <html lang="ko">
                            <head><meta charset="utf-8"><title>Threads connected</title></head>
                            <body>Threads 계정 연결이 완료되었습니다.</body>
                            </html>
                            """);
        } catch (RuntimeException exception) {
            return ResponseEntity.internalServerError()
                    .contentType(MediaType.TEXT_HTML)
                    .body("""
                            <!doctype html>
                            <html lang="ko">
                            <head><meta charset="utf-8"><title>Threads connection failed</title></head>
                            <body>
                              <h1>Threads 계정 연결 실패</h1>
                              <p>%s</p>
                            </body>
                            </html>
                            """.formatted(escapeHtml(exception.getMessage())));
        }
    }

    @PostMapping("/deauthorize")
    public ResponseEntity<Void> deauthorize() {
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/delete")
    public ResponseEntity<Void> delete() {
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/publish")
    public ThreadsPublishResponse publish(
            @RequestBody ThreadsPublishRequest request,
            HttpSession session
    ) {
        return threadsPublishService.publish(currentUserId(session), request.text());
    }

    @GetMapping("/logs")
    public ThreadsPublishLogsResponse logs(HttpSession session) {
        return threadsPublishService.getLogs(currentUserId(session));
    }

    private Long currentUserId(HttpSession session) {
        Object userId = session.getAttribute(AuthSession.LOGIN_USER_ID);
        if (userId instanceof Long id) {
            return id;
        }
        throw new IllegalStateException("Login is required.");
    }

    private String escapeHtml(String value) {
        if (value == null || value.isBlank()) {
            return "Unknown error";
        }
        return value
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&#39;");
    }
}
