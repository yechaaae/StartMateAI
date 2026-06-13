package com.kakao.backend.workspace.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.kakao.backend.auth.service.AuthException;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import com.kakao.backend.workspace.domain.Workspace;
import com.kakao.backend.workspace.dto.CreateWorkspaceRequest;
import com.kakao.backend.workspace.dto.UpdateWorkspaceRequest;
import com.kakao.backend.workspace.dto.WorkspaceResponse;
import com.kakao.backend.workspace.infrastructure.WorkspaceRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;

@ExtendWith(MockitoExtension.class)
class WorkspaceServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private WorkspaceRepository workspaceRepository;

    private WorkspaceService workspaceService;

    @BeforeEach
    void setUp() {
        workspaceService = new WorkspaceService(userRepository, workspaceRepository);
    }

    @Test
    void 제목_없이_생성하면_기본_이름으로_워크스페이스를_만든다() {
        User user = user();
        given(userRepository.findById(1L)).willReturn(Optional.of(user));
        given(workspaceRepository.save(any(Workspace.class))).willAnswer(invocation -> invocation.getArgument(0));

        WorkspaceResponse response = workspaceService.createWorkspace(1L, new CreateWorkspaceRequest(null));

        assertThat(response.title()).isEqualTo("새 워크스페이스");
        assertThat(response.status()).isEqualTo("ACTIVE");
    }

    @Test
    void 확정_아이템으로_워크스페이스를_갱신한다() {
        User user = user();
        Workspace workspace = Workspace.create("새 워크스페이스", "ACTIVE");
        workspace.setUser(user);
        given(workspaceRepository.findById(10L)).willReturn(Optional.of(workspace));

        UpdateWorkspaceRequest request = new UpdateWorkspaceRequest(
                null,
                new UpdateWorkspaceRequest.SelectedIdeaRequest("로컬 카페 브랜드", "F&B", 92, "상권과 강점이 맞습니다"));

        WorkspaceResponse response = workspaceService.updateWorkspace(1L, 10L, request);

        assertThat(response.title()).isEqualTo("로컬 카페 브랜드");
        assertThat(response.selectedIdeaTitle()).isEqualTo("로컬 카페 브랜드");
        assertThat(response.selectedIdeaCategory()).isEqualTo("F&amp;B");
        assertThat(response.selectedIdeaScore()).isEqualTo(92);
    }

    @Test
    void 다른_사용자의_워크스페이스는_수정할_수_없다() {
        User other = User.createLocal("other@example.com", "encodedPassword", "다른유저");
        other.setId(2L);
        Workspace workspace = Workspace.create("남의 작업공간", "ACTIVE");
        workspace.setUser(other);
        given(workspaceRepository.findById(10L)).willReturn(Optional.of(workspace));

        assertThatThrownBy(() -> workspaceService.updateWorkspace(1L, 10L,
                new UpdateWorkspaceRequest("바꾼 이름", null)))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.FORBIDDEN);
    }

    @Test
    void 없는_워크스페이스를_수정하면_실패한다() {
        given(workspaceRepository.findById(99L)).willReturn(Optional.empty());

        assertThatThrownBy(() -> workspaceService.updateWorkspace(1L, 99L,
                new UpdateWorkspaceRequest("이름", null)))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.NOT_FOUND);

        verify(workspaceRepository, never()).save(any(Workspace.class));
    }

    private User user() {
        User user = User.createLocal("test@example.com", "encodedPassword", "유저");
        user.setId(1L);
        return user;
    }
}
