package com.kakao.backend.marketing.infrastructure;

import com.kakao.backend.marketing.domain.SnsPublishLog;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SnsPublishLogRepository extends JpaRepository<SnsPublishLog, Long> {

    List<SnsPublishLog> findTop20ByUserIdAndPlatformOrderByIdDesc(Long userId, String platform);
}
