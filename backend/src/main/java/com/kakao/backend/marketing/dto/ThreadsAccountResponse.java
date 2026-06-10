package com.kakao.backend.marketing.dto;

import com.kakao.backend.marketing.domain.SnsPublishAccount;
import java.time.LocalDateTime;

public record ThreadsAccountResponse(
        boolean connected,
        String platformUserId,
        String username,
        LocalDateTime connectedAt,
        LocalDateTime tokenExpiresAt
) {

    public static ThreadsAccountResponse disconnected() {
        return new ThreadsAccountResponse(false, null, null, null, null);
    }

    public static ThreadsAccountResponse from(SnsPublishAccount account) {
        return new ThreadsAccountResponse(
                true,
                account.getPlatformUserId(),
                account.getPlatformUsername(),
                account.getConnectedAt(),
                account.getTokenExpiresAt()
        );
    }
}
