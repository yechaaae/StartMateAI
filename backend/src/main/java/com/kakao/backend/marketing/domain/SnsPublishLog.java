package com.kakao.backend.marketing.domain;

import com.kakao.backend.common.domain.BaseCreatedEntity;
import com.kakao.backend.user.model.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "sns_publish_log")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SnsPublishLog extends BaseCreatedEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "publish_account_id")
    private SnsPublishAccount publishAccount;

    @Column(name = "platform", nullable = false)
    private String platform;

    @Column(name = "status", nullable = false)
    private String status;

    @Column(name = "content_text", nullable = false, columnDefinition = "text")
    private String contentText;

    @Column(name = "platform_post_id")
    private String platformPostId;

    @Column(name = "error_message", columnDefinition = "text")
    private String errorMessage;

    @Column(name = "published_at")
    private LocalDateTime publishedAt;

    public static SnsPublishLog success(
            User user,
            SnsPublishAccount publishAccount,
            String contentText,
            String platformPostId
    ) {
        SnsPublishLog log = new SnsPublishLog();
        log.setUser(user);
        log.setPublishAccount(publishAccount);
        log.setPlatform("THREADS");
        log.setStatus("SUCCESS");
        log.setContentText(contentText);
        log.setPlatformPostId(platformPostId);
        log.setPublishedAt(LocalDateTime.now());
        return log;
    }

    public static SnsPublishLog failure(
            User user,
            SnsPublishAccount publishAccount,
            String contentText,
            String errorMessage
    ) {
        SnsPublishLog log = new SnsPublishLog();
        log.setUser(user);
        log.setPublishAccount(publishAccount);
        log.setPlatform("THREADS");
        log.setStatus("FAILED");
        log.setContentText(contentText);
        log.setErrorMessage(errorMessage);
        return log;
    }
}
