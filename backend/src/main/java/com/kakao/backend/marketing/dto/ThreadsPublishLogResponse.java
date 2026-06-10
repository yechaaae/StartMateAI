package com.kakao.backend.marketing.dto;

import com.kakao.backend.marketing.domain.SnsPublishLog;
import java.time.LocalDateTime;

public record ThreadsPublishLogResponse(
        Long id,
        String status,
        String text,
        String platformPostId,
        String errorMessage,
        LocalDateTime publishedAt,
        LocalDateTime createdAt
) {

    public static ThreadsPublishLogResponse from(SnsPublishLog log) {
        return new ThreadsPublishLogResponse(
                log.getId(),
                log.getStatus(),
                log.getContentText(),
                log.getPlatformPostId(),
                log.getErrorMessage(),
                log.getPublishedAt(),
                log.getCreatedAt()
        );
    }
}
