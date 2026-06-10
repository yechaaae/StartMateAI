package com.kakao.backend.marketing.application;

import com.kakao.backend.marketing.domain.SnsPublishAccount;
import com.kakao.backend.marketing.domain.SnsPublishLog;
import com.kakao.backend.marketing.dto.ThreadsAccountResponse;
import com.kakao.backend.marketing.dto.ThreadsPublishLogResponse;
import com.kakao.backend.marketing.dto.ThreadsPublishLogsResponse;
import com.kakao.backend.marketing.dto.ThreadsPublishResponse;
import com.kakao.backend.marketing.infrastructure.SnsPublishAccountRepository;
import com.kakao.backend.marketing.infrastructure.SnsPublishLogRepository;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import jakarta.servlet.http.HttpSession;
import java.security.SecureRandom;
import java.util.HexFormat;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class ThreadsPublishService {

    private static final String PLATFORM = "THREADS";
    private static final String THREADS_OAUTH_STATE = "THREADS_OAUTH_STATE";
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    private final ThreadsApiClient threadsApiClient;
    private final SnsPublishAccountRepository publishAccountRepository;
    private final SnsPublishLogRepository publishLogRepository;
    private final UserRepository userRepository;

    public String createConnectUrl(Long userId, HttpSession session) {
        String state = userId + ":" + randomHex();
        session.setAttribute(THREADS_OAUTH_STATE, state);
        return threadsApiClient.buildAuthorizeUrl(state);
    }

    @Transactional
    public ThreadsAccountResponse connect(String code, String state, HttpSession session) {
        if (state == null || state.isBlank()) {
            throw new IllegalArgumentException("Invalid Threads OAuth state.");
        }

        Long userId = parseUserId(state);
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));

        ThreadsApiClient.ThreadsToken token = threadsApiClient.exchangeCode(code);
        ThreadsApiClient.ThreadsProfile profile = threadsApiClient.loadProfile(token.accessToken());

        SnsPublishAccount account = publishAccountRepository
                .findByUserIdAndPlatformAndPlatformUserId(userId, PLATFORM, profile.id())
                .map(existing -> {
                    existing.reconnect(profile.username(), token.accessToken(), token.expiresAt());
                    return existing;
                })
                .orElseGet(() -> SnsPublishAccount.createThreads(
                        user,
                        profile.id(),
                        profile.username(),
                        token.accessToken(),
                        token.expiresAt()
                ));

        session.removeAttribute(THREADS_OAUTH_STATE);
        return ThreadsAccountResponse.from(publishAccountRepository.save(account));
    }

    @Transactional(readOnly = true)
    public ThreadsAccountResponse getAccount(Long userId) {
        return publishAccountRepository.findFirstByUserIdAndPlatformOrderByConnectedAtDesc(userId, PLATFORM)
                .map(ThreadsAccountResponse::from)
                .orElseGet(ThreadsAccountResponse::disconnected);
    }

    @Transactional
    public ThreadsPublishResponse publish(Long userId, String text) {
        String normalizedText = normalizeText(text);
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));
        SnsPublishAccount account = publishAccountRepository
                .findFirstByUserIdAndPlatformOrderByConnectedAtDesc(userId, PLATFORM)
                .orElseThrow(() -> new IllegalStateException("Threads account is not connected."));

        try {
            String creationId = threadsApiClient.createTextContainer(
                    account.getPlatformUserId(),
                    account.getAccessToken(),
                    normalizedText
            );
            String platformPostId = threadsApiClient.publishContainer(
                    account.getPlatformUserId(),
                    account.getAccessToken(),
                    creationId
            );
            return ThreadsPublishResponse.from(publishLogRepository.save(
                    SnsPublishLog.success(user, account, normalizedText, platformPostId)
            ));
        } catch (RuntimeException exception) {
            publishLogRepository.save(SnsPublishLog.failure(
                    user,
                    account,
                    normalizedText,
                    exception.getMessage()
            ));
            throw exception;
        }
    }

    @Transactional(readOnly = true)
    public ThreadsPublishLogsResponse getLogs(Long userId) {
        return new ThreadsPublishLogsResponse(
                publishLogRepository.findTop20ByUserIdAndPlatformOrderByIdDesc(userId, PLATFORM)
                        .stream()
                        .map(ThreadsPublishLogResponse::from)
                        .toList()
        );
    }

    private String normalizeText(String text) {
        if (text == null || text.isBlank()) {
            throw new IllegalArgumentException("Threads post text is required.");
        }
        String normalized = text.trim();
        if (normalized.length() > 500) {
            throw new IllegalArgumentException("Threads post text must be 500 characters or fewer.");
        }
        return normalized;
    }

    private Long parseUserId(String state) {
        try {
            return Long.parseLong(state.split(":", 2)[0]);
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Invalid Threads OAuth state.");
        }
    }

    private String randomHex() {
        byte[] bytes = new byte[16];
        SECURE_RANDOM.nextBytes(bytes);
        return HexFormat.of().formatHex(bytes);
    }
}
