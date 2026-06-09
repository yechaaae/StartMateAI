package com.kakao.backend.startupProfile.repository;

import com.kakao.backend.startupProfile.model.StartupProfile;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

// 창업 프로필을 사용자 기준으로 조회하고 저장하는 JPA repository입니다.
public interface StartupProfileRepository extends JpaRepository<StartupProfile, Long> {

    Optional<StartupProfile> findByUserId(Long userId);
}
