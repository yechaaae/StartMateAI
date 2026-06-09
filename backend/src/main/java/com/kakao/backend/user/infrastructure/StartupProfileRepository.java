package com.kakao.backend.user.infrastructure;

import com.kakao.backend.user.domain.StartupProfile;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface StartupProfileRepository extends JpaRepository<StartupProfile, Long> {

    Optional<StartupProfile> findByUserId(Long userId);
}
