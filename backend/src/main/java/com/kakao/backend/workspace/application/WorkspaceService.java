package com.kakao.backend.workspace.application;

import com.kakao.backend.auth.service.AuthException;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import com.kakao.backend.workspace.domain.Workspace;
import com.kakao.backend.workspace.dto.CreateWorkspaceRequest;
import com.kakao.backend.workspace.dto.UpdateWorkspaceRequest;
import com.kakao.backend.workspace.dto.WorkspaceResponse;
import com.kakao.backend.workspace.infrastructure.WorkspaceRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
// 워크스페이스 목록 조회 / 생성 / 확정 아이템 갱신을 담당합니다.
public class WorkspaceService {

    private static final String DEFAULT_TITLE = "새 워크스페이스";
    private static final String ACTIVE = "ACTIVE";
    private static final int TITLE_MAX_LENGTH = 100;

    private final UserRepository userRepository;
    private final WorkspaceRepository workspaceRepository;

    @Transactional(readOnly = true)
    public List<WorkspaceResponse> getWorkspaces(Long userId) {
        getUser(userId);
        return workspaceRepository.findByUserIdOrderByIdAsc(userId).stream()
                .map(WorkspaceResponse::from)
                .toList();
    }

    @Transactional
    public WorkspaceResponse createWorkspace(Long userId, CreateWorkspaceRequest request) {
        User user = getUser(userId);
        String title = normalizeTitle(request == null ? null : request.title(), DEFAULT_TITLE);
        Workspace workspace = Workspace.create(title, ACTIVE);
        workspace.setUser(user);
        return WorkspaceResponse.from(workspaceRepository.save(workspace));
    }

    @Transactional
    public WorkspaceResponse updateWorkspace(Long userId, Long workspaceId, UpdateWorkspaceRequest request) {
        if (request == null) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "수정할 내용을 입력해주세요.");
        }

        Workspace workspace = workspaceRepository.findById(workspaceId)
                .orElseThrow(() -> new AuthException(HttpStatus.NOT_FOUND, "워크스페이스를 찾을 수 없습니다."));
        if (!workspace.getUser().getId().equals(userId)) {
            throw new AuthException(HttpStatus.FORBIDDEN, "본인의 워크스페이스만 수정할 수 있습니다.");
        }

        if (request.selectedIdea() != null) {
            UpdateWorkspaceRequest.SelectedIdeaRequest idea = request.selectedIdea();
            workspace.applySelectedIdea(
                    truncate(idea.title()),
                    truncate(idea.category()),
                    idea.score(),
                    idea.reason());
        } else if (request.title() != null && !request.title().isBlank()) {
            workspace.setTitle(normalizeTitle(request.title(), workspace.getTitle()));
        }

        return WorkspaceResponse.from(workspace);
    }

    private User getUser(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다."));
    }

    private String normalizeTitle(String title, String fallback) {
        if (title == null || title.isBlank()) {
            return fallback;
        }
        return truncate(title);
    }

    private String truncate(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.length() > TITLE_MAX_LENGTH ? trimmed.substring(0, TITLE_MAX_LENGTH) : trimmed;
    }
}
