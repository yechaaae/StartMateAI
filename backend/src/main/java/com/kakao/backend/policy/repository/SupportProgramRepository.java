package com.kakao.backend.policy.repository;

import com.kakao.backend.policy.domain.SupportProgram;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SupportProgramRepository extends JpaRepository<SupportProgram, Long> {

    Optional<SupportProgram> findBySourceAndSourceId(String source, String sourceId);
}
