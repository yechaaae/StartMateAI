package com.kakao.backend.workspace.presentation;

import com.kakao.backend.auth.service.AuthException;
import com.kakao.backend.auth.service.AuthSession;
import com.kakao.backend.workspace.application.WorkspaceService;
import com.kakao.backend.workspace.dto.CreateWorkspaceRequest;
import com.kakao.backend.workspace.dto.UpdateWorkspaceRequest;
import com.kakao.backend.workspace.dto.WorkspaceResponse;
import jakarta.servlet.http.HttpSession;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/workspaces")
@RequiredArgsConstructor
// 로그인한 사용자의 워크스페이스 목록/생성/확정 갱신 API를 담당합니다.
public class WorkspaceController {

    private final WorkspaceService workspaceService;

    @GetMapping
    public List<WorkspaceResponse> getWorkspaces(HttpSession session) {
        return workspaceService.getWorkspaces(getLoginUserId(session));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public WorkspaceResponse createWorkspace(
            @RequestBody(required = false) CreateWorkspaceRequest request,
            HttpSession session
    ) {
        return workspaceService.createWorkspace(getLoginUserId(session), request);
    }

    @PatchMapping("/{workspaceId}")
    public WorkspaceResponse updateWorkspace(
            @PathVariable Long workspaceId,
            @RequestBody UpdateWorkspaceRequest request,
            HttpSession session
    ) {
        return workspaceService.updateWorkspace(getLoginUserId(session), workspaceId, request);
    }

    private Long getLoginUserId(HttpSession session) {
        Object userId = session.getAttribute(AuthSession.LOGIN_USER_ID);
        if (!(userId instanceof Long id)) {
            throw new AuthException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return id;
    }
}
