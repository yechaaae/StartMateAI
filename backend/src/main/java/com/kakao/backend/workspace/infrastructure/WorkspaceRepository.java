package com.kakao.backend.workspace.infrastructure;

import com.kakao.backend.workspace.domain.Workspace;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WorkspaceRepository extends JpaRepository<Workspace, Long> {

    Optional<Workspace> findFirstByUserIdAndStatusOrderByIdAsc(Long userId, String status);
}
