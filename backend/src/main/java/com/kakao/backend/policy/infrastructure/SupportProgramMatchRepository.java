package com.kakao.backend.policy.infrastructure;

import com.kakao.backend.policy.domain.SupportProgramMatch;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SupportProgramMatchRepository extends JpaRepository<SupportProgramMatch, Long> {
}
