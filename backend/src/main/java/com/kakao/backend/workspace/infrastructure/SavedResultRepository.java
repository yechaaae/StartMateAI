package com.kakao.backend.workspace.infrastructure;

import com.kakao.backend.workspace.domain.SavedResult;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SavedResultRepository extends JpaRepository<SavedResult, Long> {
}
