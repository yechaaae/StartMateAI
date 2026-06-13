package com.kakao.backend.workspace.infrastructure;

import com.kakao.backend.workspace.domain.SavedResult;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SavedResultRepository extends JpaRepository<SavedResult, Long> {

    List<SavedResult> findByWorkspaceUserIdOrderByCreatedAtDesc(Long userId);

    Optional<SavedResult> findByIdAndWorkspaceUserId(Long id, Long userId);

    Optional<SavedResult> findFirstByWorkspaceUserIdAndSourceFeatureIgnoreCaseOrderByCreatedAtDesc(
            Long userId,
            String sourceFeature
    );

    Optional<SavedResult> findFirstByWorkspaceIdAndWorkspaceUserIdAndSourceFeatureIgnoreCaseOrderByCreatedAtDesc(
            Long workspaceId,
            Long userId,
            String sourceFeature
    );
}
