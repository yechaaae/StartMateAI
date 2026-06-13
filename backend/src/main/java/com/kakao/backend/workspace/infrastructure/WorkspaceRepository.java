package com.kakao.backend.workspace.infrastructure;

import com.kakao.backend.workspace.domain.Workspace;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WorkspaceRepository extends JpaRepository<Workspace, Long> {

    Optional<Workspace> findFirstByUserIdAndStatusOrderByIdAsc(Long userId, String status);

    Optional<Workspace> findByIdAndUserId(Long id, Long userId);

    List<Workspace> findByUserIdOrderByIdAsc(Long userId);
}
