package com.kakao.backend.marketing.domain;

import com.kakao.backend.common.domain.BaseTimeEntity;
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
@Table(name = "sns_publish_account")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SnsPublishAccount extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "platform", nullable = false)
    private String platform;

    @Column(name = "platform_user_id", nullable = false)
    private String platformUserId;

    @Column(name = "platform_username")
    private String platformUsername;

    @Column(name = "access_token", nullable = false, columnDefinition = "text")
    private String accessToken;

    @Column(name = "refresh_token", columnDefinition = "text")
    private String refreshToken;

    @Column(name = "token_expires_at")
    private LocalDateTime tokenExpiresAt;

    @Column(name = "connected_at", nullable = false)
    private LocalDateTime connectedAt;

    public static SnsPublishAccount createThreads(
            User user,
            String platformUserId,
            String platformUsername,
            String accessToken,
            LocalDateTime tokenExpiresAt
    ) {
        SnsPublishAccount account = new SnsPublishAccount();
        account.setUser(user);
        account.setPlatform("THREADS");
        account.setPlatformUserId(platformUserId);
        account.setPlatformUsername(platformUsername);
        account.setAccessToken(accessToken);
        account.setTokenExpiresAt(tokenExpiresAt);
        account.setConnectedAt(LocalDateTime.now());
        return account;
    }

    public void reconnect(String platformUsername, String accessToken, LocalDateTime tokenExpiresAt) {
        this.platformUsername = platformUsername;
        this.accessToken = accessToken;
        this.tokenExpiresAt = tokenExpiresAt;
        this.connectedAt = LocalDateTime.now();
    }
}
