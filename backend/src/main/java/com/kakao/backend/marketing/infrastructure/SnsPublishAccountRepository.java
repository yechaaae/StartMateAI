package com.kakao.backend.marketing.infrastructure;

import com.kakao.backend.marketing.domain.SnsPublishAccount;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SnsPublishAccountRepository extends JpaRepository<SnsPublishAccount, Long> {

    Optional<SnsPublishAccount> findFirstByUserIdAndPlatformOrderByConnectedAtDesc(Long userId, String platform);

    Optional<SnsPublishAccount> findByUserIdAndPlatformAndPlatformUserId(
            Long userId,
            String platform,
            String platformUserId
    );
}
