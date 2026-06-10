package com.kakao.backend.marketing.dto;

import com.kakao.backend.marketing.domain.SnsPublishLog;
import java.time.LocalDateTime;

public record ThreadsPublishResponse(
        Long logId,
        String platformPostId,
        String status,
        LocalDateTime publishedAt
) {

    public static ThreadsPublishResponse from(SnsPublishLog log) {
        return new ThreadsPublishResponse(
                log.getId(),
                log.getPlatformPostId(),
                log.getStatus(),
                log.getPublishedAt()
        );
    }
}
